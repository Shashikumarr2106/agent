"""Analysis State definition for LangGraph workflow."""
from typing import Any, Dict, List, Optional
from ..core.compat import BaseModel, Field

class AnalysisState(BaseModel):
    """Section 9 of Flow.md: LangGraph State."""
    session_id: str
    job_id: str
    dataset_id: str
    question: str = ""

    # Schema & Plan
    dataset_schema: Optional[Dict[str, Any]] = None
    is_relevant: bool = True
    suggested_analyses: List[str] = Field(default_factory=list)
    analysis_plan: Optional[Dict[str, Any]] = None

    # Skill Resolution
    skill_found: bool = False
    skill_id: Optional[str] = None
    skill_version: Optional[int] = None
    analysis_method: Optional[Dict[str, Any]] = None
    generated_code: Optional[str] = None

    # Human Approval
    requires_approval: bool = False
    user_approved: Optional[bool] = None
    approval_comment: Optional[str] = None
    user_feedback: Optional[str] = None

    # SQL Execution
    sql_query: Optional[str] = None
    retrieved_data: Optional[List[Dict[str, Any]]] = None

    # Calculation & Validation
    sdk_output: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None

    # Visualization & Response
    chart_spec: Optional[Dict[str, Any]] = None
    markdown: Optional[str] = None

    # Workflow Status
    status: str = "pending"  # "pending", "awaiting_approval", "executing", "completed", "failed"
    error: Optional[str] = None
