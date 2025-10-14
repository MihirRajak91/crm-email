from contextlib import asynccontextmanager
from fastapi import FastAPI
from crm.configs.redis_config import redis_service
from crm.services.ollama_services import load_llm
from crm.utils.logger import logger
from crm.core.settings import get_settings
from crm.configs.constant import RABBITMQ_CONSUMER_QUEUES

@asynccontextmanager
async def lifespan(crm: FastAPI):
    """
    Description: FastAPI lifespan context manager for managing application startup and shutdown services
    
    args:
        crm (FastAPI): FastAPI application instance for service lifecycle management
    
    returns:
        AsyncGenerator: Context manager that initializes services on startup and cleans up on shutdown
    """
    logger.info("Starting up the application...")

    # Start ollama
    load_llm()

    # Start Qdrant and ensure collection
    # qdrant_service.start()

    # Connect services (Redis optional)
    try:
        redis_service.connect()
    except Exception as e:
        logger.error(f"Redis connection failed during startup but continuing: {e}")

    # Start RabbitMQ consumers only if enabled to avoid importing optional stacks
    settings = get_settings()
    if settings.ENABLE_RABBITMQ_CONSUMERS:
        try:
            from crm.rabbitmq.consumers import rabbitmq_consumer
            rabbitmq_consumer.start(RABBITMQ_CONSUMER_QUEUES)
        except Exception as e:
            logger.error(f"Failed to start RabbitMQ consumers: {e}")

    yield

    logger.warning("Shutting down services...")
