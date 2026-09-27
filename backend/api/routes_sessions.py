"""Session management API endpoints."""
import uuid
from typing import Any, Dict, List, Optional
from ..services.database import db_service
from .schemas import SessionCreateRequest

try:
    from fastapi import APIRouter, HTTPException, Query, Body
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = object

router = APIRouter(prefix="/sessions", tags=["Sessions"]) if HAS_FASTAPI else None

def handle_list_sessions(user_id: str = "default_user") -> List[Dict[str, Any]]:
    """Lists all conversation sessions for a user."""
    return db_service.list_sessions(user_id=user_id)

def handle_get_session(session_id: str) -> Dict[str, Any]:
    """Retrieves session details and chronological list of associated analysis jobs."""
    conn = db_service._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    s_row = cursor.fetchone()
    if not s_row:
        conn.close()
        return {"error": f"Session '{session_id}' not found", "status": 404}

    cursor.execute("""
        SELECT job_id, dataset_id, question, status, skill_id, skill_version, created_at, completed_at
        FROM analysis_jobs
        WHERE session_id = ?
        ORDER BY created_at ASC
    """, (session_id,))
    job_rows = cursor.fetchall()
    conn.close()

    return {
        "session_id": s_row["session_id"],
        "user_id": s_row["user_id"],
        "active_dataset_id": s_row["active_dataset_id"],
        "created_at": s_row["created_at"],
        "updated_at": s_row["updated_at"],
        "jobs": [dict(j) for j in job_rows]
    }

def handle_create_session(user_id: str = "default_user", active_dataset_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new session record."""
    session_id = f"s_{uuid.uuid4().hex[:8]}"
    conn = db_service._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (session_id, user_id, active_dataset_id)
        VALUES (?, ?, ?)
    """, (session_id, user_id, active_dataset_id))
    conn.commit()
    conn.close()
    return {
        "session_id": session_id,
        "user_id": user_id,
        "active_dataset_id": active_dataset_id,
        "message": f"Session '{session_id}' created successfully."
    }

def handle_delete_session(session_id: str) -> Dict[str, Any]:
    """Delete session and its associated jobs."""
    ok = db_service.delete_session(session_id)
    if not ok:
        return {"error": f"Session '{session_id}' not found", "status": 404}
    return {"success": True, "message": f"Session '{session_id}' and all associated jobs deleted."}

if HAS_FASTAPI:
    @router.get("")
    @router.get("/")
    async def list_sessions_endpoint(user_id: str = Query("default_user")):
        """List all conversation sessions for the active user."""
        return handle_list_sessions(user_id=user_id)

    @router.post("")
    @router.post("/")
    async def create_session_endpoint(payload: SessionCreateRequest):
        """Create a new conversational analysis session."""
        return handle_create_session(user_id=payload.user_id, active_dataset_id=payload.active_dataset_id)

    @router.get("/{session_id}")
    async def get_session_endpoint(session_id: str):
        """Retrieve session timeline and list of executed analysis jobs."""
        res = handle_get_session(session_id)
        if res.get("error"):
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    @router.delete("/{session_id}")
    async def delete_session_endpoint(session_id: str):
        """Delete session and clear associated jobs and execution logs."""
        res = handle_delete_session(session_id)
        if res.get("error"):
            raise HTTPException(status_code=404, detail=res["error"])
        return res
