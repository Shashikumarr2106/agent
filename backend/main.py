"""Main application entry point configuring FastAPI, MCP, and modular HTTP routing."""
import os
import sys
import json
from pathlib import Path

# Ensure project root is in sys.path so both direct execution and module execution work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Any, Optional

try:
    from .core.config import settings
    from .services.database import db_service
    from .services.skill_service import skill_service
    from .mcp import mcp_server
    from .api import (
        datasets_router,
        chat_router,
        analysis_router,
        skills_router,
        jobs_router,
        sessions_router,
        system_router,
        handle_upload_csv,
        handle_get_dataset,
        handle_list_datasets,
        handle_preview_dataset,
        handle_summary_dataset,
        handle_delete_dataset,
        handle_chat_request,
        handle_approve_analysis,
        handle_reject_analysis,
        handle_feedback,
        handle_direct_execute,
        handle_get_job,
        handle_list_jobs,
        handle_get_job_logs,
        handle_list_skills,
        handle_get_skill,
        handle_search_skills,
        handle_list_sessions,
        handle_get_session,
        handle_create_session,
        handle_delete_session,
        handle_health_check,
        handle_system_stats,
    )
except (ImportError, ValueError):
    from backend.core.config import settings
    from backend.services.database import db_service
    from backend.services.skill_service import skill_service
    from backend.mcp import mcp_server
    from backend.api import (
        datasets_router,
        chat_router,
        analysis_router,
        skills_router,
        jobs_router,
        sessions_router,
        system_router,
        handle_upload_csv,
        handle_get_dataset,
        handle_list_datasets,
        handle_preview_dataset,
        handle_summary_dataset,
        handle_delete_dataset,
        handle_chat_request,
        handle_approve_analysis,
        handle_reject_analysis,
        handle_feedback,
        handle_direct_execute,
        handle_get_job,
        handle_list_jobs,
        handle_get_job_logs,
        handle_list_skills,
        handle_get_skill,
        handle_search_skills,
        handle_list_sessions,
        handle_get_session,
        handle_create_session,
        handle_delete_session,
        handle_health_check,
        handle_system_stats,
    )

# Detect if FastAPI is available
try:
    from fastapi import FastAPI, APIRouter
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

if HAS_FASTAPI:
    app = FastAPI(
        title="AI Data Analyst Agent API",
        description="Comprehensive REST API for AI Data Analyst Agent — FastAPI, LangGraph Orchestration, MCP Server, pgvector Skill Store, and Deterministic Analysis SDK.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 1. Mount root API routers (directly accessible at /datasets, /chat, /analysis, /skills, /jobs, /sessions, /health)
    app.include_router(datasets_router)
    app.include_router(chat_router)
    app.include_router(analysis_router)
    app.include_router(skills_router)
    app.include_router(jobs_router)
    app.include_router(sessions_router)
    app.include_router(system_router)

    # 2. Mount versioned API routers under /api/v1 prefix
    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(datasets_router)
    api_v1.include_router(chat_router)
    api_v1.include_router(analysis_router)
    api_v1.include_router(skills_router)
    api_v1.include_router(jobs_router)
    api_v1.include_router(sessions_router)
    api_v1.include_router(system_router)
    app.include_router(api_v1)

    # 3. Serve static frontend and root UI route
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False)
        async def serve_index():
            index_path = frontend_dir / "index.html"
            if index_path.exists():
                return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
            return HTMLResponse("<h1>AI Data Analyst Agent API is running</h1>")

else:
    app = None

