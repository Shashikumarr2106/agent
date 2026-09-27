from typing import Any, Dict, List, Optional
from ..core.compat import BaseModel, Field
from datetime import datetime

class ExecutionLog(BaseModel):
    log_id: str
    job_id: str
    step: str
    status: str  # "started" | "completed" | "error" | "skipped"
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class AnalysisJob(BaseModel):
    job_id: str
    session_id: str
    dataset_id: str
    question: Optional[str] = None
    status: str = "pending"  # "pending" | "planning" | "awaiting_approval" | "executing" | "completed" | "failed"
    analysis_plan: Optional[Dict[str, Any]] = None
    skill_found: bool = False
    skill_id: Optional[str] = None
    skill_version: Optional[int] = None
    proposed_method: Optional[Dict[str, Any]] = None
    sql_query: Optional[str] = None
    user_approved: Optional[bool] = None
    user_feedback: Optional[str] = None
    sdk_output: Optional[Dict[str, Any]] = None
    chart_spec: Optional[Dict[str, Any]] = None
    markdown: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

class Session(BaseModel):
    session_id: str
    user_id: str = "default_user"
    active_dataset_id: Optional[str] = None
    job_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ApprovalRequest(BaseModel):
    job_id: str
    approved: bool
    modification_instructions: Optional[str] = None

class FeedbackRequest(BaseModel):
    job_id: str
    feedback: str  # e.g., "Use population standard deviation instead."
