"""Skill resolution and dynamic method generation node for LangGraph workflow."""
import uuid
import re
from typing import Any, Dict, List
from .state import AnalysisState
from ..mcp import mcp_client

def skill_resolution_node(state: AnalysisState) -> AnalysisState:
    """Searches pgvector for existing skill; if not found, generates a new method requiring approval."""
    if not state.is_relevant:
        return state

    question = state.question
    plan = state.analysis_plan or {}
    analysis_type = plan.get("analysis_type", "")
    schema = state.dataset_schema or {}
    dataset_cols = set(c["name"].lower() for c in schema.get("columns", []))
    q_words = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', question) if w.lower() not in dataset_cols]
    pure_query = " ".join(q_words) + f" {analysis_type}" if q_words else f"{question} {analysis_type}"

    # 1. Search skill via MCP
    search_res = mcp_client.call("search_skills", query=pure_query, threshold=0.55)

    if search_res.get("found") and search_res.get("matches"):
        top_match = search_res["matches"][0]
        state.skill_found = True
        state.skill_id = top_match["skill_id"]
        state.skill_version = top_match["version"]

        sk_ver = top_match["skill_version"]
        state.analysis_method = {
            "skill_id": sk_ver["skill_id"],
            "version": sk_ver["version"],
            "name": sk_ver["name"],
            "formula": sk_ver.get("formula"),
            "logic": sk_ver["logic"],
            "code": sk_ver.get("code"),
            "required_inputs": sk_ver.get("required_inputs", []),
            "validation_rules": sk_ver.get("validation_rules", [])
        }
        state.requires_approval = False  # Pre-existing validated skills proceed directly
    else:
        # Section 23: Skill NOT Found -> Generate Method & Require Human Approval
        state.skill_found = False
        new_skill_id = f"custom_skill_{uuid.uuid4().hex[:6]}"

        num_cols = schema.get("numeric_columns", [])
        cat_cols = schema.get("categorical_columns", [])

        # Match columns mentioned in question
        mentioned_num = [c for c in num_cols if c.lower() in question.lower()]
        target_num = mentioned_num if mentioned_num else num_cols[:2]

        concept_label = " ".join(q_words).title() if q_words else "Dynamic Analysis"

        generated_method = {
            "skill_id": new_skill_id,
            "version": 1,
            "name": f"Method: {concept_label}",
            "description": f"Statistical procedure for {concept_label}",
            "formula": "Dynamically formulated statistical logic based on question context",
            "required_inputs": target_num,
            "logic": f"Calculate metrics for columns: {', '.join(target_num)} to answer '{question}'",
            "code": f"result = sdk.run('summary_statistics', data, column='{target_num[0]}')",
            "validation_rules": ["Non-empty data", "Output within statistical bounds"]
        }

        state.skill_id = new_skill_id
        state.skill_version = 1
        state.analysis_method = generated_method
        state.generated_code = generated_method["code"]

        # If user has not yet approved, flag for human approval
        if state.user_approved is None:
            state.requires_approval = True
            state.status = "awaiting_approval"
        else:
            state.requires_approval = False

    return state