# Standalone Pure-Python HTTP Server (zero external dependencies fallback)
def run_standalone_server(port: int = 8000):
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import parse_qs, urlparse

    class AgentHTTPHandler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, data: Any):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Filename")
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Filename")
            self.end_headers()

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            # Strip /api/v1 prefix if present
            clean_path = path[7:] if path.startswith("/api/v1") else path

            if clean_path in ("/", "/index.html"):
                frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
                if frontend_path.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(frontend_path.read_bytes())
                else:
                    self._send_json(200, {"message": "AI Data Analyst Agent API is active"})
                return

            if clean_path.startswith("/static/"):
                subpath = clean_path[len("/static/"):]
                fpath = Path(__file__).resolve().parent.parent / "frontend" / subpath
                if fpath.exists():
                    ext = fpath.suffix.lower()
                    content_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png" if ext == ".png" else "text/javascript" if ext == ".js" else "text/css" if ext == ".css" else "text/plain"
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.end_headers()
                    self.wfile.write(fpath.read_bytes())
                    return

            if clean_path in ("/health",):
                self._send_json(200, handle_health_check())
            elif clean_path in ("/stats",):
                self._send_json(200, handle_system_stats())
            elif clean_path in ("/datasets", "/datasets/"):
                self._send_json(200, handle_list_datasets())
            elif clean_path.startswith("/datasets/") and clean_path.endswith("/preview"):
                ds_id = clean_path.split("/")[2]
                self._send_json(200, handle_preview_dataset(ds_id))
            elif clean_path.startswith("/datasets/") and clean_path.endswith("/summary"):
                ds_id = clean_path.split("/")[2]
                self._send_json(200, handle_summary_dataset(ds_id))
            elif clean_path.startswith("/datasets/"):
                ds_id = clean_path.split("/")[2]
                self._send_json(200, handle_get_dataset(ds_id))
            elif clean_path in ("/skills", "/skills/"):
                self._send_json(200, handle_list_skills())
            elif clean_path.startswith("/skills/"):
                sk_id = clean_path.split("/")[2]
                self._send_json(200, handle_get_skill(sk_id))
            elif clean_path in ("/jobs", "/jobs/"):
                self._send_json(200, handle_list_jobs())
            elif clean_path.startswith("/jobs/") and clean_path.endswith("/logs"):
                job_id = clean_path.split("/")[2]
                self._send_json(200, handle_get_job_logs(job_id))
            elif clean_path.startswith("/jobs/"):
                job_id = clean_path.split("/")[2]
                self._send_json(200, handle_get_job(job_id))
            elif clean_path in ("/sessions", "/sessions/"):
                self._send_json(200, handle_list_sessions())
            elif clean_path.startswith("/sessions/"):
                session_id = clean_path.split("/")[2]
                self._send_json(200, handle_get_session(session_id))
            else:
                self._send_json(404, {"error": "Not Found"})

        def do_POST(self):
            parsed = urlparse(self.path)
            clean_path = parsed.path[7:] if parsed.path.startswith("/api/v1") else parsed.path
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            if clean_path == "/datasets/upload":
                filename = self.headers.get("X-Filename", "dataset.csv")
                res = handle_upload_csv(filename, body)
                self._send_json(200, res)
            else:
                try:
                    payload = json.loads(body.decode("utf-8")) if body else {}
                except Exception:
                    payload = {}

                if clean_path == "/chat":
                    res = handle_chat_request(
                        dataset_id=payload.get("dataset_id"),
                        question=payload.get("question", ""),
                        session_id=payload.get("session_id")
                    )
                    self._send_json(200, res)
                elif clean_path == "/analysis/approve":
                    res = handle_approve_analysis(payload.get("job_id"))
                    self._send_json(200, res)
                elif clean_path == "/analysis/reject":
                    res = handle_reject_analysis(payload.get("job_id"), payload.get("modification_instructions"))
                    self._send_json(200, res)
                elif clean_path == "/analysis/feedback":
                    res = handle_feedback(payload.get("job_id"), payload.get("feedback"))
                    self._send_json(200, res)
                elif clean_path == "/analysis/direct-execute":
                    res = handle_direct_execute(payload.get("dataset_id"), payload.get("method"), payload.get("params", {}))
                    self._send_json(200, res)
                elif clean_path == "/skills/search":
                    res = handle_search_skills(payload.get("query", ""), threshold=payload.get("threshold", 0.5), top_k=payload.get("top_k", 5))
                    self._send_json(200, res)
                elif clean_path in ("/sessions", "/sessions/"):
                    res = handle_create_session(user_id=payload.get("user_id", "default_user"), active_dataset_id=payload.get("active_dataset_id"))
                    self._send_json(200, res)
                else:
                    self._send_json(404, {"error": "Endpoint Not Found"})

        def do_DELETE(self):
            parsed = urlparse(self.path)
            clean_path = parsed.path[7:] if parsed.path.startswith("/api/v1") else parsed.path
            if clean_path.startswith("/datasets/"):
                ds_id = clean_path.split("/")[2]
                self._send_json(200, handle_delete_dataset(ds_id))
            elif clean_path.startswith("/sessions/"):
                session_id = clean_path.split("/")[2]
                self._send_json(200, handle_delete_session(session_id))
            else:
                self._send_json(404, {"error": "Endpoint Not Found"})

    server = HTTPServer(("0.0.0.0", port), AgentHTTPHandler)
    print(f"🚀 AI Data Analyst Agent running at http://localhost:{port}", flush=True)
    server.serve_forever()

if __name__ == "__main__":
    print(f"⚡ Launching AI Data Analyst Agent on port {settings.APP_PORT}...", flush=True)
    if HAS_FASTAPI:
        import uvicorn
        uvicorn.run("backend.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.DEBUG)
    else:
        run_standalone_server(port=settings.APP_PORT)
