"""Chat and Analysis initiation API endpoints."""
import uuid
from typing import Any, Dict, Optional
from ..graph.state import AnalysisState
from ..graph.graph import workflow_engine
from ..services.database import db_service

def handle_chat_request(
    dataset_id: str,
    question: str = "",
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Handles user question, initiates LangGraph workflow, returns immediate result or approval pause."""
    session_id = session_id or f"s_{uuid.uuid4().hex[:8]}"
    job_id = f"j_{uuid.uuid4().hex[:8]}"

    # Update or insert session
    conn = db_service._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (session_id, user_id, active_dataset_id)
        VALUES (?, 'default_user', ?)
        ON CONFLICT(session_id) DO UPDATE SET active_dataset_id = ?, updated_at = CURRENT_TIMESTAMP
    """, (session_id, dataset_id, dataset_id))
    conn.commit()
    conn.close()

    # Create initial LangGraph state
    state = AnalysisState(
        session_id=session_id,
        job_id=job_id,
        dataset_id=dataset_id,
        question=question
    )

    # Execute workflow graph
    resulting_state = workflow_engine.run(state)

    return {
        "job_id": resulting_state.job_id,
        "session_id": resulting_state.session_id,
        "dataset_id": resulting_state.dataset_id,
        "status": resulting_state.status,
        "question": resulting_state.question,
        "is_relevant": resulting_state.is_relevant,
        "requires_approval": resulting_state.requires_approval,
        "proposed_method": resulting_state.analysis_method if resulting_state.requires_approval else None,
        "analysis_plan": resulting_state.analysis_plan,
        "markdown": resulting_state.markdown,
        "chart": resulting_state.chart_spec,
        "sdk_output": resulting_state.sdk_output,
        "error": resulting_state.error
    }
