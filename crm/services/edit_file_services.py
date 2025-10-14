import logging
from pathlib import Path
from typing import Dict
from crm.services.add_file_services import AddFileServices
from crm.services.delete_file_services import DeleteFileServices
from crm.cache.chat_cache import ChatCache
from crm.utils.logger import logger

class EditFileServices:
    """
    Description: Service for editing files by deleting old embeddings and adding new ones with cache invalidation
    
    args:
        output_dir (str): Directory where files will be saved, defaults to project rag_documents folder
    
    returns:
        EditFileServices: Instance for handling file edit operations
    """

    def __init__(self, output_dir: str | None = None):
        """
        Description: Initialize EditFileServices with both delete and add service capabilities
        
        args:
            output_dir (str): Directory where files will be saved for processing
        
        returns:
            None
        """
        # Default to the repository rag_documents directory if an explicit path isn't provided
        self.output_dir = output_dir or str(Path(__file__).resolve().parents[2] / "rag_documents")
        self.delete_service = DeleteFileServices()
        self.chat_cache = ChatCache()
        self.add_service = AddFileServices(output_dir=self.output_dir)

    def process_edit_file(self, file_info: Dict,file_type: str) -> None:
        """
        Description: Process file edit by first deleting old embeddings then adding new ones
        
        args:
            file_info (Dict): File information containing metadata including resource_id and file_name
            file_type (str): Type of file being processed (pdf, docx, etc.)
        
        returns:
            None: Raises exception on failure, logs success on completion
        """
        try:
            resource_id = file_info.resource_id
            file_type = file_type

            if not resource_id or not file_type:
                logger.error("Missing required fields in file_info")
                return

            logger.info(f"Starting edit process for resource_id: {resource_id}")
                
            # Invalidate the cache for this resource_id
            logger.info("Invalidating chat cache for this resource_id...")
            self.chat_cache.invalidate_cache_by_resource_id(resource_id)

            # Step 1: Delete existing embeddings
            logger.info("Deleting existing embeddings")
            self.delete_service.delete_embeddings(file_info)

            # Step 2: Add new embeddings
            logger.info("Adding new embeddings")
            self.add_service.process_file(file_info, file_type)

            logger.info(f"Successfully edited file: {file_info.file_name}")

        except Exception as e:
            logger.error(f"Error editing file: {e}")
            raise
