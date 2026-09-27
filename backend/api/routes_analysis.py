"""Human approval, feedback, and direct execution API endpoints."""
import json
from typing import Any, Dict, Optional
from ..graph.state import AnalysisState
from ..graph.graph import workflow_engine
from ..services.database import db_service
from ..services.skill_service import skill_service
from ..services.ingestion import ingestion_service
from ..sdk import sdk
from .schemas import ApproveRequest, RejectRequest, FeedbackRequest, DirectExecuteRequest

try:
    from fastapi import APIRouter, HTTPException, Body
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = object

router = APIRouter(prefix="/analysis", tags=["Analysis & Approval"]) if HAS_FASTAPI else None

def _load_job_as_state(job_id: str) -> Optional[AnalysisState]:
    conn = db_service._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM analysis_jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None

    state = AnalysisState(
        session_id=row["session_id"],
        job_id=row["job_id"],
        dataset_id=row["dataset_id"],
        question=row["question"] or "",
        status=row["status"],
        analysis_plan=json.loads(row["analysis_plan_json"]) if row["analysis_plan_json"] else None,
        skill_found=bool(row["skill_found"]),
        skill_id=row["skill_id"],
        skill_version=row["skill_version"],
        analysis_method=json.loads(row["proposed_method_json"]) if row["proposed_method_json"] else None,
        sql_query=row["sql_query"],
        user_approved=bool(row["user_approved"]) if row["user_approved"] is not None else None,
        user_feedback=row["user_feedback"],
        sdk_output=json.loads(row["sdk_output_json"]) if row["sdk_output_json"] else None,
        chart_spec=json.loads(row["chart_spec_json"]) if row["chart_spec_json"] else None,
        markdown=row["markdown"],
        error=row["error"],
        requires_approval=(row["status"] == "awaiting_approval")
    )
    return state

def handle_approve_analysis(job_id: str) -> Dict[str, Any]:
    """Resumes paused workflow after human approval."""
    state = _load_job_as_state(job_id)
    if not state:
        return {"error": f"Job '{job_id}' not found", "status": "not_found"}

    if state.status != "awaiting_approval":
        return {"error": f"Job is in '{state.status}' state, not awaiting approval.", "status": "invalid_state"}

    state.user_approved = True
    state.requires_approval = False
    state.status = "executing"

    resulting_state = workflow_engine.run(state)

    return {
        "job_id": resulting_state.job_id,
        "status": resulting_state.status,
        "markdown": resulting_state.markdown,
        "chart": resulting_state.chart_spec,
        "sdk_output": resulting_state.sdk_output,
        "error": resulting_state.error
    }

def handle_reject_analysis(job_id: str, modification_instructions: Optional[str] = None) -> Dict[str, Any]:
    """Rejects or requests modifications to proposed analysis method."""
    state = _load_job_as_state(job_id)
    if not state:
        return {"error": f"Job '{job_id}' not found", "status": "not_found"}

    state.user_approved = False
    state.approval_comment = modification_instructions

    resulting_state = workflow_engine.run(state)

    return {
        "job_id": resulting_state.job_id,
        "status": resulting_state.status,
        "message": "Analysis method modification requested." if modification_instructions else "Analysis rejected.",
        "proposed_method": resulting_state.analysis_method,
        "error": resulting_state.error
    }

