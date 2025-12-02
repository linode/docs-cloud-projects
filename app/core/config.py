"""
Configuration management for the LangChain RAG Chatbot application.
Handles environment variables and application settings.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
    # Database Configuration
    vector_db_url: str = Field(..., env="VECTOR_DB_URL")
    state_db_url: str = Field(..., env="STATE_DB_URL")
    
    # Linode Object Storage Configuration
    linode_object_storage_access_key: str = Field(..., env="LINODE_OBJECT_STORAGE_ACCESS_KEY")
    linode_object_storage_secret_key: str = Field(..., env="LINODE_OBJECT_STORAGE_SECRET_KEY")
    linode_object_storage_endpoint: str = Field(..., env="LINODE_OBJECT_STORAGE_ENDPOINT")
    linode_object_storage_bucket: str = Field(..., env="LINODE_OBJECT_STORAGE_BUCKET")
    
    # Application Configuration
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # RAG Configuration
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    retrieval_k: int = Field(default=10, env="RETRIEVAL_K")
    
    # OpenAI Model Configuration
    llm_model: str = Field(default="gpt-4o-mini", env="LLM_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the application settings instance."""
    return settings


def validate_environment() -> bool:
    """Validate that all required environment variables are set."""
    required_vars = [
        "OPENAI_API_KEY",
        "VECTOR_DB_URL", 
        "STATE_DB_URL",
        "LINODE_OBJECT_STORAGE_ACCESS_KEY",
        "LINODE_OBJECT_STORAGE_SECRET_KEY",
        "LINODE_OBJECT_STORAGE_ENDPOINT",
        "LINODE_OBJECT_STORAGE_BUCKET"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True
