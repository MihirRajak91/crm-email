from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Optional

class UploadResourceEvent(BaseModel):
    """
    Description: Pydantic model for upload resource events from external systems
    
    args:
        event (str): Event type identifier, example "upload_resource"
        resource_id (UUID): Unique resource identifier
        resource_type (str): Type of the resource, example "FILE"
        user_id (str): User identifier, example "1"
        user_ids (list[str]): List of user IDs with access, example ["1", "2", "3"]
        organization_id (UUID): Organization unique identifier
        file_name (str): Name of the uploaded file
        file_path (str): Path to the uploaded file
        flag (str): Source indicator, example "local"
        
    returns:
        UploadResourceEvent: Validated upload resource event instance
    """
    event: str = Field(..., example="upload_resource")
    resource_id: UUID
    resource_type: str = Field(..., example="FILE")
    user_id: str = Field(..., example="1")
    user_ids: list[str] = Field(..., example=["1", "2", "3"])
    organization_id: UUID
    file_name: str
    file_path: str
    flag: str = Field(..., example="local")

class BatchUploadRequest(BaseModel):
    """
    Description: Pydantic model for batch upload processing requests containing multiple upload events
    
    args:
        events (List[UploadResourceEvent]): List of upload resource events to process
        max_workers (Optional[int]): Override max workers for this specific batch, defaults to None
    
    returns:
        BatchUploadRequest: Validated batch upload request instance
    """
    events: List[UploadResourceEvent]
    max_workers: Optional[int] = Field(default=None, description="Override max workers for this batch")
    
class StressTestRequest(BaseModel):
    """
    Description: Pydantic model for stress test configuration parameters
    
    args:
        num_messages (int): Number of messages to generate (1-1000), defaults to 10
        max_workers (Optional[int]): Max workers for processing (1-32), defaults to None
        file_type (str): File type to simulate (pdf|docx|zeta|mp4), defaults to "pdf"
        organization_prefix (str): Prefix for organization names, defaults to "test_org"
        user_prefix (str): Prefix for user names, defaults to "user"
    
    returns:
        StressTestRequest: Validated stress test request instance
    """
    num_messages: int = Field(default=10, ge=1, le=1000, description="Number of messages to generate (1-1000)")
    max_workers: Optional[int] = Field(default=None, ge=1, le=32, description="Max workers for processing (1-32)")
    file_type: str = Field(default="pdf", pattern="^(pdf|docx|zeta|mp4)$", description="File type to simulate")
    organization_prefix: str = Field(default="test_org", description="Prefix for organization names")
    user_prefix: str = Field(default="user", description="Prefix for user names")