def handle_feedback(job_id: str, feedback: str) -> Dict[str, Any]:
    """Section 27: Processes user feedback ('Result is wrong'), creates skill v2, re-runs."""
    state = _load_job_as_state(job_id)
    if not state:
        return {"error": f"Job '{job_id}' not found"}

    if not state.skill_id:
        return {"error": "No skill associated with this job to revise."}

    # Understand and validate correction
    fb_low = feedback.lower()
    modifications = {}

    if "population" in fb_low and ("standard deviation" in fb_low or "std" in fb_low or "cv" in fb_low):
        modifications["logic"] = "Use population standard deviation (ddof=0) instead of sample standard deviation."
        modifications["formula"] = "CV = (std_pop / mean) * 100"
    elif "spearman" in fb_low:
        modifications["name"] = "Spearman Rank Correlation Analysis"
        modifications["logic"] = "Use non-parametric Spearman rank-order correlation."
        modifications["formula"] = "rho = 1 - (6 * Σ d² / (n(n² - 1)))"
    elif "median" in fb_low:
        modifications["logic"] = "Use median instead of mean for central tendency."
    else:
        modifications["logic"] = f"Adjusted calculation according to feedback: '{feedback}'"

    # Create new skill version (Section 26 & 27)
    try:
        new_version = skill_service.update_skill_version(
            skill_id=state.skill_id,
            modifications=modifications,
            feedback=feedback
        )
    except Exception as e:
        return {"error": f"Failed to create new skill version: {str(e)}"}

    # Re-run analysis with new skill version
    state.skill_version = new_version.version
    state.user_feedback = feedback
    state.analysis_method = new_version.model_dump()
    state.status = "executing"

    resulting_state = workflow_engine.run(state)

    return {
        "job_id": resulting_state.job_id,
        "status": resulting_state.status,
        "revised_skill": {
            "skill_id": new_version.skill_id,
            "version": new_version.version,
            "logic": new_version.logic
        },
        "markdown": resulting_state.markdown,
        "chart": resulting_state.chart_spec,
        "sdk_output": resulting_state.sdk_output,
        "error": resulting_state.error
    }

def handle_direct_execute(dataset_id: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an SDK statistical routine directly on dataset."""
    schema = ingestion_service.get_dataset(dataset_id)
    if not schema:
        return {"error": f"Dataset '{dataset_id}' not found"}

    rows, err = db_service.execute_dataset_sql(f'SELECT * FROM "{schema.table_name}"')
    if err:
        return {"error": err}

    try:
        result = sdk.run(method, rows, **params)
        return {
            "dataset_id": dataset_id,
            "method": method,
            "status": result.status,
            "value": result.value,
            "sample_size": result.sample_size,
            "metric": result.metric,
            "summary": result.summary,
            "details": result.details,
            "error": result.error
        }
    except Exception as e:
        return {"error": f"Direct SDK execution failed: {str(e)}"}

def handle_get_job(job_id: str) -> Dict[str, Any]:
    """Retrieves full job status, results, charts, and execution logs."""
    state = _load_job_as_state(job_id)
    if not state:
        return {"error": f"Job '{job_id}' not found"}

    conn = db_service._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT step, status, error, timestamp FROM execution_logs WHERE job_id = ? ORDER BY timestamp ASC", (job_id,))
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "job_id": state.job_id,
        "session_id": state.session_id,
        "dataset_id": state.dataset_id,
        "question": state.question,
        "status": state.status,
        "analysis_plan": state.analysis_plan,
        "skill_id": state.skill_id,
        "skill_version": state.skill_version,
        "proposed_method": state.analysis_method,
        "sql_query": state.sql_query,
        "sdk_output": state.sdk_output,
        "chart": state.chart_spec,
        "markdown": state.markdown,
        "error": state.error,
        "logs": logs
    }

# --- FastAPI Router Endpoints ---
if HAS_FASTAPI:
    @router.post("/approve")
    async def approve_analysis(payload: ApproveRequest):
        """Approve proposed analysis method (Section 24). Saves skill and executes calculation."""
        res = handle_approve_analysis(payload.job_id)
        if res.get("error") and res.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    @router.post("/reject")
    async def reject_analysis(payload: RejectRequest):
        """Reject proposed analysis method or provide modification instructions."""
        res = handle_reject_analysis(payload.job_id, payload.modification_instructions)
        if res.get("error") and res.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    @router.post("/feedback")
    async def submit_feedback(payload: FeedbackRequest):
        """Submit feedback/correction (Section 27). Creates skill v2 without overwriting v1."""
        res = handle_feedback(payload.job_id, payload.feedback)
        if res.get("error") and "not found" in res.get("error", "").lower():
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    @router.post("/direct-execute")
    async def direct_execute(payload: DirectExecuteRequest):
        """Execute a deterministic statistical method directly through Analysis SDK."""
        res = handle_direct_execute(payload.dataset_id, payload.method, payload.params)
        if res.get("error"):
            raise HTTPException(status_code=400, detail=res["error"])
        return res
