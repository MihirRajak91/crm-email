from typing import Optional, List
from qdrant_client import QdrantClient
from qdrant_client.http import models
from crm.utils.qdrand_db import client
# from crm.configs.collection_name_configs import COLLECTION_NAME
from crm.core.settings import get_settings
from crm.models.rabbitmq_event_models import ResourceEvent
from crm.utils.logger import logger
from crm.cache.chat_cache import ChatCache

settings = get_settings()
COLLECTION_NAME = settings.COLLECTION_NAME

class DeleteFileServices:
    """
    Description: Service for deleting files and their embeddings from Qdrant vector database and cache invalidation
    
    args:
        collection_name (str): Qdrant collection name, defaults to global collection_name
    
    returns:
        DeleteFileServices: Instance for handling file deletion operations
    """
    
    def __init__(self, collection_name: str = COLLECTION_NAME):
        """
        Description: Initialize the delete file services with Qdrant client and cache
        
        args:
            COLLECTION_NAME (str): Qdrant collection name for embeddings storage
        
        returns:
            None
        """
        self.collection_name = collection_name
        self.client = client
        self.chat_cache = ChatCache()

    def delete_embeddings(self, file_info: ResourceEvent) -> None:
        """
        Description: Delete all embeddings associated with a resource_id from Qdrant and invalidate cache
        
        args:
            file_info (ResourceEvent): File information containing resource_id and organization_id
        
        returns:
            None: Raises exception on failure
        """
        try:
            resource_id = file_info.resource_id
            organization_id = file_info.organization_id      
            # print(f"Resource ID: {resource_id}")
            if not resource_id:
                logger.error("No resource_id provided in file_info")
                return

            logger.info(f"Deleting embeddings for resource_id: {resource_id}")
            logger.debug(f"File info: {file_info}")

            # Invalidate the cache for this resource_id
            logger.info("Invalidating chat cache for this resource_id...")
            self.chat_cache.invalidate_cache_by_resource_id(resource_id)

            # Create filter conditions
            filter_conditions = [
                models.FieldCondition(
                    key="resource_id",
                    match=models.MatchValue(value=str(resource_id))
                )
            ]

            # Add organization filter if provided
            if organization_id:
                filter_conditions.append(
                    models.FieldCondition(
                        key="organization_id",
                        match=models.MatchValue(value=str(organization_id))
                    )
                )

            # Delete points matching the filter
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.Filter(
                    must=filter_conditions
                ),
                wait=True  # Ensure deletion completes before returning
            )
            logger.warning(f"Deletion result: {result}")
            logger.info(f"Successfully deleted embeddings for resource_id: {resource_id}")
            logger.debug(f"Deletion result: {result}")
            
        except Exception as e:
            logger.error(f"Failed to delete embeddings for resource_id {resource_id}: {e}")
            raise