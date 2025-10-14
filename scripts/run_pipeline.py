#!/usr/bin/env python3
"""
End-to-end pipeline runner for event-driven flow.

Capabilities:
- Extract a document (pdf/docx/html) into chunks (no local embedding)
- Queue an embedding task via RabbitMQ (create_embedding)
- Optionally simulate embedding locally and store into Qdrant (for dev)
- Compose a status-aware email grounded on stored docs (direct service call)

Examples:

  # Queue embedding task only
  poetry run python scripts/run_pipeline.py \
    --file /path/to/file.pdf --file-type pdf --queue-only

  # Simulate end-to-end (embed locally, store, then compose)
  poetry run python scripts/run_pipeline.py \
    --file "/home/zeta/Downloads/eng_docuements/pdf/engineering_guides_3 (1).pdf" \
    --file-type pdf \
    --status new --past-email "Intro email body" \
    --simulate
"""

import argparse
import asyncio
from typing import List

from crm.services.embedder_service import EmbeddingTaskService
from crm.services.embedding_store_service import QdrantEmbeddingStore
from crm.services.qdrant_services import PDFEmbedder
from crm.utils.qdrand_db import client as qdrant_client
from crm.utils.embedder import embedder as local_embedder
from crm.services.email_composer_service import EmailComposerService
from crm.models.email_models import ComposeEmailRequest, EmailThreadMessage, StatusEnum
from crm.core.settings import get_settings


async def simulate_embedding_and_store(texts: List[str]) -> int:
    """Generate embeddings locally and store them into Qdrant (dev aid)."""
    embeddings = await local_embedder.encode(texts)
    store = QdrantEmbeddingStore()
    return store.store(embeddings=embeddings, chunks=texts)


def main() -> None:
    p = argparse.ArgumentParser(description="CRM pipeline runner (event-driven or simulated)")
    p.add_argument("--file", help="Path to document (pdf/docx/html)")
    p.add_argument("--file-type", default="pdf", choices=["pdf", "docx", "html"], help="Document type")
    p.add_argument("--queue-only", action="store_true", help="Only queue embedding task, do not simulate or compose")
    p.add_argument("--simulate", action="store_true", help="Simulate embedding locally and store to Qdrant")

    # Compose options
    p.add_argument("--status", choices=["new", "contacted", "qualified", "lost"], help="Email status")
    p.add_argument("--past-email", dest="past_email", help="First email body in the thread")
    p.add_argument("--latest-email", dest="latest_email", help="Most recent email body in the thread")
    p.add_argument("--recipient-name", dest="recipient_name")
    p.add_argument("--recipient-company", dest="recipient_company")
    p.add_argument("--top-k", type=int, default=6)

    args = p.parse_args()
    settings = get_settings()

    # Step 1: Extract document into text chunks (if file given)
    texts: List[str] = []
    if args.file:
        loader = PDFEmbedder(collection_name=settings.COLLECTION_NAME, client=qdrant_client, embedder=local_embedder)
        if args.file_type == "pdf":
            docs = loader.load_and_split_pdf(args.file)
        elif args.file_type == "docx":
            docs = loader.load_and_split_docx(args.file)
        else:
            docs = loader.load_and_split_html(args.file)
        texts = [d.page_content for d in docs]
        print(f"Extracted {len(texts)} chunks from {args.file}")

    # Step 2: Queue embedding task via RMQ
    if args.file and not args.simulate:
        svc = EmbeddingTaskService()
        resp = svc.queue_texts(texts, file_name=args.file, file_path=args.file)
        print(f"Queued embedding task: {resp}")
        if args.queue_only:
            return

    # Step 3: Simulate embedding + store (dev aid)
    if args.simulate:
        count = asyncio.run(simulate_embedding_and_store(texts))
        print(f"Stored {count} chunks into Qdrant")

    # Step 4: Compose email (direct call)
    if args.status:
        composer = EmailComposerService()
        thread: List[EmailThreadMessage] = []
        if args.past_email:
            thread.append(EmailThreadMessage(subject=None, body=args.past_email))
        if args.latest_email:
            thread.append(EmailThreadMessage(subject=None, body=args.latest_email))

        req = ComposeEmailRequest(
            status=StatusEnum(args.status),
            past_emails=thread,
            recipient_name=args.recipient_name,
            recipient_company=args.recipient_company,
            top_k=args.top_k,
        )
        resp = asyncio.run(composer.compose(req))
        print("\n=== Composed Email ===")
        print("Subject:", resp.subject)
        print("\nBody:\n", resp.body)


if __name__ == "__main__":
    main()
