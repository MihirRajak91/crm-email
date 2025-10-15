from pydantic import BaseModel, Field, AliasChoices, field_validator
from typing import List, Optional, Dict, Any


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
    service_name: str
    extraction_type: str
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


class EmbeddingResultEvent(BaseModel):
    """
    Description: Pydantic model for RabbitMQ embedding result events

    args:
        task_id (str): Original task identifier
        status (str): Result status ('completed', 'failed', 'processing')
        result (Optional[Dict[str, Any]]): Embedding result data
        error (Optional[str]): Error message if failed
        processing_time (Optional[float]): Time taken to process in seconds
        created_at (Optional[str]): Result creation timestamp
        metadata (Optional[Dict[str, Any]]): Additional metadata

    returns:
        EmbeddingResultEvent: Validated result event instance
    """
    task_id: str
    status: str  # 'completed', 'failed', 'processing'
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    service_name: str

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
    """
    Description: Pydantic model for RabbitMQ embedding response events

    args:
        event (str): Event type, should be 'embedding_response'
        resource_id (str): Resource identifier for the embedding request
        embeddings (List[List[float]]): List of embedding vectors
        chunks (Dict[str, Dict[str, Any]]): Mapping of chunk id to payload data
        status (str): Response status ('success', 'failed')

    returns:
        EmbeddingResponse: Validated embedding response instance
    """
    event: str = "embedding_response"
    resource_id: str = Field(alias="id")
    embeddings: List[List[float]] = Field(default_factory=list)
    chunks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    status: str = "success"  # 'success', 'failed'
    service_name: str
    task_id: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    model_name: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    file_name: Optional[str] = Field(default=None, validation_alias=AliasChoices("resource_name", "file_name"))
    file_path: Optional[str] = Field(default=None, validation_alias=AliasChoices("resource_path", "file_path"))
    error: Optional[str] = Field(default=None, validation_alias=AliasChoices("error", "error_message"))

    @field_validator("chunks", mode="before")
    @classmethod
    def normalize_chunks(cls, value):
        """
        Accept list-based payloads for backward compatibility by converting them into
        an indexed dictionary structure.
        """
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            normalized: Dict[str, Dict[str, Any]] = {}
            for index, chunk in enumerate(value):
                key = str(index)
                if isinstance(chunk, dict):
                    normalized[key] = chunk
                else:
                    normalized[key] = {"text": chunk}
            return normalized
        raise TypeError("chunks must be a dictionary or list-compatible payload")
