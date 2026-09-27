"""SQL query generation and execution node for LangGraph workflow."""
import re
from typing import Any, Dict, List
from .state import AnalysisState
from ..mcp import mcp_client

def sql_execution_node(state: AnalysisState) -> AnalysisState:
    """Generates an optimal, secure SQL aggregation query and retrieves the data subset via MCP."""
    if not state.is_relevant or state.status == "awaiting_approval" or state.status == "failed":
        return state

    schema = state.dataset_schema or {}
    table_name = schema.get("table_name", f"dataset_{state.dataset_id}")
    question = state.question.lower()
    method = state.analysis_method or {}
    skill_id = state.skill_id or ""

    numeric_cols = schema.get("numeric_columns", [])
    cat_cols = schema.get("categorical_columns", [])
    dt_cols = schema.get("datetime_columns", [])

    # Find columns mentioned in user question
    matched_num = [c for c in numeric_cols if c.lower() in question]
    matched_cat = [c for c in cat_cols if c.lower() in question]
    matched_dt = [c for c in dt_cols if c.lower() in question]

    # Generate targeted SQL based on skill and question
    if "correlation" in skill_id or "regression" in skill_id or "correlation" in question:
        x_col = matched_num[0] if len(matched_num) >= 1 else (numeric_cols[0] if numeric_cols else "x")
        y_col = matched_num[1] if len(matched_num) >= 2 else (numeric_cols[1] if len(numeric_cols) > 1 else x_col)
        sql = f'SELECT "{x_col}", "{y_col}" FROM "{table_name}" WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL LIMIT 1000'

    elif "group_aggregation" in skill_id or (matched_cat and matched_num) or "by" in question:
        grp = matched_cat[0] if matched_cat else (cat_cols[0] if cat_cols else "category")
        val = matched_num[0] if matched_num else (numeric_cols[0] if numeric_cols else "value")
        agg = "AVG" if "avg" in question or "average" in question or "mean" in question else "SUM"
        sql = f'SELECT "{grp}", {agg}("{val}") AS "{val}" FROM "{table_name}" WHERE "{grp}" IS NOT NULL AND "{val}" IS NOT NULL GROUP BY "{grp}" ORDER BY "{val}" DESC LIMIT 100'

    elif "trend" in skill_id or matched_dt:
        dt = matched_dt[0] if matched_dt else (dt_cols[0] if dt_cols else "date")
        val = matched_num[0] if matched_num else (numeric_cols[0] if numeric_cols else "value")
        sql = f'SELECT "{dt}", AVG("{val}") AS "{val}" FROM "{table_name}" WHERE "{dt}" IS NOT NULL GROUP BY "{dt}" ORDER BY "{dt}" ASC LIMIT 200'

    elif "coefficient_variation" in skill_id or "cv" in question or "variation" in question:
        col = matched_num[0] if matched_num else (numeric_cols[0] if numeric_cols else "value")
        sql = f'SELECT "{col}" FROM "{table_name}" WHERE "{col}" IS NOT NULL LIMIT 2000'

    else:
        # Default: extract key numeric column
        col = matched_num[0] if matched_num else (numeric_cols[0] if numeric_cols else "*")
        sql = f'SELECT "{col}" FROM "{table_name}" WHERE "{col}" IS NOT NULL LIMIT 1000' if col != "*" else f'SELECT * FROM "{table_name}" LIMIT 500'

    state.sql_query = sql

    # Execute SQL via MCP
    exec_res = mcp_client.call("execute_sql", dataset_id=state.dataset_id, sql=sql)
    if exec_res.get("status") == "failed" or exec_res.get("error"):
        state.status = "failed"
        state.error = exec_res.get("error", "SQL execution failed")
        return state

    state.retrieved_data = exec_res.get("data", [])
    return state
