import os
import uuid
import time
from typing import Optional, Dict, List
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredHTMLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchAny
from crm.utils.qdrand_db import client
from crm.utils.embedder import embedder
from crm.utils.token_text_splitter import TikTokenTextSplitter
from crm.utils.table_aware_splitter import TableAwareTextSplitter
from crm.models.rabbitmq_event_models import ResourceEvent
from crm.configs.constant import EXCHANGE_NAME
from crm.rabbitmq.producers import rabbitmq_producer
from crm.utils.logger import logger
from crm.configs.performance_config import perf_config
# Note: Heavy OpenAI vision extraction is optional; import lazily where needed

class PDFEmbedder:
    """
    A class for loading, splitting, embedding, and storing documents (PDF, DOCX, HTML) into Qdrant vector database using LangChain
    
    args:
        collection_name (str): The name of the Qdrant collection to insert into
        client: The Qdrant client instance for upserting points
        embedder: The embedding model used to encode document chunks
        chunk_size (int): Maximum characters in each text chunk, defaults to 500
        chunk_overlap (int): Number of characters to overlap between chunks, defaults to 100
    
    returns:
        PDFEmbedder: Instance for handling document processing and embedding operations
    """

    def __init__(self, collection_name, client, embedder, chunk_size=500, chunk_overlap=100):
        """
        Description: Initialize the PDFEmbedder with collection configuration, vector DB client, and text splitting parameters
        
        args:
            collection_name (str): The name of the Qdrant collection to insert into
            client: The Qdrant client instance for upserting points
            embedder: The embedding model used to encode document chunks
            chunk_size (int): Maximum characters in each text chunk
            chunk_overlap (int): Number of characters to overlap between chunks
        
        returns:
            None
        """
        self.collection_name = collection_name
        self.client = client
        self.embedder = embedder
        
        # Initialize both character-based and token-based splitters
        self.char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Table-aware splitters for different content types
        self.token_splitter = TableAwareTextSplitter(
            max_tokens=perf_config.max_tokens_per_chunk,
            overlap_tokens=perf_config.token_overlap
        )

        # Video-optimized splitter for transcripts (keep regular splitter for video)
        self.video_token_splitter = TikTokenTextSplitter(
            max_tokens=perf_config.video_max_tokens,
            overlap_tokens=perf_config.video_token_overlap
        )
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.global_id_counter = 0
        logger.info(f"Collection Helper on Qdrant Services: {self.collection_name}")
        logger.info(f"Using table-aware chunking: {perf_config.max_tokens_per_chunk} tokens, {perf_config.token_overlap} overlap")

    def document_splitter(self, documents, use_token_splitting=True):
        """
        Description: Split documents into smaller text chunks using token-based or character-based splitting
        
        args:
            documents: List of documents loaded by a LangChain loader
            use_token_splitting (bool): Whether to use token-based splitting (recommended)
        
        returns:
            List: List of text chunks ready for embedding
        """
        logger.info(f"Splitting {len(documents)} pages into chunks (table-aware: {use_token_splitting})...")

        if use_token_splitting:
            # Use table-aware splitting for better performance and semantic preservation
            all_chunks = []
            for doc in documents:
                text_chunks = self.token_splitter.split_text(doc.page_content)
                # Create mock document objects with same structure as LangChain
                for chunk_text in text_chunks:
                    chunk_doc = type(doc)(
                        page_content=chunk_text,
                        metadata=doc.metadata.copy()
                    )
                    all_chunks.append(chunk_doc)

            logger.info(f"Table-aware splitting created {len(all_chunks)} chunks")
            return all_chunks
        else:
            # Fallback to character-based splitting
            return self.char_splitter.split_documents(documents)

    def load_and_split_pdf(self, pdf_path):
        """
        Description: Load and split a PDF file into chunks using PyPDFLoader
        
        args:
            pdf_path (str): Path to the PDF file to process
        
        returns:
            List: List of text chunks from the PDF document
        """
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        return self.document_splitter(documents)

    def load_and_split_html(self, html_path):
        """
        Description: Load and split an HTML file into chunks using UnstructuredHTMLLoader
        
        args:
            html_path (str): Path to the HTML file to process
        
        returns:
            List: List of text chunks from the HTML document
        """
        loader = UnstructuredHTMLLoader(html_path)
        documents = loader.load()
        return self.document_splitter(documents)

    async def add_embeddings_from_file(
            self,
            file_path: str,
            meta_data: Optional[ResourceEvent] = None,
            file_type: Optional[str] = None
    ) -> None:
        """
        Load, split, embed, and upsert a file's content into the Qdrant vector DB.

        Args:
            file_path (str): Path to the file.
            meta_data (Optional[ResourceEvent]): Additional metadata to store with each chunk.
            file_type (Optional[str]): One of "pdf", "docx", "zeta", or "mp4".
        """
        try:
            # Handle file types with optional OpenAI vision extraction
            if file_type in ("pdf", "docx"):
                texts = None
                try:
                    from crm.services.openai_extraction_services import document_to_images  # type: ignore
                    texts = document_to_images(file_path)
                except Exception as e:
                    logger.warning(f"OpenAI vision extraction unavailable; falling back to text loaders: {e}")
                    try:
                        if file_type == "pdf":
                            docs = self.load_and_split_pdf(file_path)
                        else:
                            docs = self.load_and_split_docx(file_path)
                        texts = [doc.page_content for doc in docs]
                    except Exception as e2:
                        raise ImportError(f"No available loader for {file_type}: {e2}")
            else:
                loader_map = {
                    "zeta": (self.load_and_split_html, "Zeta (HTML)")
                }
                loader_entry = loader_map.get(file_type)
                if not loader_entry:
                    raise ValueError(f"Unsupported file type: {file_type}")
                loader_func, file_label = loader_entry
                logger.debug(f"loader_func: {loader_func}")
                logger.info(f"Embedding {file_label}...")
                docs = loader_func(file_path)
                texts = [doc.page_content for doc in docs]

            # Normalize extracted content to a list of chunks before embedding
            if isinstance(texts, str):
                # Chunk long extracted text using token-aware splitter
                texts = self.token_splitter.split_text(texts)
            elif isinstance(texts, list) and texts and isinstance(texts[0], str):
                # Already a list of strings (pages/chunks) — keep as-is
                pass
            else:
                # Safeguard: coerce to single-item list
                texts = [str(texts)]

            # Use language-aware embeddings for all chunks
            logger.info(
                "Starting embedding generation",
                extra={
                    "file_path": file_path,
                    "chunks": len(texts),
                    "file_type": file_type,
                },
            )
            embed_start = time.perf_counter()
            embeddings = await self.embedder.encode(texts)
            embed_duration = time.perf_counter() - embed_start
            logger.info(
                "Embeddings generated",
                extra={
                    "file_path": file_path,
                    "embeddings": len(embeddings),
                    "duration_sec": round(embed_duration, 3),
                },
            )
            if meta_data and hasattr(meta_data, 'dict'):
                try:
                    logger.debug(f"Meta data: {meta_data.dict()}")
                except Exception:
                    pass

            # Safe access to nested keys
            if meta_data and hasattr(meta_data, 'resource_id') and meta_data.resource_id:
                resource_id = str(meta_data.resource_id)
            else:
                resource_id = uuid.uuid4().hex

            if meta_data and hasattr(meta_data, 'file_name') and meta_data.file_name:
                file_name = str(meta_data.file_name)
            else:
                try:
                    file_name = os.path.basename(file_path)
                except Exception:
                    file_name = None
            
            points = []
            for i, embedding in enumerate(embeddings):
                try:
                    text_chunk = texts[i]
                except Exception:
                    # Length mismatch fallback: skip
                    continue
                points.append(
                    PointStruct(
                        id=uuid.uuid4().hex,
                        vector=embedding,
                        payload={
                            "resource_id": resource_id,
                            "file_name": file_name,
                            "chunk_id": i,
                            "chunk_index": i,
                            "text": text_chunk,
                        },
                    )
                )
            
            logger.info(
                "Upserting embeddings into Qdrant",
                extra={
                    "file_path": file_path,
                    "points": len(points),
                    "collection": self.collection_name,
                },
            )
            upsert_start = time.perf_counter()
            self.client.upsert(collection_name=self.collection_name, points=points)
            upsert_duration = time.perf_counter() - upsert_start
            self.global_id_counter += len(points)

            logger.info(
                "File processed and stored",
                extra={
                    "file_path": file_path,
                    "chunks": len(points),
                    "collection": self.collection_name,
                    "upsert_duration_sec": round(upsert_duration, 3),
                },
            )

        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"File access error for {file_path}: {e}")
            logger.info("Continuing with next file...")
        except ValueError as e:
            logger.error(f"Invalid data format in {file_path}: {e}")
            logger.info("Continuing with next file...")
        except ImportError as e:
            logger.error(f"Required loader not available for {file_path}: {e}")
            logger.info("Continuing with next file...")

    async def process_file(self, file_path, meta_data=None, file_type=None):
        """
        Process a single file and add its embeddings to the vector DB.
        Args:
            file_path (str): Path to the file.
            meta_data (Optional[Dict]): Metadata to associate with the file.
            file_type (Optional[str]): File type ("pdf", "docx", or "zeta").
        """
        try:
            await self.add_embeddings_from_file(file_path, meta_data=meta_data, file_type=file_type)
        except Exception as e:
            logger.error(f"Embedding Failed: {str(e)}", exc_info=True)
            raise

    async def process_folder(self, folder_path, meta_data=None):
        """
        Recursively process all supported files in a folder.

        Args:
            folder_path (str): Path to the folder containing documents.
            meta_data (Optional[Dict]): Metadata to associate with all files.
        """
        for root, _, files in os.walk(folder_path):
            for filename in files:
                ext = filename.lower().split(".")[-1]
                file_type = {"pdf": "pdf", "docx": "docx", "html": "zeta"}.get(ext)

                file_path = os.path.join(root, filename)
                await self.process_file(file_path, meta_data=meta_data, file_type=file_type)

    def update_resource_access(self, resource_id: str, assigned_user_ids: List[str], unassigned_user_ids: List[str]) -> None:
        """
        Update access permissions for a resource by adding and removing user IDs.

        Args:
            resource_id (str): The ID of the resource to update
            assigned_user_ids (List[str]): List of user IDs to add access for
            unassigned_user_ids (List[str]): List of user IDs to remove access from
        """
        try:
            # Create filter to find all points for this resource
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="resource_id",
                        match=MatchAny(any=[resource_id])
                    )
                ]
            )

            # Scroll through all points for this resource
            points = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filter,
                limit=100  # Adjust batch size as needed
            )[0]  # [0] gets points, [1] gets next_page_offset

            if not points:
                logger.info(f"No points found for resource_id: {resource_id}")
                return

            # Update each point's access list
            updated_points = []
            for point in points:
                # Get current access list
                current_access = set(point.payload.get("access", []))

                # Add new users and remove unassigned users
                current_access.update(assigned_user_ids)
                current_access.difference_update(unassigned_user_ids)

                # Create updated point
                updated_point = PointStruct(
                    id=point.id,
                    vector=point.vector,
                    payload={
                        **point.payload,
                        "access": list(current_access)
                    }
                )
                updated_points.append(updated_point)

            # Update points in batches
            if updated_points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=updated_points
                )
                logger.info(f"Successfully updated access for resource {resource_id}")
                logger.debug(f"Added users: {assigned_user_ids}")
                logger.debug(f"Removed users: {unassigned_user_ids}")

        except Exception as e:
            logger.error(f"Error updating access for resource {resource_id}: {e}")

    def _create_content_based_chunks(self, full_text, chunk_size, chunk_overlap):
        """
        Create fixed-size content chunks with overlap, ensuring timestamp boundaries aren't cut.
        
        Args:
            full_text (str): Full timestamped transcript text
            chunk_size (int): Target size for each chunk in characters
            chunk_overlap (int): Number of characters to overlap between chunks
            
        Returns:
            List[str]: List of text chunks with embedded timestamps
        """
        chunks = []
        text_len = len(full_text)
        start = 0
        
        while start < text_len:
            end = start + chunk_size
            
            # Don't go beyond text length
            if end >= text_len:
                chunk = full_text[start:]
                if chunk.strip():
                    chunks.append(chunk.strip())
                break
            
            # Find a good breaking point to avoid cutting timestamps
            chunk_candidate = full_text[start:end]
            
            # Try to end at a complete timestamp or sentence
            good_break_point = self._find_safe_break_point(chunk_candidate, full_text, start, end)
            
            if good_break_point is not None:
                chunk = full_text[start:good_break_point]
            else:
                chunk = chunk_candidate
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            # Move to next chunk with overlap
            if good_break_point:
                start = max(start + 1, good_break_point - chunk_overlap)
            else:
                start = end - chunk_overlap
            
            # Prevent infinite loops
            if start <= 0:
                start = 1
        
        return chunks

    def _find_safe_break_point(self, chunk_candidate, full_text, start_pos, end_pos):
        """
        Find a safe place to break the chunk, avoiding cutting timestamps mid-way.
        
        Args:
            chunk_candidate (str): The chunk text being considered
            full_text (str): The full text
            start_pos (int): Start position in full text
            end_pos (int): End position in full text
            
        Returns:
            int or None: Safe break point position, or None if no good break found
        """
        # Look for end of timestamp patterns like "] text"
        import re
        
        # Find all positions where timestamps end ("] " pattern)
        timestamp_ends = []
        for match in re.finditer(r'\] ', chunk_candidate):
            timestamp_ends.append(start_pos + match.end())
        
        if timestamp_ends:
            # Use the last complete timestamp end as break point
            return timestamp_ends[-1]
        
        # Fallback: try to break at sentence boundaries
        sentence_ends = []
        for match in re.finditer(r'[.!?] ', chunk_candidate):
            sentence_ends.append(start_pos + match.end())
        
        if sentence_ends:
            return sentence_ends[-1]
        
        # Last resort: try to break at word boundaries
        word_boundaries = []
        for match in re.finditer(r' ', chunk_candidate):
            word_boundaries.append(start_pos + match.end())
        
        if word_boundaries:
            # Take last word boundary in the latter half of the chunk
            mid_point = len(chunk_candidate) // 2
            for boundary in reversed(word_boundaries):
                if boundary - start_pos > mid_point:
                    return boundary
        
        return None

    def _extract_timestamps_from_chunk(self, chunk_text):
        """
        Extract all timestamp ranges from a chunk of text.
        
        Args:
            chunk_text (str): Text chunk with embedded timestamps
            
        Returns:
            List[Dict]: List of timestamp ranges with start and end times
        """
        import re
        
        # Pattern to match timestamps like [12.3s-45.6s]
        timestamp_pattern = r'\[(\d+\.?\d*)s-(\d+\.?\d*)s\]'
        matches = re.findall(timestamp_pattern, chunk_text)
        
        timestamps = []
        for start_str, end_str in matches:
            try:
                timestamps.append({
                    'start': float(start_str),
                    'end': float(end_str)
                })
            except ValueError:
                # Skip invalid timestamps
                continue
        
        return timestamps
