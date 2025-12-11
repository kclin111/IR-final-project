"""
FastAPI main application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.api import routes
from app.utils.vector_store import VectorStoreBuilder
from app.utils.mapping import LawCaseMapping
from app.utils.retrieval import RetrievalEngine
from app.utils.context_builder import ContextBuilder
from app.utils.llm_generator import LLMGenerator


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    """
    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        description=settings.API_DESCRIPTION,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    static_path = Path("app/static")
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # Include routers (no prefix since we handle / in routes)
    app.include_router(routes.router)

    return app


def initialize_system():
    """
    Initialize system components on startup
    """
    print("\n=== Initializing Traffic Law Retrieval System ===")

    # Load vector stores
    print("Loading vector stores...")
    vector_builder = VectorStoreBuilder(persist_directory="data/chroma_db")

    law_collection = vector_builder.load_law_collection()
    case_collection = vector_builder.load_case_collection()
    print("✓ Vector stores loaded")

    # Load mapping
    print("Loading law-case mapping...")
    mapping = LawCaseMapping(mapping_path="data/law_case_mapping.json")
    print("✓ Mapping loaded")

    # Create retrieval engine
    print("Creating retrieval engine...")
    retrieval_engine = RetrievalEngine(
        law_collection=law_collection,
        case_collection=case_collection,
        mapping=mapping,
        law_top_k=5,
        case_top_k=5,
        expand_cases_per_law=3
    )
    print("✓ Retrieval engine created")

    # Create context builder
    print("Creating context builder...")
    context_builder = ContextBuilder(max_context_tokens=10000)
    print("✓ Context builder created")

    # Create LLM generator
    print("Creating LLM generator...")
    llm_generator = LLMGenerator()
    print("✓ LLM generator created")

    # Set dependencies in routes
    routes.set_dependencies(
        engine=retrieval_engine,
        builder=context_builder,
        generator=llm_generator,
        map_instance=mapping
    )

    print("=== System initialized successfully ===\n")


# Create app
app = create_app()


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    initialize_system()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
    )
