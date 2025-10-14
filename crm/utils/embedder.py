import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Union, Optional
# from sentence_transformers import SentenceTransformer
from crm.utils.logger import logger
import numpy as np
from openai import OpenAI
from crm.core.settings import get_settings

settings = get_settings()

# OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
# LOCAL_EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"

class AsyncEmbedder:
    """
    Enhanced embedder with batch processing and async support
    """
    def __init__(
        self, 
        model_name: str = settings.EMBEDDING_MODEL, 
        max_workers: int = 2,
        normalize:bool = True,
        use_openai:bool = True
    ):
        """
        Initialize the embedder with async capabilities
        
        Args:
            model_name (str): Name of the sentence transformer model
            max_workers (int): Maximum number of worker threads for embedding generation
        """
        self.use_openai = use_openai
        self.normalize = normalize
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"[Embedder Init] model={model_name} use_openai={self.use_openai}")

        if self.use_openai:
            self.openai_model = model_name
            # Use API key from app settings so we don't depend on shell env
            api_key = settings.OPENAI_API_KEY
            if not api_key:
                logger.error("[Embedder] OPENAI_API_KEY is not set in settings")
            self.client = OpenAI(api_key=api_key)
            logger.info(f"[Embedder] Using OpenAI model: {self.openai_model}")
        # else:
        #     self.model = SentenceTransformer(model_name, trust_remote_code=True)
        #     logger.info(f"[Embedder] Using local model: {self.model}")

    def _normalize_embeddings(self, vectors: List[List[float]]) -> List[List[float]]:
        """
        Normalize embedding vectors
        """
        vectors = np.array(vectors)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return (vectors/norms).tolist()
    
    def _encode_local(self, texts: List[str], batch_size:int=32) -> List[List[float]]:
        """
        Synchronous handling of encode operations locally
        """
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeds = self.model.encode(
                batch,
                convert_to_tensor=False,
                normalize_embeddings=self.normalize,
                show_progress_bar=False
            )
            embeddings.extend(batch_embeds)
        return embeddings

    def _encode_openai(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            input=texts,
            model=self.openai_model
        )
        embeddings = [r.embedding for r in response.data]
        return embeddings
    
    async def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> Union[List[float], List[List[float]]]:
        """
        Async-compatible embedding method
        """
        if isinstance(texts, str):
            texts = [texts]

        loop = asyncio.get_event_loop()
        if self.use_openai:
            embeds = await loop.run_in_executor(self.executor, self._encode_openai, texts)
        else:
            embeds = await loop.run_in_executor(self.executor, self._encode_local, texts, batch_size)

        return embeds        
    
    def __del__(self):
        """Cleanup executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


logger.info(f"USE OPENAI: {settings.USE_OPENAI}")
# Create enhanced embedder instance
embedder = AsyncEmbedder(model_name=settings.EMBEDDING_MODEL, use_openai=settings.USE_OPENAI)

# # embedding_model = os.getenv("EMBEDDING_MODEL", None)
# if embedding_model == "local":
#     embedder = AsyncEmbedder(model_name=LOCAL_EMBEDDING_MODEL, use_openai=False)
# else:
#     logger.error(f"[Embedder] Invalid EMBEDDING_MODEL value: {embedding_model}")
    
