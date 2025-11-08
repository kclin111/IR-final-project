"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # OpenAI API Key
    OPENAI_API_KEY: str

    # API Settings
    API_TITLE: str = "智慧交通法規與判例檢索輔助系統"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Traffic Law and Case Retrieval System"

    # Database Settings
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    SQLITE_DB_PATH: str = "data/kp_app_mapping.db"

    # ChromaDB Collections
    KNOWLEDGE_POINTS_COLLECTION: str = "knowledge_points"
    APPLICATIONS_COLLECTION: str = "applications"
    IMAGE_FEATURES_COLLECTION: str = "image_features"

    # Retrieval Settings
    TOP_K_KP: int = 10
    TOP_K_CASES: int = 20
    RERANK_TOP_N: int = 5

    # LLM Settings
    LLM_MODEL: str = "gpt-5-nano"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2000
    LLM_TIMEOUT: int = 30

    # Embedding Settings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # VLM Settings (Optional)
    ENABLE_VLM: bool = False
    VLM_MODEL: Optional[str] = None

    # Performance Settings
    MAX_QUERY_TIMEOUT: int = 30
    ENABLE_CACHE: bool = True
    CACHE_TTL: int = 3600

    # Alignment Settings
    MIN_ALIGNMENT_CONFIDENCE: float = 0.5

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
