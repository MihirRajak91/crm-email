from __future__ import annotations

"""
Embedding task submission service for event-driven workflows.

This service does NOT perform local embedding. It extracts (if needed)
and publishes text chunks to RabbitMQ as `create_embedding` events.

An external embedding worker should consume those events and respond with
an `embedding_response` event that this app will store in Qdrant via
EventProcessor.store_received_embeddings.
"""

from typing import List, Optional, Dict, Any
import uuid

from crm.utils.logger import logger
from crm.core.settings import get_settings
from crm.configs.constant import EXCHANGE_NAME, EMBEDDING_TASK_QUEUE
from crm.rabbitmq.producers import rabbitmq_producer

# Reuse existing document loaders
from crm.services.qdrant_services import PDFEmbedder
from crm.utils.qdrand_db import client as qdrant_client
from crm.utils.embedder import embedder as local_embedder  # only to satisfy PDFEmbedder init


class EmbeddingTaskService:
    def __init__(self, exchange_name: str = EXCHANGE_NAME) -> None:
        self.exchange_name = exchange_name
        self.settings = get_settings()

    def queue_texts(
        self,
        texts: List[str],
        *,
        resource_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        routing_key: str = EMBEDDING_TASK_QUEUE,
    ) -> Dict[str, Any]:
        """Publish a `create_embedding` task for the given text chunks."""
        if not texts:
            raise ValueError("No texts provided to queue for embedding")

        task_id = uuid.uuid4().hex
        rid = resource_id or uuid.uuid4().hex

        message: Dict[str, Any] = {
            "event": "create_embedding",
            "task_id": task_id,
            "resource_id": rid,
            "texts": texts,
            "chunks": texts,
        }
        if file_name:
            message["file_name"] = file_name
        if file_path:
            message["file_path"] = file_path
        if user_id:
            message["user_id"] = user_id
        if organization_id:
            message["organization_id"] = organization_id

        rabbitmq_producer(message, self.exchange_name, routing_key=routing_key)
        logger.info(
            f"Queued embedding task: task_id={task_id} resource_id={rid} chunks={len(texts)} routing_key={routing_key}"
        )

        return {
            "status": "accepted",
            "task_id": task_id,
            "resource_id": rid,
            "chunks": len(texts),
            "collection": self.settings.COLLECTION_NAME,
        }

    def queue_document(
        self,
        file_path: str,
        *,
        file_type: str = "pdf",
        resource_id: Optional[str] = None,
        file_name: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        routing_key: str = EMBEDDING_TASK_QUEUE,
    ) -> Dict[str, Any]:
        """
        Extract text from a document (pdf/docx/html) and queue an embedding task.
        """
        loader = PDFEmbedder(
            collection_name=self.settings.COLLECTION_NAME,
            client=qdrant_client,
            embedder=local_embedder,
        )

        if file_type == "pdf":
            docs = loader.load_and_split_pdf(file_path)
        elif file_type == "docx":
            docs = loader.load_and_split_docx(file_path)
        elif file_type in ("html", "zeta"):
            docs = loader.load_and_split_html(file_path)
        else:
            raise ValueError(f"Unsupported file_type: {file_type}")

        texts = [d.page_content for d in docs]
        return self.queue_texts(
            texts,
            resource_id=resource_id,
            file_name=file_name,
            file_path=file_path,
            user_id=user_id,
            organization_id=organization_id,
            routing_key=routing_key,
        )
