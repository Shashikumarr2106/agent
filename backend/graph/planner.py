"""Planning and relevance verification node for LangGraph workflow."""
import re
from typing import Any, Dict, List
from .state import AnalysisState
from ..mcp import mcp_client

def check_relevance_and_plan_node(state: AnalysisState) -> AnalysisState:
    """Inspects dataset schema, assesses relevance of question, and generates analysis plan."""
    # 1. Load schema via MCP
    if not state.dataset_schema:
        schema_res = mcp_client.call("get_dataset_schema", dataset_id=state.dataset_id)
        if schema_res.get("error"):
            state.status = "failed"
            state.error = schema_res["error"]
            return state
        state.dataset_schema = schema_res

    schema = state.dataset_schema
    all_cols = [c["name"].lower() for c in schema.get("columns", [])]
    numeric_cols = [c.lower() for c in schema.get("numeric_columns", [])]
    categorical_cols = [c.lower() for c in schema.get("categorical_columns", [])]
    datetime_cols = [c.lower() for c in schema.get("datetime_columns", [])]

    question = state.question.strip()

    # Section 14: User provides no question
    if not question:
        primary_suggestion = ""
        suggested = []
        if len(numeric_cols) >= 2:
            suggested.append(f"Correlation between {numeric_cols[0]} and {numeric_cols[1]}")
            primary_suggestion = suggested[-1]
        if numeric_cols and categorical_cols:
            suggested.append(f"Average {numeric_cols[0]} grouped by {categorical_cols[0]}")
            if not primary_suggestion:
                primary_suggestion = suggested[-1]
        if numeric_cols:
            suggested.append(f"Distribution & Summary statistics for {numeric_cols[0]}")
            suggested.append(f"Coefficient of Variation for {numeric_cols[0]}")

        state.question = primary_suggestion or f"Summary statistics for {all_cols[0]}"
        state.suggested_analyses = suggested
        question = state.question

    # Section 13: Check question relevance
    tokens = re.findall(r'\b[a-zA-Z0-9_]{3,}\b', question.lower())
    col_matches = [t for t in tokens if t in all_cols]

    # Common analytical concepts that imply relevance even if column names are mentioned in context
    analytical_keywords = {
        "correlation", "profit", "sales", "average", "avg", "mean", "median",
        "standard", "deviation", "highest", "lowest", "sum", "trend", "variation",
        "distribution", "regression", "cv", "growth", "top", "rate", "revenue"
    }
    concept_matches = [t for t in tokens if t in analytical_keywords]

    is_relevant = len(col_matches) > 0 or len(concept_matches) > 0

    # Catch blatantly irrelevant questions (e.g. weather, politics, recipes)
    irrelevant_keywords = {"weather", "tomorrow", "president", "recipe", "cook", "movie", "song"}
    if any(w in question.lower() for w in irrelevant_keywords) and len(col_matches) == 0:
        is_relevant = False

    state.is_relevant = is_relevant

    if not is_relevant:
        # Suggest 5 useful dataset analyses
        suggestions = []
        if len(numeric_cols) >= 2:
            suggestions.append(f"Calculate correlation between '{numeric_cols[0]}' and '{numeric_cols[1]}'")
        if numeric_cols and categorical_cols:
            suggestions.append(f"Compare average '{numeric_cols[0]}' across '{categorical_cols[0]}'")
        if numeric_cols and datetime_cols:
            suggestions.append(f"Analyze trend of '{numeric_cols[0]}' over time")
        if numeric_cols:
            suggestions.append(f"Compute Coefficient of Variation for '{numeric_cols[0]}'")
            suggestions.append(f"Summary descriptive statistics for '{numeric_cols[0]}'")

        state.suggested_analyses = suggestions
        state.status = "completed"
        state.markdown = (
            f"### Question Not Directly Relevant to Dataset\n\n"
            f"Your question *\"{state.question}\"* cannot be answered from the uploaded dataset (`{schema.get('filename')}`).\n\n"
            f"**Here are useful analyses you can run on this dataset:**\n"
            + "\n".join([f"- {s}" for s in suggestions])
        )
        return state

    # Create structured analysis plan
    target_metric = ""
    target_dim = ""

    q_low = question.lower()
    if "correlation" in q_low or "relationship" in q_low:
        analysis_type = "correlation"
    elif "variation" in q_low or " cv" in q_low:
        analysis_type = "coefficient_of_variation"
    elif "trend" in q_low or "growth" in q_low or "over time" in q_low:
        analysis_type = "trend"
    elif "regression" in q_low or "predict" in q_low:
        analysis_type = "regression"
    elif "summary" in q_low or "describe" in q_low or "distribution" in q_low:
        analysis_type = "summary"
    elif any(k in q_low for k in ("by ", "group", "average", "avg", "sum", "total", "highest", "lowest", "max", "min")):
        analysis_type = "aggregation"
    else:
        analysis_type = "custom"

    state.analysis_plan = {
        "analysis_type": analysis_type,
        "question": question,
        "detected_columns": col_matches,
        "steps": [
            "1. Identify required columns from dataset schema",
            "2. Search skill vector database for matching methodology",
            "3. Formulate SQL query to extract required data subset",
            "4. Execute calculation through deterministic Analysis SDK",
            "5. Validate calculation results against statistical constraints",
            "6. Generate chart specification and markdown presentation"
        ]
    }
    state.status = "planning"
    return state
