"""
Description: Main router aggregation module that combines all API route modules with appropriate prefixes and tags

args:
    None (module-level router configuration)

returns:
    APIRouter: Combined main_router with all application endpoints organized by functionality
"""

from fastapi import APIRouter
from crm.routers.query_store_router import router as database_store
from crm.routers.auth import router as auth_routes
from crm.routers.document_list_router import router as document_list
from crm.routers.logger_router import router as logger_router
from crm.routers.email_router import router as email_router
from crm.routers.upload_router import router as upload_router

main_router = APIRouter()

main_router.include_router(auth_routes, prefix="/api", tags=["auth"])
# Chat routes removed per request (no response generation endpoints)
main_router.include_router(database_store,prefix="/api", tags=["mongodb"])
main_router.include_router(document_list, prefix="/api", tags=["qdrant"])
main_router.include_router(logger_router, prefix="/api", tags=["logger"])
main_router.include_router(email_router, prefix="/api", tags=["email"])
main_router.include_router(upload_router, prefix="/api", tags=["upload"])
