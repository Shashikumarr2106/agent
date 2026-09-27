"""Chart specification and Markdown synthesis node for LangGraph workflow."""
import json
from .state import AnalysisState
from ..mcp import mcp_client

def chart_generation_node(state: AnalysisState) -> AnalysisState:
    """Generates visual chart specification via MCP and formats comprehensive Markdown report."""
    if not state.is_relevant or state.status == "awaiting_approval" or state.status == "failed":
        return state

    sdk_out = state.sdk_output or {}
    method = sdk_out.get("method", "")
    data = state.retrieved_data or []

    # 1. Generate chart spec via MCP
    chart_res = mcp_client.call(
        "generate_chart",
        method=method,
        sdk_result_dict=sdk_out,
        question=state.question,
        dataset_data=data
    )

    chart_spec = chart_res.get("chart_spec") if chart_res.get("status") == "success" else None
    state.chart_spec = chart_spec

    # 2. Synthesize Markdown response (Section 30 & 35)
    summary_text = sdk_out.get("summary", "Analysis completed successfully.")
    method_name = method.replace("_", " ").title()

    md_lines = [
        f"## {method_name} Results\n",
        f"**Question Analyzed:** *\"{state.question}\"*\n",
        f"### Executive Summary\n{summary_text}\n"
    ]

    # Embed Chart placeholder if chart available
    if chart_spec:
        chart_id = chart_spec.get("id", "chart_001")
        md_lines.append(f"{{{{chart:{chart_id}}}}}\n")

    # Include Data Table
    details = sdk_out.get("details", {})
    if method == "group_aggregation" and "results" in details:
        results = details["results"][:10]
        grp_col = details.get("group_column", "Category")
        val_col = details.get("value_column", "Metric")
        md_lines.append(f"### Detailed Breakdown\n")
        md_lines.append(f"| {grp_col.title()} | {val_col.title()} | Share % |")
        md_lines.append(f"|---|---:|---:|")
        for r in results:
            md_lines.append(f"| {r.get(grp_col)} | {r.get('metric')} | {r.get('share_pct', 'N/A')}% |")
        md_lines.append("\n")

    elif method == "summary_statistics" and isinstance(sdk_out.get("value"), dict):
        stats = sdk_out["value"]
        md_lines.append(f"### Statistical Measures\n")
        md_lines.append(f"| Metric | Value |")
        md_lines.append(f"|---|---:|")
        for k, v in stats.items():
            md_lines.append(f"| {k.replace('_', ' ').title()} | {v} |")
        md_lines.append("\n")

    # Skill provenance
    if state.skill_found:
        md_lines.append(f"> ℹ️ *Calculated deterministically using reusable skill `{state.skill_id}` (v{state.skill_version}) via Analysis SDK.*")
    else:
        md_lines.append(f"> ℹ️ *Executed via dynamically generated and user-approved logic.*")

    state.markdown = "\n".join(md_lines)
    state.status = "completed"
    return state
