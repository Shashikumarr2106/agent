"""Session management API endpoints."""
import json
from typing import Any, Dict
from ..services.database import db_service

def handle_get_session(session_id: str) -> Dict[str, Any]:
    """Retrieves session details and chronological list of associated analysis jobs."""
    conn = db_service._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    s_row = cursor.fetchone()
    if not s_row:
        conn.close()
        return {"error": f"Session '{session_id}' not found"}

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
