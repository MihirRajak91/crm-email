from fastapi import APIRouter
from crm.models.email_models import (
    EmailUpdateRequest,
    ComposeEmailRequest,
)
from crm.utils.logger import logger
from crm.utils.response_formatter import (
    format_success_response,
    format_error_response,
)
from crm.services.email_composer_service import EmailComposerService


router = APIRouter()
composer_service = EmailComposerService()


@router.post("/email/update")
async def update_email_status(payload: EmailUpdateRequest):
    """
    Description: Accepts status, past_email (content), and latest_email (content).

    args:
        payload (EmailUpdateRequest): Incoming request with status, past_email content, latest_email content

    returns:
        JSONResponse: Standardized success response echoing the request or error on failure
    """
    try:
        # Avoid logging full email contents; log lengths and short previews
        past_len = len(payload.past_email)
        latest_len = len(payload.latest_email)
        past_preview = (payload.past_email[:120].replace("\n", " ") + ("..." if past_len > 120 else "")) if past_len else ""
        latest_preview = (payload.latest_email[:120].replace("\n", " ") + ("..." if latest_len > 120 else "")) if latest_len else ""

        logger.info(
            f"Email update received | status={payload.status} | past_len={past_len}, latest_len={latest_len} | previews: past='{past_preview}', latest='{latest_preview}'"
        )

        # Placeholder for actual business logic
        result = {
            "status": payload.status,
            # Keep keys as provided; values are full email contents
            "past_email": payload.past_email,
            "latest_email": payload.latest_email,
            "message": "Email content payload received",
        }

        return format_success_response(result, message="Email update accepted")
    except Exception as e:
        logger.error(f"Error in email update endpoint: {e}")
        return format_error_response(str(e), status_code=500)


@router.post("/email/compose")
async def compose_email(payload: ComposeEmailRequest):
    """
    Compose a status-aware email using separated system/user/context messages.

    - System prompt: writing rules for the email type
    - Retrieved context: company/product digest from Qdrant, passed as a separate message
    - User payload: status, conversation history (`past_emails`), and light personalization
    """
    try:
        # Avoid logging full email bodies
        thread_count = len(payload.past_emails)
        first_preview = (
            payload.past_emails[0].body[:120].replace("\n", " ") + "..."
            if thread_count and len(payload.past_emails[0].body) > 120
            else (payload.past_emails[0].body.replace("\n", " ") if thread_count else "")
        )
        logger.info(
            "Compose request | status=%s | thread_messages=%s | top_k=%s | first_message='%s'",
            payload.status,
            thread_count,
            payload.top_k,
            first_preview,
        )

        resp = await composer_service.compose(payload)
        return format_success_response(
            data=resp.model_dump(),
            message="Email composed successfully",
        )
    except Exception as e:
        logger.error(f"Error composing email: {e}")
        return format_error_response(str(e), status_code=500)
