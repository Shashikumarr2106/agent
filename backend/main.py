"""Main application entry point configuring FastAPI, MCP, and HTTP routing."""
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
        handle_upload_csv,
        handle_get_dataset,
        handle_list_datasets,
        handle_chat_request,
        handle_approve_analysis,
        handle_reject_analysis,
        handle_get_job,
        handle_feedback,
        handle_get_session,
    )
except (ImportError, ValueError):
    from backend.core.config import settings
    from backend.services.database import db_service
    from backend.services.skill_service import skill_service
    from backend.mcp import mcp_server
    from backend.api import (
        handle_upload_csv,
        handle_get_dataset,
        handle_list_datasets,
        handle_chat_request,
        handle_approve_analysis,
        handle_reject_analysis,
        handle_get_job,
        handle_feedback,
        handle_get_session,
    )

# Detect if FastAPI is available
try:
    from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

if HAS_FASTAPI:
    app = FastAPI(
        title="AI Data Analyst Agent",
        description="FastAPI + LangGraph + MCP + pgvector + Analysis SDK",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/datasets/upload")
    async def upload_dataset(file: UploadFile = File(...)):
        content = await file.read()
        return handle_upload_csv(file.filename, content)

    @app.get("/datasets/{dataset_id}")
    async def get_dataset(dataset_id: str):
        res = handle_get_dataset(dataset_id)
        if "error" in res:
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    @app.get("/datasets")
    async def list_datasets():
        return handle_list_datasets()

    @app.post("/chat")
    async def chat(payload: dict = Body(...)):
        dataset_id = payload.get("dataset_id")
        if not dataset_id:
            raise HTTPException(status_code=400, detail="dataset_id is required")
        question = payload.get("question", "")
        session_id = payload.get("session_id")
        return handle_chat_request(dataset_id=dataset_id, question=question, session_id=session_id)

    @app.post("/analysis/approve")
    async def approve_analysis(payload: dict = Body(...)):
        job_id = payload.get("job_id")
        if not job_id:
            raise HTTPException(status_code=400, detail="job_id is required")
        return handle_approve_analysis(job_id)

    @app.post("/analysis/reject")
    async def reject_analysis(payload: dict = Body(...)):
        job_id = payload.get("job_id")
        if not job_id:
            raise HTTPException(status_code=400, detail="job_id is required")
        return handle_reject_analysis(job_id, payload.get("modification_instructions"))

    @app.get("/jobs/{job_id}")
    async def get_job(job_id: str):
        res = handle_get_job(job_id)
        if "error" in res:
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    @app.post("/analysis/feedback")
    async def submit_feedback(payload: dict = Body(...)):
        job_id = payload.get("job_id")
        feedback = payload.get("feedback")
        if not job_id or not feedback:
            raise HTTPException(status_code=400, detail="job_id and feedback are required")
        return handle_feedback(job_id, feedback)

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        res = handle_get_session(session_id)
        if "error" in res:
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    # Serve static frontend if directory exists
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
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
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/" or path == "/index.html":
                frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
                if frontend_path.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(frontend_path.read_bytes())
                else:
                    self._send_json(200, {"message": "AI Data Analyst Agent API is active"})
                return

            if path.startswith("/static/"):
                subpath = path[len("/static/"):]
                fpath = Path(__file__).resolve().parent.parent / "frontend" / subpath
                if fpath.exists():
                    content_type = "text/javascript" if fpath.suffix == ".js" else "text/css" if fpath.suffix == ".css" else "text/plain"
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.end_headers()
                    self.wfile.write(fpath.read_bytes())
                    return

            if path == "/datasets":
                self._send_json(200, handle_list_datasets())
            elif path.startswith("/datasets/"):
                ds_id = path.split("/")[2]
                self._send_json(200, handle_get_dataset(ds_id))
            elif path.startswith("/jobs/"):
                job_id = path.split("/")[2]
                self._send_json(200, handle_get_job(job_id))
            elif path.startswith("/sessions/"):
                session_id = path.split("/")[2]
                self._send_json(200, handle_get_session(session_id))
            else:
                self._send_json(404, {"error": "Not Found"})

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            if path == "/datasets/upload":
                # Handle raw CSV or multipart payload
                filename = self.headers.get("X-Filename", "dataset.csv")
                res = handle_upload_csv(filename, body)
                self._send_json(200, res)
            else:
                try:
                    payload = json.loads(body.decode("utf-8")) if body else {}
                except Exception:
                    payload = {}

                if path == "/chat":
                    res = handle_chat_request(
                        dataset_id=payload.get("dataset_id"),
                        question=payload.get("question", ""),
                        session_id=payload.get("session_id")
                    )
                    self._send_json(200, res)
                elif path == "/analysis/approve":
                    res = handle_approve_analysis(payload.get("job_id"))
                    self._send_json(200, res)
                elif path == "/analysis/reject":
                    res = handle_reject_analysis(payload.get("job_id"), payload.get("modification_instructions"))
                    self._send_json(200, res)
                elif path == "/analysis/feedback":
                    res = handle_feedback(payload.get("job_id"), payload.get("feedback"))
                    self._send_json(200, res)
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
