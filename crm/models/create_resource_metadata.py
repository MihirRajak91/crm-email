from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class CreateResourceMetadata(BaseModel):
    """
    Description: Pydantic model for resource metadata used in create/upload/delete/update operations
    
    args:
        event (Literal): Event type - one of "upload_resource", "create_resource", "delete_resource", "update_permissions"
        resource_id (str): Unique identifier for the resource
        resource_type (Literal): Resource type - one of "pdf", "docx", "zeta", "mp4"
        user_id (str): User identifier who owns or triggers the operation
        organization_id (str): Organization identifier
        file_name (str): Name of the file
        file_path (str): File system path to the resource
        summary (Optional[str]): Optional summary or description, defaults to empty string
        user_ids (List[str]): List of user IDs with access to this resource
        flag (Optional[str]): Optional processing or status flag, defaults to empty string
    
    returns:
        CreateResourceMetadata: Validated resource metadata instance
    """
    event: Literal["upload_resource", "create_resource", "delete_resource", "update_permissions"]
    resource_id: str
    resource_type: Literal["pdf", "docx", "zeta", "mp4"]
    user_id: str
    organization_id: str
    file_name: str
    file_path: str
    summary: Optional[str] = ""
    user_ids: List[str] = Field(default_factory=list, description="List of user IDs with access")
    flag: Optional[str] = ""
