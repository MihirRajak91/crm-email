import os
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Dict, List, Optional
from crm.services.downlaod_store_services import MetadataProcessor
from crm.services.qdrant_services import PDFEmbedder
from crm.utils.qdrand_db import client
from crm.utils.embedder import embedder
# from crm.configs.collection_name_configs import COLLECTION_NAME
from crm.core.settings import get_settings
from crm.models.rabbitmq_event_models import ResourceEvent
from crm.utils.logger import logger
import inspect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
rag_dir = os.path.join(BASE_DIR,"..","..","rag_documents")
settings = get_settings()
COLLECTION_NAME = settings.COLLECTION_NAME

class AddFileServices:
    """
    Description: Service for adding files to the system with parallelization support for PDF, DOCX, Zeta, and MP4 files
    
    args:
        output_dir (str): Directory where files will be saved, defaults to rag_documents
        max_workers (int): Maximum number of concurrent workers, defaults to 4
    
    returns:
        AddFileServices: Instance for handling file processing and embedding operations
    """
    def __init__(self, output_dir: str = rag_dir, max_workers: int = 4):
        """
        Description: Initialize AddFileServices with parallel processing capabilities for file handling and embedding
        
        args:
            output_dir (str): Directory where files will be saved
            max_workers (int): Maximum number of concurrent workers for parallelization
        
        returns:
            None
        """
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.pdf_files: List[dict] = []
        self.zeta_files: List[dict] = []
        self.docx_files: List[dict] = []
        
        # Initialize processors
        self.metadata_processor = MetadataProcessor(output_dir=self.output_dir)
        logger.info(f"Collection Name for the storage : {COLLECTION_NAME}")
        self.embedder = PDFEmbedder(
            collection_name=COLLECTION_NAME,
            client=client,
            embedder=embedder
        )
        # Transcription disabled: no dependency on VideoTranscriber
        
        # Thread pools for I/O bound operations
        self.io_executor = ThreadPoolExecutor(max_workers=max_workers)
        # Process pool for CPU-intensive embedding operations
        self.cpu_executor = ProcessPoolExecutor(max_workers=max_workers//2)

    def _process_file_by_type(self, file_info: dict, file_type: str) -> Optional[str]:
        """
        Description: Helper method to process file by type using appropriate processor in thread pool
        
        args:
            file_info (dict): File metadata containing file information
            file_type (str): Type of file (pdf/docx/zeta/mp4)
        
        returns:
            Optional[str]: Path to processed file or None if processing fails
        """
        if file_type == "pdf":
            return self.metadata_processor.process_pdf(file_info)
        elif file_type == "docx":
            return self.metadata_processor.process_docx(file_info)
        elif file_type == "zeta":
            return self.metadata_processor.process_zeta(file_info)
        else:
            logger.error(f"Unsupported file type: {file_type}")
            return None

    def process_file(self, event: ResourceEvent, file_type: str) -> None:
        """
        Description: Process a single file based on its type (synchronous version for backward compatibility)
        
        args:
            event (ResourceEvent): File event containing metadata
            file_type (str): Type of file (pdf/docx/zeta/mp4)
        
        returns:
            None: Raises exception on failure, logs success on completion
        """
        try:
            logger.info(f"Processing {file_type.upper()} file: {event.file_name}")
            
            files_local_path = self._process_file_by_type(event, file_type)
            
            if files_local_path:
                asyncio.run(self.embedder.process_file(
                    file_path=files_local_path,
                    meta_data=event,
                    file_type=file_type
                ))

                # Cleanup: delete local file after successful embedding if it resides under output_dir
                try:
                    abs_saved_path = os.path.abspath(files_local_path)
                    abs_output_dir = os.path.abspath(self.output_dir)
                    if os.path.commonpath([abs_saved_path, abs_output_dir]) == abs_output_dir and os.path.exists(abs_saved_path):
                        os.remove(abs_saved_path)
                        logger.info(f"Deleted local file after embedding: {abs_saved_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to delete local file after embedding: {files_local_path} | Error: {cleanup_error}")


                logger.info(f"Successfully processed {file_type.upper()} file: {event.file_name}")
            else:
                logger.error(f"Failed to process {file_type.upper()} file: {event.file_name}")

        except Exception as e:
            logger.error(f"Error processing {file_type} file {event.file_name}: {e}")
            raise

    @property
    def file_counts(self) -> dict:
        """
        Description: Get count of files by type currently in processing lists
        
        args:
            None
        
        returns:
            dict: Dictionary with counts for each file type (pdf, docx, zeta)
        """
        return {
            "pdf": len(self.pdf_files),
            "docx": len(self.docx_files),
            "zeta": len(self.zeta_files)
        }
