"""Chat and Analysis initiation API endpoints with LangGraph orchestration and streaming."""
import uuid
import json
import asyncio
from typing import Any, Dict, Optional
from ..graph.state import AnalysisState
from ..graph.graph import workflow_engine
from ..services.database import db_service
from .schemas import ChatRequest, ChatResponse

try:
    from fastapi import APIRouter, HTTPException, Body
    from fastapi.responses import StreamingResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = object

router = APIRouter(tags=["Chat & Workflow"]) if HAS_FASTAPI else None

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

async def chat_event_stream(dataset_id: str, question: str, session_id: Optional[str] = None):
    """Server-Sent Events generator yielding workflow execution milestones."""
    session_id = session_id or f"s_{uuid.uuid4().hex[:8]}"
    job_id = f"j_{uuid.uuid4().hex[:8]}"

    yield f"data: {json.dumps({'event': 'started', 'job_id': job_id, 'session_id': session_id})}\n\n"
    await asyncio.sleep(0.01)

    # Run workflow
    res = handle_chat_request(dataset_id, question, session_id)
    if res.get("requires_approval"):
        yield f"data: {json.dumps({'event': 'awaiting_approval', 'data': res})}\n\n"
    elif res.get("status") == "completed":
        yield f"data: {json.dumps({'event': 'completed', 'data': res})}\n\n"
    else:
        yield f"data: {json.dumps({'event': res.get('status', 'progress'), 'data': res})}\n\n"

if HAS_FASTAPI:
    @router.post("/chat", response_model=ChatResponse)
    async def chat_endpoint(payload: ChatRequest):
        """Send a natural language data question. Executes LangGraph orchestration."""
        res = handle_chat_request(
            dataset_id=payload.dataset_id,
            question=payload.question,
            session_id=payload.session_id
        )
        return res

    @router.post("/chat/stream")
    async def chat_stream_endpoint(payload: ChatRequest):
        """Stream conversational workflow milestones via Server-Sent Events (SSE)."""
        return StreamingResponse(
            chat_event_stream(payload.dataset_id, payload.question, payload.session_id),
            media_type="text/event-stream"
        )
