from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import tempfile
import os
from crm.services.qdrant_services import PDFEmbedder
from crm.utils.qdrand_db import client, ensure_collection_exists
from crm.utils.embedder import embedder
from crm.core.settings import get_settings
from crm.utils.logger import logger
from crm.rabbitmq.producers import rabbitmq_producer
from crm.configs.constant import EXCHANGE_NAME, EMBEDDING_TASK_QUEUE
import uuid

router = APIRouter()
settings = get_settings()


@router.post("/documents/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF and queue its extracted content for embedding.

    When available, convert pages to images and run OpenAI extraction so the
    background embedding worker receives richer Markdown text. Falls back to
    local PDF splitting if OpenAI is unavailable.
    """
    logger.info("Upload request received", extra={
        "upload_filename": file.filename,
        "content_type": getattr(file, "content_type", None),
    })

    if not file.filename.lower().endswith(".pdf"):
        logger.warning("Rejected upload: unsupported extension", extra={
            "upload_filename": file.filename,
        })
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Only .pdf files are supported by this endpoint"
        })

    tmp_path = ""
    content: bytes = b""
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        logger.info("Saved upload to temporary file", extra={
            "upload_filename": file.filename,
            "tmp_path": tmp_path,
            "bytes": len(content),
        })
    except Exception as save_error:
        logger.error("Failed to save uploaded file", exc_info=True, extra={
            "upload_filename": file.filename,
        })
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": f"Failed to save uploaded file: {save_error}"
        })

    try:
        service = PDFEmbedder(
            collection_name=settings.COLLECTION_NAME,
            client=client,
            embedder=embedder,
        )

        texts: list[str] = []
        extraction_method = "openai_document_to_images"
        try:
            from crm.services.openai_extraction_services import document_to_images

            logger.info("Attempting OpenAI extraction", extra={
                "upload_filename": file.filename,
                "tmp_path": tmp_path,
                "extraction_method": extraction_method,
            })

            extracted_content = document_to_images(tmp_path)
            if isinstance(extracted_content, str):
                texts = service.token_splitter.split_text(extracted_content)
            elif isinstance(extracted_content, list):
                texts = [chunk for chunk in extracted_content if isinstance(chunk, str)]
            else:
                raise ValueError("Unsupported return from document_to_images")

            if not texts:
                raise ValueError("OpenAI extraction returned no chunks")

            logger.info("OpenAI extraction succeeded", extra={
                "upload_filename": file.filename,
                "tmp_path": tmp_path,
                "chunks": len(texts),
            })
        except Exception as extraction_error:
            extraction_method = "pypdf_loader_fallback"
            logger.warning(
                "OpenAI extraction unavailable; falling back to local PDF splitter",
                extra={
                    "upload_filename": file.filename,
                    "tmp_path": tmp_path,
                    "error": str(extraction_error),
                },
            )
            docs = service.load_and_split_pdf(tmp_path)
            texts = [d.page_content for d in docs]
            logger.info("Fallback PDF splitter produced chunks", extra={
                "upload_filename": file.filename,
                "tmp_path": tmp_path,
                "chunks": len(texts),
            })

        if not texts:
            logger.error("Extraction produced no text chunks", extra={
                "upload_filename": file.filename,
                "tmp_path": tmp_path,
                "extraction_method": extraction_method,
            })
            return JSONResponse(
                status_code=422,
                content={
                    "status": "error",
                    "message": "Unable to extract any text from the uploaded PDF",
                },
            )

        task_id = uuid.uuid4().hex
        resource_id = uuid.uuid4().hex
        message = {
            "event": "create_embedding",
            "task_id": task_id,
            "resource_id": resource_id,
            "texts": texts,
            # Extra helpful metadata for the embedding worker (optional fields)
            "file_name": file.filename,
            "file_path": tmp_path,
            "extraction_method": extraction_method,
        }
        if extraction_method == "openai_document_to_images":
            openai_model = getattr(settings, "OPENAI_EXTRACT_CONTENT_MODEL", None)
            if openai_model:
                message["openai_model"] = openai_model

        logger.info("Publishing embedding task", extra={
            "task_id": task_id,
            "resource_id": resource_id,
            "chunks": len(texts),
            "extraction_method": extraction_method,
        })
        rabbitmq_producer(message, EXCHANGE_NAME, routing_key=EMBEDDING_TASK_QUEUE)

        logger.info("Upload accepted and task queued", extra={
            "task_id": task_id,
            "resource_id": resource_id,
            "collection": settings.COLLECTION_NAME,
        })

        return JSONResponse(status_code=202, content={
            "status": "accepted",
            "message": f"Embedding task queued for '{file.filename}'",
            "task_id": task_id,
            "resource_id": resource_id,
            "chunks": len(texts),
            "collection": settings.COLLECTION_NAME,
        })
    except Exception as ingest_error:
        logger.error("Failed to ingest PDF", exc_info=True, extra={
            "upload_filename": file.filename,
            "tmp_path": tmp_path,
        })
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": f"Failed to ingest PDF: {ingest_error}",
        })
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
                logger.info("Temporary file removed", extra={
                    "tmp_path": tmp_path,
                })
        except Exception as cleanup_error:
            logger.warning("Failed to remove temporary file", extra={
                "tmp_path": tmp_path,
                "error": str(cleanup_error),
            })
