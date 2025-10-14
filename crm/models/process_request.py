from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
import uuid


class ChatBot(BaseModel):
    """
    Description: Pydantic model for chat bot request containing query and user context information
    
    args:
        query (str): User's query or question
        organization_id (Optional[str]): Organization context for the request, defaults to None
        user_id (Optional[str]): Unique identifier for the user, defaults to None
        role_id (Optional[str]): User role identifier, defaults to None
        conversation_id (Optional[str]): Conversation session tracking identifier, defaults to None
        include_history (bool): Whether to include conversation context, defaults to True
    
    returns:
        ChatBot: Validated chat bot request instance
    """
    query: str
    organization_id: Optional[str] = None  # For organizational context
    user_id: Optional[str]= None # Unique identifier for the user
    role_id: Optional[str] = None  # user roles id, e.g., ['admin', 'user']
    conversation_id: Optional[str] = None  # For tracking conversation sessions
    include_history: bool = True  # Whether to include conversation context


class Query(BaseModel):
    """
    Description: Simple Pydantic model for basic query requests
    
    args:
        query (str): User's query string
    
    returns:
        Query: Validated query instance
    """
    query: str


class ConversationMessage(BaseModel):
    """
    Description: Pydantic model for individual messages within a conversation
    
    args:
        id (str): UUID for the message, auto-generated if not provided
        sender (str): Message sender - 'user' or 'ai'
        content (str): Message content text
        created_at (datetime): Message creation timestamp, auto-generated if not provided
        conversation_id (str): Conversation identifier this message belongs to
        user_id (Optional[str]): User identifier, optional for AI messages
    
    returns:
        ConversationMessage: Validated conversation message instance
    """
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")  # UUID for the message
    sender: str  # 'user' or 'ai'
    content: str  # Message content
    created_at: datetime = Field(default_factory=datetime.now)
    conversation_id: str
    user_id: Optional[str] = None  # Optional, may be missing for AI messages


class Conversation(BaseModel):
    """
    Description: Pydantic model for conversation document with embedded messages
    
    args:
        id (Optional[str]): MongoDB ObjectId, optional for creation, defaults to None
        title (str): Conversation title or subject
        user_id (str): User identifier who owns the conversation
        conversation_id (str): Unique conversation identifier
        messages (List[ConversationMessage]): List of messages in the conversation, defaults to empty list
        created_at (datetime): Conversation creation timestamp, auto-generated if not provided
        updated_at (datetime): Last update timestamp, auto-generated if not provided
    
    returns:
        Conversation: Validated conversation instance
    """
    model_config = ConfigDict(populate_by_name=True)
    
    id: Optional[str] = Field(default=None, alias="_id")  # MongoDB ObjectId, optional for creation
    title: str
    user_id: str
    conversation_id: str
    messages: List[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# Legacy model for backward compatibility
class LegacyConversationMessage(BaseModel):
    """
    Description: Legacy Pydantic model for storing individual conversation messages (backward compatibility)
    
    args:
        user_id (str): User identifier
        conversation_id (str): Conversation identifier
        message (str): Message content
        role (str): Message role - 'user' or 'assistant'
        timestamp (str): Message timestamp as string
    
    returns:
        LegacyConversationMessage: Validated legacy conversation message instance
    """
    user_id: str
    conversation_id: str
    message: str
    role: str  # 'user' or 'assistant'
    timestamp: str


class UploadResourceEvent(BaseModel):
    """
    Description: Pydantic model for upload_resource event payload from external systems
    
    args:
        event (str): Event name, should be "upload_resource"
        resource_id (str): UUID of the uploaded resource
        resource_type (str): Type of the resource (e.g., "FILE")
        user_id (str): ID of the user who uploaded the file
        organization_id (str): UUID of the user's organization
        file_name (str): Name of the uploaded file
        file_path (str): Local path to the file
        flag (str): Indicator of file source ("local" or other flags)
    
    returns:
        UploadResourceEvent: Validated upload resource event instance
    """
    event: str  # Event name, should be "upload_resource"
    resource_id: str  # UUID of the uploaded resource
    resource_type: str  # Type of the resource (e.g., "FILE")
    user_id: str  # ID of the user who uploaded the file
    organization_id: str  # UUID of the user's organization
    file_name: str  # Name of the uploaded file
    file_path: str  # Local path to the file
    flag: str  # Indicator of file source ("local" or other flags)