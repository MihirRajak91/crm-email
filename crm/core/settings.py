# crm/core/settings.py
from typing import Literal
from functools import lru_cache
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, computed_field

# ---- type aliases ----
EnvName = Literal["dev", "staging", "prod"]
LLMProvider = Literal["openai", "azure", "ollama"]
EmbeddingProvider = Literal["openai", "local"]
TranscriptionProvider = Literal["openai", "whisper"]

# Resolve a default .env path relative to the project root so running from subfolders still works
_DEFAULT_ENV_FILE = (
    os.environ.get("CRMAI_ENV_FILE")
    or os.environ.get("KMSAI_ENV_FILE")
    or str(Path(__file__).resolve().parents[2] / ".env")
)


class Settings(BaseSettings):
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=_DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow", 
    )

    # -- Application settings
    APP_NAME: str = Field(default="CRM", description="CRM Services")
    APP_VERSION: str = Field(default="1.0.0", description="Version of the CRM application")
    APP_DESCRIPTION: str = Field(default="Customer Relationship Management AI", description="Description of the CRM application")

    # -- Environment and service configurations
    ENV: EnvName = Field(default="dev", description="Environment in which the application is running")
    DEBUG: bool = Field(default=True, description="Enable or disable debug mode")
    JWT_SECRET_KEY: str = Field(default="jwt_secret_key_here", description="Secret key for JWT authentication")
    ALGORITHM: str = Field(default="HS256", description="Algorithm used for JWT encoding")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=300, description="Access token expiration time in minutes")

    @field_validator("ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        if v not in ("dev", "staging", "prod"):
            raise ValueError("Invalid environment. Must be one of: dev, staging, prod.")
        return v

    # -- MongoDB configurations
    MONGODB_HOST: str = Field(default="localhost", description="MongoDB host")
    MONGODB_PORT: int = Field(default=27017, alias="MONGODB_PORT_NUMBER", description="MongoDB Port")
    MONGODB_DB_NAME: str = Field(default="chat_db", description="MongoDB database name")
    MONGODB_USERNAME: str = Field(default="", description="MongoDB username")
    MONGODB_PASSWORD: str = Field(default="", description="MongoDB password")

    @property
    def mongodb_uri(self) -> str:
        if self.MONGODB_USERNAME and self.MONGODB_PASSWORD:
            return f"mongodb://{self.MONGODB_USERNAME}:{self.MONGODB_PASSWORD}@{self.MONGODB_HOST}:{self.MONGODB_PORT}/{self.MONGODB_DB_NAME}"
        return f"mongodb://{self.MONGODB_HOST}:{self.MONGODB_PORT}/{self.MONGODB_DB_NAME}"

    # -- Qdrant and Redis configurations
    QDRANT_HOST: str = Field(default="localhost", description="Qdrant host")
    QDRANT_PORT: int = Field(default=6333, alias="QDRANT_PORT_NUMBER", description="Qdrant port")
    QDRANT_SKIP_COLLECTION_INIT: bool = Field(default=False, description="Skip auto-creation/ensure of Qdrant collection")

    @property
    def qdrant_uri(self) -> str:
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    # -- Redis configurations
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, alias="REDIS_PORT_NUMBER", description="Redis port")
    REDIS_PASSWORD: str = Field(default="", description="Redis password")

    @property
    def redis_uri(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    # -- RabbitMQ configurations
    RABBITMQ_HOST: str = Field(default="localhost", description="RabbitMQ host")
    RABBITMQ_PORT: int = Field(default=5672, description="RabbitMQ port")
    RABBITMQ_USER: str = Field(default="guest", description="RabbitMQ user")
    RABBITMQ_PASSWORD: str = Field(default="guest", description="RabbitMQ password")
    ENABLE_RABBITMQ_CONSUMERS: bool = Field(default=True, description="Start RabbitMQ consumers on startup")
    METRICS_PORT: int = Field(default=9102, description="Prometheus metrics port (0 disables)")

    # -- Service configurations
    LLM_PROVIDER: LLMProvider = Field(default="openai", description="LLM provider for the application")
    EMBEDDING_PROVIDER: EmbeddingProvider = Field(default="openai", description="Embedding provider for the application")
    VIDEO_TRANSCRIPTION_PROVIDER: TranscriptionProvider = Field(default="openai", description="Video transcription provider for the application")

    # -- OpenAI configurations
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_LLM_MODEL: str = Field(default="gpt-3.5-turbo", description="OpenAI LLM model name")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="OpenAI embedding model name")
    OPENAI_EMBEDDING_DIM: int = Field(default=1536, description="OpenAI embedding dimensionality")
    OPENAI_COLLECTION_NAME: str = Field(default="CRM_zeta_documents_openai", description="OpenAI collection name for embeddings")
    OPENAI_EXTRACT_CONTENT_MODEL: str = Field(default="gpt-4o", description="OpenAI LLM model name")
    OPENAI_EXTRACT_CONTENT_DIM: int = Field(default=1536, description="OpenAI embedding dimensionality")

    # -- Ollama configurations
    OLLAMA_API_URL: str = Field(default="http://localhost:11434", description="Ollama API URL")
    LOCAL_LLM_MODEL: str = Field(default="llama3.1", description="LLM Model")
    LOCAL_EMBEDDING_MODEL: str = Field(default="embed", description="Ollama embedding model name")
    LOCAL_EMBEDDING_DIM: int = Field(default=768, description="Local embedding dimensionality")
    LOCAL_COLLECTION_NAME: str = Field(default="CRM_zeta_documents", description="Local collection name for embeddings")

    # -- External service configurations
    WHISPER_HOST: str = Field(default="localhost", description="Whisper service host")
    WHISPER_PORT: int = Field(default=9000, alias="WHISPER_PORT_NUMBER", description='Whisper service port')


    @computed_field
    @property
    def EMBEDDING_MODEL(self) -> str:
        """
        Returns the embedding model based on the environment.
        """
        return self.LOCAL_EMBEDDING_MODEL if self.ENV == "dev" else self.OPENAI_EMBEDDING_MODEL
    
    @computed_field
    @property
    def EMBEDDING_DIM(self) -> int:
        """
        Returns the embedding dimensionality based on the environment.
        """
        return self.LOCAL_EMBEDDING_DIM if self.ENV == "dev" else self.OPENAI_EMBEDDING_DIM

    @computed_field
    @property
    def USE_OPENAI(self) -> bool:
        """
        Returns whether to use OpenAI for embeddings based on the environment.
        """
        return self.ENV != "dev"

    @computed_field
    @property
    def COLLECTION_NAME(self) -> str:
        """
        Returns the collection name based on the environment.
        """
        return self.LOCAL_COLLECTION_NAME if self.ENV == "dev" else self.OPENAI_COLLECTION_NAME


@lru_cache()
def get_settings() -> Settings:
    """
    Get the settings instance with caching.
    
    Returns:
        Settings: An instance of the Settings class with loaded environment variables.
    """
    return Settings()


# settings = get_settings()
