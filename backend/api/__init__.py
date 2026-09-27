"""API package exporting routers and handler functions."""
from .routes_datasets import (
    router as datasets_router,
    handle_upload_csv,
    handle_get_dataset,
    handle_list_datasets,
    handle_preview_dataset,
    handle_summary_dataset,
    handle_delete_dataset,
)
from .routes_chat import (
    router as chat_router,
    handle_chat_request,
)
from .routes_analysis import (
    router as analysis_router,
    handle_approve_analysis,
    handle_reject_analysis,
    handle_feedback,
    handle_direct_execute,
    handle_get_job,
)
from .routes_skills import (
    router as skills_router,
    handle_list_skills,
    handle_get_skill,
    handle_create_skill,
    handle_update_skill,
    handle_delete_skill,
    handle_search_skills,
)
from .routes_jobs import (
    router as jobs_router,
    handle_list_jobs,
    handle_get_job_logs,
)
from .routes_sessions import (
    router as sessions_router,
    handle_list_sessions,
    handle_get_session,
    handle_create_session,
    handle_delete_session,
)
from .routes_system import (
    router as system_router,
    handle_health_check,
    handle_system_stats,
)

__all__ = [
    # Routers
    "datasets_router",
    "chat_router",
    "analysis_router",
    "skills_router",
    "jobs_router",
    "sessions_router",
    "system_router",
    # Datasets
    "handle_upload_csv",
    "handle_get_dataset",
    "handle_list_datasets",
    "handle_preview_dataset",
    "handle_summary_dataset",
    "handle_delete_dataset",
    # Chat
    "handle_chat_request",
    # Analysis & Approval
    "handle_approve_analysis",
    "handle_reject_analysis",
    "handle_feedback",
    "handle_direct_execute",
    "handle_get_job",
    # Skills
    "handle_list_skills",
    "handle_get_skill",
    "handle_create_skill",
    "handle_update_skill",
    "handle_delete_skill",
    "handle_search_skills",
    # Jobs
    "handle_list_jobs",
    "handle_get_job_logs",
    # Sessions
    "handle_list_sessions",
    "handle_get_session",
    "handle_create_session",
    "handle_delete_session",
    # System
    "handle_health_check",
    "handle_system_stats",
]
