import os
import logging
import asyncio
import time
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from crm.services.delete_file_services import DeleteFileServices
from crm.services.pipeline_service import PipelineService
from crm.models.rabbitmq_event_models import (
    ResourceEvent,
    UpdatePermissionsEvent,
    EmbeddingResponse,
    EmbeddingEvent,
)
from crm.configs.constant import UPDATE_PERMISSION_EVENT, EXCHANGE_NAME, EMBEDDING_TASK_QUEUE
from crm.utils.logger import logger
from crm.rabbitmq.producers import rabbitmq_producer
from crm.core.settings import get_settings
from crm.services.embedding_store_service import QdrantEmbeddingStore
import uuid


class EventProcessor:
    """
    Description: Service for processing RabbitMQ events with parallel processing capabilities for file operations and permissions
    
    args:
        max_workers (int): Maximum number of concurrent workers for parallel processing, defaults to 4
    
    returns:
        EventProcessor: Instance for handling file upload, delete, edit, and permission events with async support
    """
    def __init__(self, max_workers: int = 4):
        """
        Description: Initialize EventProcessor with parallel processing capabilities and service dependencies
        
        args:
            max_workers (int): Maximum number of concurrent workers for parallel processing
        
        returns:
            None
        """
        # Initialize services with parallel processing support
        self.max_workers = max_workers
        self.pipeline = PipelineService()
        self.delete_service = DeleteFileServices()
        # Permissions service disabled; no dependency on UpdatePermissionsService
        
        # Executor for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
                
    def process_message(self, message: dict) -> Tuple[bool, float]:   
        """
        Process a single message from RabbitMQ and route to appropriate service (synchronous version)
        
        Args:
            message (dict): Message containing file information
            
        Returns:
            Tuple[bool, float]: (success_status, processing_time_seconds)
        """        
        start_time = time.time()
        success = False
        event_type = None

        try:
            # Check if this is an embedding-related event (different structure)
            event_key = message.get("event") if isinstance(message, dict) else None
            if event_key in ("embedding_response", "event_response", "embeddi_response"):
                event_type = message["event"]
                logger.info(f"Processing special event: {event_type}")
                # Normalize alias so downstream expects the canonical name
                if event_type in ("event_response", "embeddi_response"):
                    message = dict(message)
                    message["event"] = "embedding_response"
                success = self.process_embedding_response(message)
            elif event_key in ("create_embedding", "batch_embedding"):
                event_type = message["event"]
                logger.info(f"Processing embedding consumer event: {event_type}")
                # For now, just log the event as we don't need to process it locally
                # The external embedding consumer will handle these events
                logger.info(f"Received embedding event {event_type} for resource {message.get('resource_id', 'unknown')}")
                success = True  # Successfully "processed" by acknowledging reception
            else:
                try:
                    event_data = ResourceEvent(**message)
                except Exception as e:
                    logger.error(f"Error processing resource event: {e}", exc_info=True)
                    return success, time.time() - start_time
                event_type = event_data.event
                file_path = (event_data.file_path or "").lower()
                # Derive file_type if missing, stripping query params
                base_path = file_path.split("?")[0]
                file_type = event_data.file_type or self._determine_file_type(base_path)
                logger.info(f"File type determined: {file_type}")

                if not event_type:
                    
                    logger.error("No event type provided in message")
                    return success, time.time() - start_time

                logger.info(f"Processing event: {event_type}")
                success = self._route_event(event_type, file_type, event_data)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise

        finally:
            processing_time = time.time() - start_time
            logger.info(
                f"Sync message processing completed for event: {event_type}. "
                f"Processing time: {processing_time:.2f} seconds"
            )
            return success, processing_time

    def __del__(self):
        """Cleanup executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

    def _determine_file_type(self, file_path:str) -> str:
        """
        Determine the file type based on its file extension.
        Args:
            file_path (str): Path or name of the file.
        Returns:
            str: File type as a lowercase string (e.g., "pdf", "docx", "mp4", "zeta").
        """
        logger.info(f"Determining file type for path: {file_path}")
        if not file_path:
            logger.warning("Empty file path provided, defaulting to 'zeta'")
            return "zeta"

        file_path = file_path.lower()
        
        # Check for specific file extensions
        if file_path.endswith('.pdf'):
            return "pdf"
        elif file_path.endswith('.docx'):
            return "docx"
        return "zeta"
        
    def _route_event(self, event: str, file_type: str, event_data: ResourceEvent) -> bool:
        """
        Route the event to the appropriate service based on its type.

        Args:
            event (str): The type of event to process (e.g., "upload_resource").
            file_type (str): Determined file type.
            event_data (ResourceEvent): Parsed event data.

        Returns:
            bool: True if the event was routed and processed successfully, False otherwise.
        """
        if event in ("upload_resource", "create_resource"):
            logger.info("Routing to PipelineService.process_upload")
            self.pipeline.process_upload(event_data, file_type)
            return True

        elif event == "delete_resource":
            logger.info("Routing to DeleteFileServices")
            self.delete_service.delete_embeddings(event_data)
            return True

        elif event == "edit_resource":
            logger.info(f"Routing to PipelineService.process_edit with file type: {file_type}")
            self.pipeline.process_edit(event_data, file_type)
            return True

        return True

    def process_embedding_response(self, message: dict) -> bool:
        """
        Process an embedding response event and store embeddings in Qdrant.

        Args:
            message: The message containing embedding response data

        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Parse the embedding response
            embedding_response = EmbeddingResponse(**message)
            resource_id = embedding_response.resource_id or message.get("resource_id")

            status = (embedding_response.status or "success").lower()
            if status not in {"success", "partial"}:
                logger.warning(
                    "Embedding response reported failure",
                    extra={
                        "resource_id": resource_id,
                        "status": embedding_response.status,
                        "error": embedding_response.error,
                    },
                )
                return False
            chunk_items = list(embedding_response.chunks.items())
            chunk_items.sort(key=lambda item: int(item[0]) if str(item[0]).isdigit() else item[0])
            chunk_payloads = [item[1] for item in chunk_items]

            if not embedding_response.embeddings or not chunk_payloads:
                logger.warning(
                    "Embedding response missing embeddings or chunks; skipping persistence",
                    extra={
                        "resource_id": resource_id,
                        "status": embedding_response.status,
                    },
                )
                return False
            if len(embedding_response.embeddings) != len(chunk_payloads):
                logger.warning(
                    "Embedding/chunk count mismatch",
                    extra={
                        "resource_id": resource_id,
                        "embeddings": len(embedding_response.embeddings),
                        "chunks": len(chunk_payloads),
                    },
                )

            logger.info(
                "Processing embedding response",
                extra={
                    "resource_id": resource_id,
                    "embeddings": len(embedding_response.embeddings),
                    "status": embedding_response.status,
                },
            )

            # Store embeddings in Qdrant
            self.store_received_embeddings(embedding_response)

            logger.info(f"Successfully processed and stored embedding response for resource {resource_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing embedding response: {e}")
            return False

    def store_received_embeddings(self, embedding_response: EmbeddingResponse) -> None:
        """
        Store received embeddings in Qdrant vector database.

        Args:
            embedding_response: The processed embedding response to store
        """
        try:
            store = QdrantEmbeddingStore()
            embeddings = embedding_response.embeddings or []
            chunk_items = list(embedding_response.chunks.items())
            chunk_items.sort(key=lambda item: int(item[0]) if str(item[0]).isdigit() else item[0])
            chunk_payloads = [item[1] for item in chunk_items]
            resource_id = embedding_response.resource_id
            chunk_texts: List[str] = []
            for chunk in chunk_payloads:
                if isinstance(chunk, dict):
                    text_value = chunk.get("text") or chunk.get("content") or ""
                else:
                    text_value = str(chunk)
                chunk_texts.append(text_value)
            logger.info(
                "Received embeddings to persist",
                extra={
                    "resource_id": resource_id,
                    "raw_embeddings": len(embeddings),
                    "raw_chunks": len(chunk_texts),
                },
            )
            # Filter out invalid vectors
            valid_embeddings = []
            valid_chunks = []
            for emb, chunk_text in zip(embeddings, chunk_texts):
                if emb and all(isinstance(x, (int, float)) for x in emb):
                    valid_embeddings.append(emb)
                    valid_chunks.append(chunk_text)

            meta = {
                "user_id": embedding_response.user_id,
                "organization_id": embedding_response.organization_id,
                "embedding_model": embedding_response.model_name or "unknown",
                "processing_time": embedding_response.processing_time or 0.0,
                "status": embedding_response.status or "success",
                "file_name": embedding_response.file_name,
                "file_path": embedding_response.file_path,
                "service_name": embedding_response.service_name,
            }

            logger.info(
                "Persisting filtered embeddings",
                extra={
                    "resource_id": resource_id,
                    "valid_embeddings": len(valid_embeddings),
                },
            )

            count = store.store(
                embeddings=valid_embeddings,
                chunks=valid_chunks,
                resource_id=resource_id,
                file_name=embedding_response.file_name,
                file_path=embedding_response.file_path,
                metadata=meta,
            )
            logger.info(
                "Embeddings persisted successfully",
                extra={
                    "resource_id": resource_id,
                    "stored_embeddings": count,
                },
            )
            logger.info(
                "Embeddings stored in Qdrant",
                extra={
                    "resource_id": resource_id,
                    "stored_embeddings": count,
                },
            )
        except Exception as e:
            logger.error(f"Error storing received embeddings: {e}")
            raise

    def publish_embedding_event(self, task_id: str, resource_id: str,
                                texts: List[str], user_id: str,
                                event_type: str = "create_embedding",
                                callback_url: Optional[str] = None) -> bool:
        """
        Publish an embedding event to RabbitMQ for the external embedding service.

        Args:
            task_id: Unique task identifier for tracking
            resource_id: Resource identifier for the embedding request
            texts: List of text chunks to be embedded
            user_id: User who triggered the embedding process
            event_type: Type of embedding event ('create_embedding', 'batch_embedding', etc.)
            callback_url: Optional callback URL for results

        Returns:
            bool: True if event was published successfully, False otherwise
        """
        try:
            embedding_event = EmbeddingEvent(
                event=event_type,
                task_id=task_id,
                resource_id=resource_id,
                texts=texts,
                callback_url=callback_url,
                user_id=user_id
            )

            # Publish the event to RabbitMQ
            rabbitmq_producer(
                message=embedding_event.dict(),
                exchange_name=EXCHANGE_NAME,
                routing_key=EMBEDDING_TASK_QUEUE
            )

            logger.info(f"Successfully published {event_type} event for resource {resource_id} with {len(texts)} texts")
            return True

        except Exception as e:
            logger.error(f"Failed to publish embedding event for resource {resource_id}: {e}")
            return False
