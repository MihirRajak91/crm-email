from fastapi import APIRouter, Query
from qdrant_client.models import Filter, FieldCondition, MatchValue
from crm.utils.qdrand_db import client
# from crm.configs.collection_name_configs import COLLECTION_NAME
from crm.core.settings import get_settings

router = APIRouter()
settings = get_settings()
collection_name = settings.COLLECTION_NAME

@router.get("/documents")
async def list_documents(
    organization_id: str = Query(..., description="Filter by organization ID"),
    limit: int = Query(100, ge=1, le=1000, description="Max docs to list")
):
    """
    Description: Retrieve a list of documents from Qdrant filtered by organization ID with metadata
    
    args:
        organization_id (str): Unique organization identifier for filtering documents
        limit (int): Maximum number of documents to return (1-1000), defaults to 100
    
    returns:
        dict: Object containing list of documents with metadata including filename, text preview, access, and timestamps
    """
    scroll_filter = Filter(
        must=[FieldCondition(key="organization_id", match=MatchValue(value=organization_id))]
    )

    result, _ = client.scroll(
        collection_name=collection_name,
        scroll_filter=scroll_filter,
        limit=limit,
    )

    documents = [{
        "id": point.id,
        "filename": point.payload.get("filename"),
        "text": point.payload.get("text", "")[:200],
        "access": point.payload.get("access", []),
        "organization_id": point.payload.get("organization_id", ""),
        "resource_id": point.payload.get("resource_id", ""),
        "file_type": point.payload.get("file_type", ""),
        "start_time": point.payload.get("start_time"),
        "end_time": point.payload.get("end_time"),
        "source_type": point.payload.get("source_type", ""),
    } for point in result]

    return {"documents": documents}
