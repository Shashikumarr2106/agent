"""Human approval and job status API endpoints."""
import json
from typing import Any, Dict, Optional
from ..graph.state import AnalysisState
from ..graph.graph import workflow_engine
from ..services.database import db_service

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

def handle_get_job(job_id: str) -> Dict[str, Any]:
    """Retrieves full job status, results, charts, and execution logs."""
    state = _load_job_as_state(job_id)
    if not state:
        return {"error": f"Job '{job_id}' not found"}

    # Fetch execution logs
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
