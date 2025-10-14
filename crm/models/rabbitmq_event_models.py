from pydantic import BaseModel, Field, AliasChoices
from typing import List, Optional
from uuid import UUID

 
class ResourceEvent(BaseModel):
    """
    Description: Pydantic model for RabbitMQ resource events containing file upload and processing information
    
    args:
        event (str): Event type identifier
        resource_id (str): Unique resource identifier (aliased from 'id')
        user_id (str): User who triggered the event
        organization_id (str): Organization identifier
        file_name (str): Name of the file (aliased from 'resource_name')
        file_path (str): Path to the file (aliased from 'resource_path')
        resource_type (Optional[str]): Type of resource, defaults to "FILE"
        file_type (Optional[str]): Specific file type (pdf, docx, etc.)
        flag (Optional[str]): Additional processing flags
        organization_access (Optional[str]): Organization access level
        role_id (Optional[str]): Role ID with access
        user_ids (Optional[List[str]]): List of user IDs with access
        summary (Optional[str]): Resource summary or description
        organization_schema (Optional[str]): Schema for the organization
    
    returns:
        ResourceEvent: Validated resource event instance
    """
    event: str = None
    resource_id: str = Field(alias="id")
    user_id: str
    organization_id: str
    file_name: str = Field(alias="resource_name")
    file_path: str = Field(alias="resource_path")
    summary: Optional[str] = None  
    resource_type: Optional[str] = "FILE"
    file_type: Optional[str] = None 
    flag: Optional[str] = None
    organization_access: Optional[str] = None
    role_id: Optional[str] = None
    user_ids: Optional[List[str]] = None
    organization_schema: Optional[str] = None
class UpdatePermissionsEvent(BaseModel):
    """
    Description: Pydantic model for RabbitMQ permission update events with new field structure

    args:
        event (str): Event type identifier
        resource_id (str): Unique resource identifier (aliased from 'id')
        assigned_user_ids (List[str]): List of user IDs being assigned access
        unassigned_user_ids (List[str]): List of user IDs being removed from access
        organization_access (Optional[bool]): Organization-wide access flag (aliased from 'organization_wide')
        assigned_role_ids (List[str]): List of role IDs being assigned access
        unassigned_role_ids (List[str]): List of role IDs being removed from access
        title (str): Title of the notification
        message (str): Message content
        type (str): Type of notification (e.g., "Push")
        organization_id (str): Organization identifier

    returns:
        UpdatePermissionsEvent: Validated permission update event instance
    """
    event: str
    resource_id: str = Field(alias="id")
    assigned_user_ids: List[str] = []
    unassigned_user_ids: List[str] = []
    organization_access: Optional[bool] = Field(alias="organization_wide")
    assigned_role_ids: List[str] = []
    unassigned_role_ids: List[str] = []


class EmbeddingEvent(BaseModel):
    """
    Description: Simplified pydantic model for RabbitMQ embedding events

    args:
        event (str): Event type identifier (e.g., 'create_embedding', 'batch_embedding')
        task_id (str): Unique task identifier
        resource_id (str): Resource identifier for the embedding request
        texts (Optional[List[str]]): Texts to embed (for batch processing)
        callback_url (Optional[str]): URL to callback with results
        user_id (Optional[str]): User who triggered the event

    returns:
        EmbeddingEvent: Validated embedding event instance
    """
    event: str
    task_id: str
    resource_id: str
    texts: Optional[List[str]] = None
    callback_url: Optional[str] = None
    user_id: Optional[str] = None


class EmbeddingResponse(BaseModel):
    """Flexible embedding response supporting success and failure payloads."""

    event: str = "embedding_response"
    task_id: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = "success"
    resource_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("id", "resource_id"))
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    embeddings: Optional[List[List[float]]] = None
    chunks: Optional[List[str]] = None
    file_name: Optional[str] = Field(default=None, validation_alias=AliasChoices("resource_name", "file_name"))
    file_path: Optional[str] = Field(default=None, validation_alias=AliasChoices("resource_path", "file_path"))
    model_name: Optional[str] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = Field(default=None, validation_alias=AliasChoices("error_message", "error"))
