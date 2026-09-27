"""Analysis SDK execution node for LangGraph workflow."""
from typing import Any, Dict
from .state import AnalysisState
from ..mcp import mcp_client

def analysis_execution_node(state: AnalysisState) -> AnalysisState:
    """Executes deterministic calculations through the Analysis SDK via MCP."""
    if not state.is_relevant or state.status == "awaiting_approval" or state.status == "failed":
        return state

    data = state.retrieved_data or []
    if not data:
        state.status = "failed"
        state.error = "No data returned by SQL query to perform analysis."
        return state

    skill_id = state.skill_id or ""
    schema = state.dataset_schema or {}
    num_cols = schema.get("numeric_columns", [])
    cat_cols = schema.get("categorical_columns", [])
    dt_cols = schema.get("datetime_columns", [])
    q_low = state.question.lower()

    # Determine SDK method and parameters
    if "correlation" in skill_id or "correlation" in q_low:
        cols = list(data[0].keys())
        x_col = cols[0]
        y_col = cols[1] if len(cols) > 1 else cols[0]
        res = mcp_client.call("run_analysis", method="pearson_correlation", data=data, params={"x_col": x_col, "y_col": y_col})

    elif "linear_regression" in skill_id or "regression" in q_low:
        cols = list(data[0].keys())
        x_col = cols[0]
        y_col = cols[1] if len(cols) > 1 else cols[0]
        res = mcp_client.call("run_analysis", method="linear_regression", data=data, params={"x_col": x_col, "y_col": y_col})

    elif "coefficient_variation" in skill_id or "variation" in q_low or "cv" in q_low:
        col = list(data[0].keys())[0]
        res = mcp_client.call("run_analysis", method="coefficient_of_variation", data=data, params={"column": col})

    elif "group_aggregation" in skill_id or len(data[0].keys()) >= 2 and any(k in cat_cols for k in data[0].keys()):
        cols = list(data[0].keys())
        grp_col = cols[0]
        val_col = cols[1] if len(cols) > 1 else cols[0]
        res = mcp_client.call("run_analysis", method="group_aggregation", data=data, params={"group_col": grp_col, "value_col": val_col})

    elif "trend" in skill_id or any(k in dt_cols for k in data[0].keys()):
        cols = list(data[0].keys())
        d_col = cols[0]
        v_col = cols[1] if len(cols) > 1 else cols[0]
        res = mcp_client.call("run_analysis", method="time_series_trend", data=data, params={"date_col": d_col, "value_col": v_col})

    else:
        # Default to summary statistics
        col = list(data[0].keys())[0]
        res = mcp_client.call("run_analysis", method="summary_statistics", data=data, params={"column": col})

    if res.get("status") == "error" or res.get("error"):
        state.status = "failed"
        state.error = res.get("error", "SDK analysis execution failed")
        return state

    state.sdk_output = res

    # Section 25: If this was a newly approved dynamic skill, save it as v1
    if not state.skill_found and state.user_approved is True and state.analysis_method:
        mcp_client.call(
            "save_skill",
            skill_id=state.skill_id,
            name=state.analysis_method.get("name", "Dynamic Analysis"),
            description=state.analysis_method.get("description", state.question),
            logic=state.analysis_method.get("logic", "Approved dynamic calculation"),
            formula=state.analysis_method.get("formula"),
            code=state.generated_code,
            job_id=state.job_id
        )

    return state
