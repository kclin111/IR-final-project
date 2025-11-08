"""
API routes for traffic law retrieval system
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
import time

from app.config import settings


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# Global instances (will be initialized in main.py)
retrieval_engine = None
context_builder = None
llm_generator = None
mapping = None


def set_dependencies(engine, builder, generator, map_instance):
    """Set global dependencies"""
    global retrieval_engine, context_builder, llm_generator, mapping
    retrieval_engine = engine
    context_builder = builder
    llm_generator = generator
    mapping = map_instance


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Render main Q&A page
    """
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "交通法規智慧檢索系統"}
    )


@router.post("/api/query")
async def query(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main query endpoint for traffic law retrieval

    Process:
    1. Retrieve laws and cases with expansion
    2. Build context
    3. Generate LLM response
    """
    try:
        query_text = request.get("query", "").strip()

        if not query_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query text cannot be empty"
            )

        start_time = time.time()

        # Step 1: Retrieval with expansion
        laws, cases = retrieval_engine.retrieve(query_text)

        # Step 2: Build context
        system_prompt = context_builder.build_system_prompt()
        context = context_builder.build_context(laws, cases, query_text)

        # Debug: Print full context
        print("\n" + "="*60)
        print("檢索上下文DEBUG")
        print("="*60)
        print(context)
        print("="*60 + "\n")

        # Step 3: Generate response
        answer = llm_generator.generate_response(
            system_prompt=system_prompt,
            context=context,
            query_text=query_text
        )

        # Debug: Print answer
        print(f"\n生成的回答: {answer}\n")

        # Extract citations from retrieval results (not from LLM answer)
        law_citations = [law_data['metadata']['cited_law'] for law_data in laws.values()]
        case_citations = [case_id for case_id in cases.keys()]

        elapsed_time = time.time() - start_time

        return {
            "success": True,
            "query": query_text,
            "answer": answer,
            "retrieved_laws": len(laws),
            "retrieved_cases": len(cases),
            "law_citations": law_citations,
            "case_citations": case_citations,
            "processing_time": round(elapsed_time, 2),
            "context_preview": context[:500] + "..." if len(context) > 500 else context
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/api/stats")
async def get_stats() -> Dict[str, Any]:
    """
    Get system statistics

    Returns:
        Statistics including mapping counts
    """
    try:
        stats = mapping.get_statistics()

        return {
            "success": True,
            "statistics": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving stats: {str(e)}"
        )


@router.get("/api/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "service": "交通法規智慧檢索系統",
        "version": settings.API_VERSION
    }
