import hashlib
import json
import numpy as np
from typing import List, Optional
from crm.configs.redis_config import redis_service
from crm.utils.embedder import embedder
from crm.utils.logger import logger

REDIS_CACHE_PREFIX = "chatcache:"
EMBED_CACHE_PREFIX = "embedcache:"
COSINE_SIMILARITY_THRESHOLD = 0.90

class ChatCache:
    """
    Description: Redis-based caching service for conversation responses with semantic fingerprinting and access control
    
    args:
        None (initialized with Redis connection from service)
    
    returns:
        ChatCache: Instance for managing conversation caching operations
    """

    def __init__(self):
        """
        Description: Initialize the chat cache with Redis client connection
        
        args:
            None
        
        returns:
            None
        """
        self.redis = redis_service.get_redis_client()
        # self.ttl = 3600  # Cache expiration time in seconds (1 hour)

    async def generate_questions_semantic_fingerprint(self, question: str, embedding: Optional[np.ndarray] = None) -> str:
        """
        Generate a semantic fingerprint for the given question using embeddings and SHA256 hashing.

        Args:
            question (str): The question text for which to generate a semantic fingerprint.
            embedding (np.ndarray, optional): The embedding vector of the question. If not provided, it will be computed.

        Returns:
            str: A SHA256 hash of the rounded embedding vector used for semantic similarity matching.
        """
        if embedding is None:
            embedding = await embedder.encode(question)
        rounded_vector = np.round(embedding, 2)
        return hashlib.sha256(rounded_vector.tobytes()).hexdigest()

    async def generate_cache_key(self, question: str, organization_id: str, doc_fingerprint: str = "", embedding: Optional[np.ndarray] = None) -> str:
        """
        Generate a unique cache key by combining the semantic fingerprint, organization ID, and document fingerprint.

        Args:
            question (str): The question text used for generating the semantic fingerprint.
            organization_id (str): The organization identifier to ensure scope isolation for caching.
            doc_fingerprint (str, optional): The document fingerprint used for version control. Defaults to an empty string.
            embedding (np.ndarray, optional): The embedding vector of the question. If not provided, it will be computed.

        Returns:
            str: A unique cache key, including a Redis prefix, for efficient storage and retrieval.
        """
        semantic_fingerprint = await self.generate_questions_semantic_fingerprint(question, embedding)
        key = f"{semantic_fingerprint}:{organization_id}:{doc_fingerprint}"
        return REDIS_CACHE_PREFIX + hashlib.sha256(key.encode()).hexdigest()
    
    def check_access(self, user_id: str, user_roles: List[str], result: dict) -> bool:
        """
        Description: Check if user has access to cached result based on organization, role, or user-specific permissions
        
        args:
            user_id (str): User identifier to check access for
            user_roles (List[str]): List of user roles for role-based access
            result (dict): Cached result containing access control information
        
        returns:
            bool: True if user has access through any permission level, False otherwise
        """
        # 1. Org-wide access
        if result.get("is_org_wide", False):
            return True

        # 2. Role-based access
        allowed_roles = result.get("allowed_roles", [])
        if set(user_roles) & set(allowed_roles):
            return True

        # 3. User-specific access
        allowed_user_ids = result.get("allowed_user_ids", [])
        if user_id in allowed_user_ids:
            return True

        return False

    def check_access_in_list(self, user_id: str, result: dict) -> bool:
        """
        Check if the user ID exists in the allowed user list for simplified access control.

        Args:
            user_id (str): The user identifier to check against the allowed user list.
            result (dict): A cached result containing a list of allowed user IDs under the key 'allowed_user_ids'.

        Returns:
            bool: True if the user ID is in the allowed user list, False otherwise.
        """
        allowed_user_ids = result.get("allowed_user_ids", [])
        return user_id in allowed_user_ids

    async def get_conversation(
        self,
        question: str,
        organization_id: str,
        user_id: str,
        user_roles: List[str],
        doc_fingerprint: str = "",
        embedding: Optional[np.ndarray] = None
    ) -> Optional[dict]:
        """
        Retrieves the conversation for the provided question and context.

        Args:
            question (str): The question asked by the user.
            organization_id (str): The ID of the organization the user belongs to.
            user_id (str): The ID of the user asking the question.
            user_roles (List[str]): List of roles the user holds within the organization.
            doc_fingerprint (str, optional): The fingerprint of the document from the Qdrant database. Defaults to an empty string.
            embedding (np.ndarray, optional): The embedding array for the question. Defaults to None.

        Returns:
            Optional[dict]: A dictionary containing the conversation data, or None if no conversation was found.
        """
        # Try strict match
        cache_key = await self.generate_cache_key(question, organization_id, doc_fingerprint, embedding)
        # print('*'*20)
        # print("Generated Cache Key:", cache_key)
        # print("User ID:", user_id)
        # print("User Roles:", user_roles)

        cached_data = self.redis.get(cache_key)
        # print("Cached Data:", cached_data)
        # print('*'*20)

        if cached_data:
            result = json.loads(cached_data)
            if self.check_access(user_id, user_roles, result):
                return result
            
        # Soft match using cosine similarity
        if embedding is None:
            embedding = await embedder.encode(question)
        for key in self.redis.scan_iter(f"{REDIS_CACHE_PREFIX}*"):
            value = self.redis.get(key)
            if value:
                try:
                    data = json.loads(value)
                    cached_embedding = np.array(data.get("embedding", []))
                    if cached_embedding.any():
                        sim = self._cosine_similarity(embedding, cached_embedding)
                        if sim >= COSINE_SIMILARITY_THRESHOLD and self.check_access(user_id, user_roles, data):
                            logger.info(f"Similarity betwen vector : {sim}")
                            return data
                except Exception:
                    continue

        return None

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between given two vector
        Args:
            vec1 (np.ndarray) : Vector 1 for the similarity check
            vec2 (np.ndarray) : Vector 2 for the similarity check
        Returns:
            similarity score (float)
        """
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    async def set_conversation(
        self, 
        question: str, 
        organization_id: str, 
        doc_fingerprint: str = "", 
        conversation_data: Optional[dict] = None,
        embedding: Optional[np.ndarray] = None
    ):
        """
        Store conversation data in the cache, associating it with a question, organization, and optional document fingerprint.

        Args:
            question (str): The question text associated with the conversation.
            organization_id (str): The organization identifier for scoping the conversation.
            doc_fingerprint (str, optional): A fingerprint for the document related to the conversation. Defaults to an empty string.
            conversation_data (dict, optional): The conversation data (e.g., user history, context) to store in the cache.
            embedding (np.ndarray, optional): An optional embedding vector of the question to help with similarity matching.

        Returns:
            None
        """
        if conversation_data is None:
            conversation_data = {}
        if embedding is None:
            embedding = await embedder.encode(question)
        conversation_data["embedding"] = embedding.tolist()
        cache_key = await self.generate_cache_key(question, organization_id, doc_fingerprint, embedding)
        self.redis.set(cache_key, json.dumps(conversation_data))
        # self.redis.setex(cache_key, self.ttl, json.dumps(conversation_data))  # to use TTL

    def invalidate_cache_by_resource_id(self, resource_id: str):
        """
        Invalidate the cache for a specific resource by its identifier.

        Args:
            resource_id (str): The identifier of the resource whose cache should be invalidated.

        Returns:
            None
        """
        keys_to_delete = []
        for key in self.redis.scan_iter(f"{REDIS_CACHE_PREFIX}*"):
            cached_data = self.redis.get(key)
            if not cached_data:
                continue
            try:
                data = json.loads(cached_data)
                resource_ids = data.get("resource_ids", [])
                if resource_id in resource_ids:
                    keys_to_delete.append(key)
            except Exception:
                continue

        if keys_to_delete:
            self.redis.delete(*keys_to_delete)
            logger.info(f"Deleted {len(keys_to_delete)} cache entries for resource_id: {resource_id}")
        else:
            logger.info(f"ℹNo cache entries found for resource_id: {resource_id}")

    # ---------------------------------------------- #
    # ---------- Question Embedding Store ---------- #
    # ---------------------------------------------- #
    def set_question_embedding_cache(self, question: str, embedding: np.ndarray):
        """
        Store the embedding vector of a question in the cache.

        Args:
            question (str): The question whose embedding is to be cached.
            embedding (np.ndarray): The embedding vector of the question to store in the cache.

        Returns:
            None
        """
        key = EMBED_CACHE_PREFIX + hashlib.sha256(question.encode()).hexdigest()
        self.redis.set(key, json.dumps(embedding))
        # self.redis.set(key, json.dumps(embedding.tolist()))

    def get_question_embedding_cache(self, question: str) -> Optional[np.ndarray]:
        """
        Retrieve the cached embedding for a given question.

        Args:
            question (str): The question for which the embedding is cached.

        Returns:
            np.ndarray or None: The cached embedding vector if available, otherwise None.
        """
        key = EMBED_CACHE_PREFIX + hashlib.sha256(question.encode()).hexdigest()
        value = self.redis.get(key)
        if value:
            try:
                return np.array(json.loads(value))
            except:
                return None
        return None
