from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class EmailUpdateRequest(BaseModel):
    """
    Description: Request model for updating status alongside email contents.

    args:
        status (str): Status string indicating the update context
        past_email (str): Full text content of the previous email
        latest_email (str): Full text content of the latest email

    returns:
        EmailUpdateRequest: Validated request payload
    """
    status: str
    past_email: str
    latest_email: str


class StatusEnum(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    LOST = "lost"


class EmailThreadMessage(BaseModel):
    """Lightweight representation of a prior email in the thread."""

    subject: Optional[str] = None
    body: str


class ComposeEmailRequest(BaseModel):
    """Minimal payload for composing a status-aware email."""

    status: StatusEnum
    past_emails: List[EmailThreadMessage] = Field(default_factory=list)
    recipient_name: Optional[str] = None
    recipient_company: Optional[str] = None
    top_k: int = Field(default=6, ge=1, le=20)


class SourceRef(BaseModel):
    resource_id: Optional[str] = None
    chunk_id: Optional[str] = None
    title: Optional[str] = None


class ComposeEmailResponse(BaseModel):
    """
    Minimal response for email composition. Only includes the generated email.
    """
    subject: str
    body: str
