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

db_service = DatabaseService()
