"""
FastAPI dependencies for dependency injection
"""
from functools import lru_cache
from app.config import Settings, settings
from app.models.database import DatabaseManager, ChromaDBManager
from app.utils.vector_search import VectorSearcher
from app.utils.captioner import ImageCaptioner
from app.utils.alignment import AlignmentManager
from app.utils.reranker import ReRanker
from app.utils.context_builder import ContextBuilder
from app.utils.llm_generator import LLMGenerator


@lru_cache()
def get_settings() -> Settings:
    """Get application settings"""
    return settings


def get_db_manager() -> DatabaseManager:
    """Get database manager instance"""
    pass


def get_chroma_manager() -> ChromaDBManager:
    """Get ChromaDB manager instance"""
    pass


def get_vector_searcher() -> VectorSearcher:
    """Get vector searcher instance"""
    pass


def get_image_captioner() -> ImageCaptioner:
    """Get image captioner instance"""
    pass


def get_alignment_manager() -> AlignmentManager:
    """Get alignment manager instance"""
    pass


def get_reranker() -> ReRanker:
    """Get re-ranker instance"""
    pass


def get_context_builder() -> ContextBuilder:
    """Get context builder instance"""
    pass


def get_llm_generator() -> LLMGenerator:
    """Get LLM generator instance"""
    pass
