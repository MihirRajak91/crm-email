"""
Description: Main FastAPI application entry point for the CRM chatbot server with router configuration and lifespan management

args:
    None (module-level application setup)

returns:
    FastAPI: Configured application instance ready for deployment
"""

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from crm.routers.app_routes import main_router
from crm.core.lifespan import lifespan

app = FastAPI(
    title="Chatbot Server",
    version='1.0',
    description=' API Server for the AI Service',
    lifespan=lifespan,
)

app.include_router(main_router, prefix='')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app="main:app",host="0.0.0.0",port=8001, reload=True, workers=2)
