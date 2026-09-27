"""LangGraph Workflow Orchestration Engine."""
import uuid
import json
from datetime import datetime
from typing import Any, Dict, Optional
from .state import AnalysisState
from .planner import check_relevance_and_plan_node
from .skill_node import skill_resolution_node
from .approval_node import human_approval_node
from .sql_node import sql_execution_node
from .analysis_node import analysis_execution_node
from .validation_node import validation_node
from .chart_node import chart_generation_node
from ..services.database import db_service

class AnalysisGraphOrchestrator:
    """Orchestrates the end-to-end analysis workflow graph with checkpointing and state persistence."""

    def _log_step(self, job_id: str, step: str, status: str, input_data: Any = None, output_data: Any = None, error: str = None):
        """Records granular step-by-step execution log into database."""
        conn = db_service._get_connection()
        cursor = conn.cursor()
        log_id = f"log_{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO execution_logs (log_id, job_id, step, status, input_json, output_json, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id,
            job_id,
            step,
            status,
            json.dumps(input_data, default=str) if input_data else None,
            json.dumps(output_data, default=str) if output_data else None,
            error
        ))
        conn.commit()
        conn.close()

    def _persist_job_state(self, state: AnalysisState):
        """Persists current analysis job state to database."""
        conn = db_service._get_connection()
        cursor = conn.cursor()
        completed_at = datetime.now().isoformat() if state.status in ("completed", "failed", "rejected") else None
        cursor.execute("""
            INSERT OR REPLACE INTO analysis_jobs (
                job_id, session_id, dataset_id, question, status,
                analysis_plan_json, skill_found, skill_id, skill_version,
                proposed_method_json, sql_query, user_approved, user_feedback,
                sdk_output_json, chart_spec_json, markdown, error, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            state.job_id,
            state.session_id,
            state.dataset_id,
            state.question,
            state.status,
            json.dumps(state.analysis_plan, default=str) if state.analysis_plan else None,
            1 if state.skill_found else 0,
            state.skill_id,
            state.skill_version,
            json.dumps(state.analysis_method, default=str) if state.analysis_method else None,
            state.sql_query,
            1 if state.user_approved is True else (0 if state.user_approved is False else None),
            state.user_feedback,
            json.dumps(state.sdk_output, default=str) if state.sdk_output else None,
            json.dumps(state.chart_spec, default=str) if state.chart_spec else None,
            state.markdown,
            state.error,
            completed_at
        ))
        conn.commit()
        conn.close()

    def run(self, state: AnalysisState) -> AnalysisState:
        """Executes the workflow graph starting from current state until completion or approval pause."""
        job_id = state.job_id

        # Node 1: Plan and check relevance
        self._log_step(job_id, "check_relevance_and_plan", "started")
        state = check_relevance_and_plan_node(state)
        self._log_step(job_id, "check_relevance_and_plan", "completed", output_data=state.analysis_plan)
        if not state.is_relevant or state.status == "failed":
            self._persist_job_state(state)
            return state

        # Node 2: Skill resolution (pgvector search or dynamic method formulation)
        self._log_step(job_id, "skill_resolution", "started")
        state = skill_resolution_node(state)
        self._log_step(job_id, "skill_resolution", "completed", output_data={"skill_id": state.skill_id, "found": state.skill_found})

        # Node 3: Human approval breakpoint (Section 24)
        if state.requires_approval and state.user_approved is None:
            state.status = "awaiting_approval"
            self._log_step(job_id, "human_approval", "paused_awaiting_user_approval")
            self._persist_job_state(state)
            return state

        state = human_approval_node(state)
        if state.status in ("awaiting_approval", "rejected"):
            self._persist_job_state(state)
            return state

        # Node 4: Generate and execute SQL query
        self._log_step(job_id, "sql_execution", "started")
        state = sql_execution_node(state)
        if state.status == "failed":
            self._log_step(job_id, "sql_execution", "error", error=state.error)
            self._persist_job_state(state)
            return state
        self._log_step(job_id, "sql_execution", "completed", output_data={"sql": state.sql_query, "rows": len(state.retrieved_data or [])})

        # Node 5: Analysis SDK numerical computation
        self._log_step(job_id, "analysis_execution", "started")
        state = analysis_execution_node(state)
        if state.status == "failed":
            self._log_step(job_id, "analysis_execution", "error", error=state.error)
            self._persist_job_state(state)
            return state
        self._log_step(job_id, "analysis_execution", "completed", output_data=state.sdk_output)

        # Node 6: Validation
        self._log_step(job_id, "validation", "started")
        state = validation_node(state)
        if state.status == "failed":
            self._log_step(job_id, "validation", "error", error=state.error)
            self._persist_job_state(state)
            return state
        self._log_step(job_id, "validation", "completed", output_data=state.validation_result)

        # Node 7: Chart spec and Markdown generation
        self._log_step(job_id, "chart_generation", "started")
        state = chart_generation_node(state)
        self._log_step(job_id, "chart_generation", "completed", output_data={"chart": bool(state.chart_spec)})

        state.status = "completed"
        self._persist_job_state(state)
        return state

workflow_engine = AnalysisGraphOrchestrator()
