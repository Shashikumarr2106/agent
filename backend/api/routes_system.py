"""System health, status, and analytics API endpoints."""
from datetime import datetime
from typing import Any, Dict
from ..services.database import db_service
from .schemas import HealthResponse, StatsResponse

try:
    from fastapi import APIRouter
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = object

router = APIRouter(tags=["System & Monitoring"]) if HAS_FASTAPI else None

def handle_health_check() -> Dict[str, Any]:
    """Verify database responsiveness and return system health summary."""
    try:
        conn = db_service._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    stats = db_service.get_system_stats()
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "skills_count": stats["total_skills"],
        "datasets_count": stats["total_datasets"],
        "timestamp": datetime.now().isoformat()
    }

def handle_system_stats() -> Dict[str, Any]:
    """Retrieve aggregate usage statistics across all entities."""
    stats = db_service.get_system_stats()
    stats["status"] = "healthy"
    return stats

if HAS_FASTAPI:
    @router.get("/health", response_model=HealthResponse)
    async def health_endpoint():
        """Health check endpoint for Kubernetes liveness/readiness probes."""
        return handle_health_check()

    @router.get("/stats", response_model=StatsResponse)
    async def stats_endpoint():
        """Aggregated operational metrics for dataset, skill, job, and session activity."""
        return handle_system_stats()
