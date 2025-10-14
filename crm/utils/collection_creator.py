from crm.utils.qdrand_db import client
from qdrant_client.models import VectorParams, Distance
from crm.utils.logger import logger

def ensure_qdrant_collection_exists(collection_name: str, embedding_dim: int = 768):
    """
    Description: Ensure a Qdrant collection exists with specified embedding dimensions, create it if not found
    
    args:
        collection_name (str): Name of the Qdrant collection to check or create
        embedding_dim (int): Dimension of the embedding vectors, defaults to 768
    
    returns:
        None: Creates collection if needed, prints status messages
    """
    collections = client.get_collections().collections
    if not any(c.name == collection_name for c in collections):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=embedding_dim,
                distance=Distance.COSINE
            )
        )
        logger.info(f"✅ Collection '{collection_name}' created.")
    else:
        logger.info(f"ℹ️ Collection '{collection_name}' already exists.")
