"""Database service supporting PostgreSQL/pgvector with SQLite local fallback."""
import sqlite3
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from ..core.config import settings

class DatabaseService:
    def __init__(self):
        self.db_path = settings.DATA_DIR / "agent.db"
        self._init_sqlite_tables()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite_tables(self):
        """Initialize standard relational tables for application metadata."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Datasets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                user_id TEXT,
                filename TEXT,
                table_name TEXT UNIQUE,
                schema_json TEXT,
                row_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Skills
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                skill_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                current_version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Skill Versions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT,
                version INTEGER,
                name TEXT,
                description TEXT,
                required_inputs TEXT,
                formula TEXT,
                logic TEXT,
                code TEXT,
                examples_json TEXT,
                validation_rules_json TEXT,
                embedding_json TEXT,
                created_from_job TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(skill_id, version)
            )
        """)

        # Analysis Jobs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_jobs (
                job_id TEXT PRIMARY KEY,
                session_id TEXT,
                dataset_id TEXT,
                question TEXT,
                status TEXT,
                analysis_plan_json TEXT,
                skill_found INTEGER DEFAULT 0,
                skill_id TEXT,
                skill_version INTEGER,
                proposed_method_json TEXT,
                sql_query TEXT,
                user_approved INTEGER DEFAULT NULL,
                user_feedback TEXT,
                sdk_output_json TEXT,
                chart_spec_json TEXT,
                markdown TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)

        # Execution Logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                log_id TEXT PRIMARY KEY,
                job_id TEXT,
                step TEXT,
                status TEXT,
                input_json TEXT,
                output_json TEXT,
                error TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                active_dataset_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def validate_sql_security(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Enforces Section 37 of Flow.md (Security for SQL: SELECT only, no DDL/DML)."""
        clean_sql = re.sub(r'--.*?$|/\*.*?\*/', '', sql, flags=re.MULTILINE).strip()
        first_word = clean_sql.split()[0].upper() if clean_sql.split() else ""
        if first_word not in ("SELECT", "WITH"):
            return False, f"Only SELECT or WITH queries are permitted. Blocked query starting with '{first_word}'."

        forbidden = [
            r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b",
            r"\bALTER\b", r"\bCREATE\b", r"\bTRUNCATE\b", r"\bGRANT\b",
            r"\bREVOKE\b", r"\bEXEC\b", r"\bEXECUTE\b", r"\bATTACH\b"
        ]
        for pattern in forbidden:
            if re.search(pattern, clean_sql, re.IGNORECASE):
                return False, f"SQL statement contains forbidden keyword matching '{pattern}'."

        return True, None

    def execute_dataset_sql(self, sql: str, params: tuple = ()) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Executes a validated SELECT query against the dataset database."""
        is_safe, error_msg = self.validate_sql_security(sql)
        if not is_safe:
            return [], error_msg

        # Enforce row limit if not specified
        clean_sql = sql.strip().rstrip(";")
        if not re.search(r'\bLIMIT\b', clean_sql, re.IGNORECASE):
            clean_sql += f" LIMIT {settings.SQL_ROW_LIMIT}"

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(clean_sql, params)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            conn.close()
            return results, None
        except Exception as e:
            return [], f"SQL execution failed: {str(e)}"

    def list_jobs(self, session_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List historical analysis jobs with optional filtering."""
        conn = self._get_connection()
        cursor = conn.cursor()
        query = "SELECT job_id, session_id, dataset_id, question, status, skill_id, skill_version, created_at, completed_at FROM analysis_jobs"
        conditions = []
        params = []
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += f" ORDER BY created_at DESC LIMIT {max(1, min(limit, 200))}"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def list_sessions(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        """List all user sessions with job count and dataset details."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.session_id, s.user_id, s.active_dataset_id, s.created_at, s.updated_at,
                   d.filename as active_dataset_name,
                   (SELECT COUNT(*) FROM analysis_jobs WHERE session_id = s.session_id) as job_count
            FROM sessions s
            LEFT JOIN datasets d ON s.active_dataset_id = d.dataset_id
            WHERE s.user_id = ?
            ORDER BY s.updated_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: str) -> bool:
        """Delete session and associated jobs and logs."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM execution_logs WHERE job_id IN (SELECT job_id FROM analysis_jobs WHERE session_id = ?)", (session_id,))
            cursor.execute("DELETE FROM analysis_jobs WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_system_stats(self) -> Dict[str, Any]:
        """Aggregate system-wide dataset, skill, job, and session metrics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        datasets_count = cursor.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
        skills_count = cursor.execute("SELECT COUNT(*) FROM skills WHERE status = 'active'").fetchone()[0]
        jobs_count = cursor.execute("SELECT COUNT(*) FROM analysis_jobs").fetchone()[0]
        sessions_count = cursor.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        conn.close()
        return {
            "total_datasets": datasets_count,
            "total_jobs": jobs_count,
            "total_skills": skills_count,
            "total_sessions": sessions_count
        }

db_service = DatabaseService()
