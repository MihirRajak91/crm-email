from __future__ import annotations

"""
QdrantEmbeddingStore

Small service that upserts embedding vectors + chunk texts into a Qdrant collection.
Intended for event-driven workflows where an external worker produces embeddings
and this service persists them.
"""

from typing import List, Dict, Any, Optional
import uuid
import time

from qdrant_client.models import PointStruct

from crm.utils.logger import logger
from crm.core.settings import get_settings
from crm.utils.qdrand_db import client as qdrant_client, ensure_collection_exists


class QdrantEmbeddingStore:
    def __init__(
        self,
        collection_name: Optional[str] = None,
        embedding_dim: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self.collection = collection_name or settings.COLLECTION_NAME
        self.embedding_dim = embedding_dim or settings.EMBEDDING_DIM
        self.client = qdrant_client

    def ensure_collection(self) -> None:
        """Ensure target collection exists with correct vector size and cosine distance."""
        try:
            ensure_collection_exists(self.client, self.collection, self.embedding_dim)
        except Exception as e:
            logger.warning(f"Could not ensure collection '{self.collection}': {e}")

    def store(
        self,
        embeddings: List[List[float]],
        chunks: List[str],
        *,
        resource_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Upsert vectors + payloads into Qdrant.

        Returns number of points upserted.
        """
        if not embeddings:
            logger.warning("No embeddings provided to store()")
            return 0
        if not chunks:
            logger.warning("No chunks provided to store()")
            return 0

        logger.info(
            "Preparing to store embeddings",
            extra={
                "collection": self.collection,
                "embeddings": len(embeddings),
                "chunks": len(chunks),
                "resource_id": resource_id,
            },
        )

        self.ensure_collection()

        rid = resource_id or uuid.uuid4().hex
        ts = int(time.time())
        points: List[PointStruct] = []

        total = min(len(embeddings), len(chunks))
        for i in range(total):
            vec = embeddings[i]
            txt = chunks[i]
            if not isinstance(vec, list) or not vec:
                logger.debug(f"Skipping invalid vector at index {i}")
                continue

            payload: Dict[str, Any] = {
                "resource_id": rid,
                "chunk_id": i,
                "chunk_index": i,
                "total_chunks": total,
                "text": txt,
                "timestamp": ts,
                "embedding_dimension": len(vec),
            }
            if file_name:
                payload["file_name"] = file_name
            if file_path:
                payload["file_path"] = file_path
            if metadata:
                payload.update(metadata)

            points.append(
                PointStruct(
                    id=uuid.uuid4().hex,
                    vector=vec,
                    payload=payload,
                )
            )

        if not points:
            logger.warning("No valid points to upsert")
            return 0

        upsert_start = time.perf_counter()
        self.client.upsert(collection_name=self.collection, points=points)
        upsert_duration = time.perf_counter() - upsert_start
        logger.info(
            "Embeddings stored in Qdrant",
            extra={
                "collection": self.collection,
                "points": len(points),
                "resource_id": rid,
                "duration_sec": round(upsert_duration, 3),
            },
        )
        return len(points)
