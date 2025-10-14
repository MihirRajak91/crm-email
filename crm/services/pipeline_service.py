from __future__ import annotations

"""
PipelineService

Orchestrates event-driven document ingestion steps:
- For upload/create: extract text from file and publish an embedding task via RabbitMQ.
- For edit: delete old embeddings for the resource, then queue a fresh embedding task.

This service composes existing smaller services and keeps EventProcessor lean.
"""

from typing import Optional
from crm.utils.logger import logger
from crm.core.settings import get_settings
from crm.services.embedder_service import EmbeddingTaskService
from crm.services.delete_file_services import DeleteFileServices
from crm.services.qdrant_services import PDFEmbedder
from crm.utils.qdrand_db import client as qdrant_client
from crm.utils.embedder import embedder as local_embedder
from crm.models.rabbitmq_event_models import ResourceEvent


class PipelineService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.embed_queue = EmbeddingTaskService()
        self.delete_service = DeleteFileServices()

    def _detect_file_type(self, file_path: str, default: str = "zeta") -> str:
        path = (file_path or "").lower()
        if path.endswith(".pdf"):
            return "pdf"
        if path.endswith(".docx"):
            return "docx"
        if path.endswith(".html") or path.endswith(".htm"):
            return "zeta"
        return default

    def _extract_texts(self, file_path: str, file_type: str):
        loader = PDFEmbedder(
            collection_name=self.settings.COLLECTION_NAME,
            client=qdrant_client,
            embedder=local_embedder,
        )
        if file_type == "pdf":
            docs = loader.load_and_split_pdf(file_path)
        elif file_type == "docx":
            docs = loader.load_and_split_docx(file_path)
        else:
            docs = loader.load_and_split_html(file_path)
        return [d.page_content for d in docs]

    def process_upload(self, event: ResourceEvent, file_type: Optional[str] = None) -> None:
        ft = file_type or event.file_type or self._detect_file_type(event.file_path)
        texts = self._extract_texts(event.file_path, ft)
        logger.info(f"Extracted {len(texts)} chunks for upload/create | resource_id={event.resource_id}")
        self.embed_queue.queue_texts(
            texts,
            resource_id=str(event.resource_id),
            file_name=str(event.file_name),
            file_path=str(event.file_path),
            user_id=str(event.user_id),
            organization_id=str(event.organization_id),
        )

    def process_edit(self, event: ResourceEvent, file_type: Optional[str] = None) -> None:
        # Delete existing embeddings for the resource
        try:
            self.delete_service.delete_embeddings(event)
        except Exception as e:
            logger.warning(f"Failed to delete existing embeddings for edit: {e}")

        # Re-ingest
        self.process_upload(event, file_type=file_type)

