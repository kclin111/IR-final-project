"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class AlignmentStatus(str, Enum):
    """Alignment status enum"""
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


class CitationType(str, Enum):
    """Citation type enum"""
    STATUTE = "statute"
    CASE = "case"


# Request Schemas
class QueryRequest(BaseModel):
    """Query request schema"""
    text: str = Field(..., description="Query text")
    image: Optional[str] = Field(None, description="Base64 encoded image")
    top_k: Optional[int] = Field(5, description="Number of results to return")


class AlignmentReviewRequest(BaseModel):
    """Alignment review request schema"""
    kp_id: str = Field(..., description="Knowledge point ID")
    case_id: str = Field(..., description="Case ID")
    status: AlignmentStatus = Field(..., description="Review status")
    reviewer_note: Optional[str] = Field(None, description="Reviewer notes")


# Response Schemas
class Citation(BaseModel):
    """Citation schema"""
    type: CitationType = Field(..., description="Citation type")
    id: str = Field(..., description="Citation ID")
    span: str = Field(..., description="Citation span text")
    confidence: Optional[float] = Field(None, description="Citation confidence")


class AlignmentUsed(BaseModel):
    """Alignment used in response"""
    kp_id: str = Field(..., description="Knowledge point ID")
    case_id: str = Field(..., description="Case ID")
    confidence: float = Field(..., description="Alignment confidence")
    rationale_span: str = Field(..., description="Rationale span")


class QueryResponse(BaseModel):
    """Query response schema"""
    conclusion: str = Field(..., description="Generated conclusion")
    checklist: Dict[str, Any] = Field(..., description="Requirement checklist")
    citations: List[Citation] = Field(..., description="List of citations")
    alignments_used: List[AlignmentUsed] = Field(..., description="Alignments used")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    processing_time: float = Field(..., description="Processing time in seconds")


class StatsResponse(BaseModel):
    """Stats response schema"""
    total_knowledge_points: int
    total_applications: int
    total_alignments: int
    hit_at_5_statutes: float
    hit_at_5_cases: float
    alignment_precision: float
    hallucination_rate: float
    avg_latency: float


class AlignmentReviewResponse(BaseModel):
    """Alignment review response schema"""
    success: bool
    message: str
    updated_alignment: Optional[Dict[str, Any]] = None


# Database Models (for reference)
class KnowledgePoint(BaseModel):
    """Knowledge point model"""
    id: str
    content: str
    statute_id: Optional[str] = None
    article_number: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Application(BaseModel):
    """Application (case) model"""
    id: str
    fact: str
    reason: str
    court_level: Optional[str] = None
    year: Optional[int] = None
    case_number: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class KPAppMapping(BaseModel):
    """KP-Application mapping model"""
    kp_id: str
    case_id: str
    confidence: float
    rationale_span: str
    status: AlignmentStatus
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
