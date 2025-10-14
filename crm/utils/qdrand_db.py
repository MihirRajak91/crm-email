import os
import time
import socket
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
# from crm.configs.collection_name_configs import COLLECTION_NAME
from crm.core.settings import get_settings
from crm.utils.logger import logger

settings = get_settings()
COLLECTION_NAME = settings.COLLECTION_NAME

def wait_for_qdrant(host: str = "", port: int = "",
                    retries: int = 10, delay: int = 2) -> None:
    """
    Description: Wait until Qdrant is reachable via TCP connection with retry logic
    
    args:
        host (str): Qdrant host address, defaults to DEFAULT_QDRANT_HOST
        port (int): Qdrant port number, defaults to DEFAULT_QDRANT_PORT
        retries (int): Number of connection attempts, defaults to 10
        delay (int): Delay between attempts in seconds, defaults to 2
    
    returns:
        None: Returns when connection successful, raises ConnectionError if all retries fail
    """
    for attempt in range(1, retries + 1):
        try:
            with socket.create_connection((host, port), timeout=2):
                logger.info(f"Qdrant is reachable at {host}:{port}")
                return
        except Exception:
            logger.error(f"Waiting for Qdrant ({host}:{port})... attempt {attempt}/{retries}")
            time.sleep(delay)
    raise ConnectionError(f"Could not connect to Qdrant at {host}:{port}")


def ensure_collection_exists(client: QdrantClient, collection_name: str,
                             embedding_dim: int = settings.EMBEDDING_DIM) -> None:
    """
    Description: Create the collection in Qdrant if it doesn't already exist with COSINE distance
    
    args:
        client (QdrantClient): Initialized Qdrant client instance
        collection_name (str): Name of the collection to check/create
        embedding_dim (int): Dimensionality of vectors, defaults to DEFAULT_EMBEDDING_DIM
    
    returns:
        None: Creates collection if needed, prints status messages
    """
    existing_collections = {col.name for col in client.get_collections().collections}
    if collection_name in existing_collections:
        logger.info(f"Collection '{collection_name}' already exists.")
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=embedding_dim,
            distance=Distance.COSINE
        )
    )
    logger.info(f"Collection '{collection_name}' created.")


def initialize_qdrant(host: str = settings.QDRANT_HOST,
                      port: int = settings.QDRANT_PORT,
                      collection_name: str = COLLECTION_NAME,
                      embedding_dim: int = settings.EMBEDDING_DIM) -> QdrantClient:
    """
    Description: Initialize Qdrant client and ensure required collection exists with full setup
    
    args:
        host (str): Qdrant host address, defaults to DEFAULT_QDRANT_HOST
        port (int): Qdrant port number, defaults to DEFAULT_QDRANT_PORT
        collection_name (str): Name of the collection to ensure exists, defaults to configured collection_name
        embedding_dim (int): Dimensionality of vectors, defaults to DEFAULT_EMBEDDING_DIM
    
    returns:
        QdrantClient: Initialized and verified client with collection ready for use
    """
    wait_for_qdrant(host=host, port=port)
    # Disable compatibility check to avoid noisy warnings in mixed environments
    try:
        client = QdrantClient(host=host, port=port, prefer_grpc=False, timeout=5.0, check_compatibility=False)  # type: ignore
    except TypeError:
        # Older client without check_compatibility parameter
        client = QdrantClient(host=host, port=port)

    # Optionally skip collection ensure to avoid crashing when storage is locked/corrupted
    if not settings.QDRANT_SKIP_COLLECTION_INIT:
        try:
            ensure_collection_exists(client, collection_name, embedding_dim)
        except Exception as e:
            logger.error(f"Failed to ensure collection '{collection_name}': {e}")
            logger.warning("Proceeding without ensuring collection. Queries may fail if collection is missing.")
    else:
        logger.info("Skipping Qdrant collection initialization as per settings.")

    return client


client = initialize_qdrant(
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT,
    embedding_dim=settings.EMBEDDING_DIM,
    collection_name=COLLECTION_NAME
)
