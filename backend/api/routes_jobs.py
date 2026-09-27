"""Analysis Jobs and Execution Logs API endpoints."""
from typing import Any, Dict, List, Optional
from ..services.database import db_service
from .routes_analysis import handle_get_job

try:
    from fastapi import APIRouter, HTTPException, Query
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = object

router = APIRouter(prefix="/jobs", tags=["Jobs & Execution Logs"]) if HAS_FASTAPI else None

def handle_list_jobs(session_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Lists historical jobs with optional session or status filter."""
    return db_service.list_jobs(session_id=session_id, status=status, limit=limit)

def handle_get_job_logs(job_id: str) -> List[Dict[str, Any]]:
    """Retrieve granular step logs for an analysis job."""
    conn = db_service._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT log_id, job_id, step, status, input_json, output_json, error, timestamp
        FROM execution_logs
        WHERE job_id = ?
        ORDER BY timestamp ASC
    """, (job_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

if HAS_FASTAPI:
    @router.get("")
    @router.get("/")
    async def list_jobs_endpoint(
        session_id: Optional[str] = Query(None, description="Filter by session ID"),
        status: Optional[str] = Query(None, description="Filter by job status (completed, awaiting_approval, failed)"),
        limit: int = Query(50, ge=1, le=200, description="Max jobs to return")
    ):
        """List historical analysis jobs with optional filtering."""
        return handle_list_jobs(session_id=session_id, status=status, limit=limit)

    @router.get("/{job_id}")
    async def get_job_endpoint(job_id: str):
        """Retrieve full details, status, chart specification, markdown, and result for a job."""
        res = handle_get_job(job_id)
        if res.get("error"):
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    @router.get("/{job_id}/logs")
    async def get_job_logs_endpoint(job_id: str):
        """Retrieve execution milestone logs and timing for a job."""
        logs = handle_get_job_logs(job_id)
        return {"job_id": job_id, "logs_count": len(logs), "logs": logs}
