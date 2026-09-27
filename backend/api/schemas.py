"""Pydantic request and response schemas for all API endpoints."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# --- Chat & Workflow Schemas ---
class ChatRequest(BaseModel):
    dataset_id: str = Field(..., description="ID of the uploaded dataset to analyze")
    question: str = Field("", description="Natural language question or analysis request")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation continuity")

class ChatResponse(BaseModel):
    job_id: str
    session_id: str
    dataset_id: str
    status: str
    question: Optional[str] = None
    is_relevant: bool = True
    requires_approval: bool = False
    proposed_method: Optional[Dict[str, Any]] = None
    analysis_plan: Optional[Dict[str, Any]] = None
    markdown: Optional[str] = None
    chart: Optional[Dict[str, Any]] = None
    sdk_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# --- Analysis & Approval Schemas ---
class ApproveRequest(BaseModel):
    job_id: str = Field(..., description="ID of the job currently awaiting approval")

class RejectRequest(BaseModel):
    job_id: str = Field(..., description="ID of the job to reject or modify")
    modification_instructions: Optional[str] = Field(None, description="Instructions to adjust the proposed method")

class FeedbackRequest(BaseModel):
    job_id: str = Field(..., description="ID of the completed job to correct")
    feedback: str = Field(..., description="Feedback/correction instructions (e.g. 'Use population std')")

class DirectExecuteRequest(BaseModel):
    dataset_id: str = Field(..., description="Target dataset ID")
    method: str = Field(..., description="SDK method name (e.g. 'summary_statistics', 'pearson_correlation')")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method arguments such as column names")

# --- Skill Schemas ---
class SkillCreateRequest(BaseModel):
    name: str = Field(..., description="Human-readable name of the skill")
    description: str = Field(..., description="Detailed description of what the skill calculates")
    required_inputs: List[str] = Field(default_factory=list, description="Required column names or parameters")
    formula: Optional[str] = Field(None, description="Mathematical formula")
    logic: str = Field(..., description="Calculation logic description")
    code: Optional[str] = Field(None, description="Analysis SDK code string")
    validation_rules: List[str] = Field(default_factory=list, description="Validation constraints")

class SkillUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    required_inputs: Optional[List[str]] = None
    formula: Optional[str] = None
    logic: Optional[str] = None
    code: Optional[str] = None
    validation_rules: Optional[List[str]] = None
    feedback: Optional[str] = Field(None, description="Reason for version update")

class SkillSearchRequest(BaseModel):
    query: str = Field(..., description="Search query describing desired analysis")
    threshold: float = Field(0.5, description="Cosine similarity threshold")
    top_k: int = Field(5, description="Maximum number of skills to return")

# --- Session Schemas ---
class SessionCreateRequest(BaseModel):
    user_id: str = Field("default_user", description="Owner user ID")
    active_dataset_id: Optional[str] = Field(None, description="Initial active dataset ID")

# --- System & Health Schemas ---
class HealthResponse(BaseModel):
    status: str = "ok"
    database: str
    skills_count: int
    datasets_count: int
    timestamp: str

class StatsResponse(BaseModel):
    total_datasets: int
    total_jobs: int
    total_skills: int
    total_sessions: int
    status: str = "healthy"
