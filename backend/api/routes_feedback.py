"""User feedback and skill versioning API endpoints."""
import json
from typing import Any, Dict
from .routes_analysis import _load_job_as_state
from ..services.skill_service import skill_service
from ..mcp import mcp_client
from ..graph.graph import workflow_engine

def handle_feedback(job_id: str, feedback: str) -> Dict[str, Any]:
    """Section 27: Processes user feedback ('Result is wrong'), creates skill v2, re-runs."""
    state = _load_job_as_state(job_id)
    if not state:
        return {"error": f"Job '{job_id}' not found"}

    if not state.skill_id:
        return {"error": "No skill associated with this job to revise."}

    # Understand and validate correction
    fb_low = feedback.lower()
    modifications = {}

    if "population" in fb_low and ("standard deviation" in fb_low or "std" in fb_low or "cv" in fb_low):
        modifications["logic"] = "Use population standard deviation (ddof=0) instead of sample standard deviation."
        modifications["formula"] = "CV = (std_pop / mean) * 100"
    elif "spearman" in fb_low:
        modifications["name"] = "Spearman Rank Correlation Analysis"
        modifications["logic"] = "Use non-parametric Spearman rank-order correlation."
        modifications["formula"] = "rho = 1 - (6 * Σ d² / (n(n² - 1)))"
    elif "median" in fb_low:
        modifications["logic"] = "Use median instead of mean for central tendency."
    else:
        modifications["logic"] = f"Adjusted calculation according to feedback: '{feedback}'"

    # Create new skill version (Section 26 & 27)
    try:
        new_version = skill_service.update_skill_version(
            skill_id=state.skill_id,
            modifications=modifications,
            feedback=feedback
        )
    except Exception as e:
        return {"error": f"Failed to create new skill version: {str(e)}"}

    # Re-run analysis with new skill version
    state.skill_version = new_version.version
    state.user_feedback = feedback
    state.analysis_method = new_version.model_dump()
    state.status = "executing"

    resulting_state = workflow_engine.run(state)

    return {
        "job_id": resulting_state.job_id,
        "status": resulting_state.status,
        "revised_skill": {
            "skill_id": new_version.skill_id,
            "version": new_version.version,
            "logic": new_version.logic
        },
        "markdown": resulting_state.markdown,
        "chart": resulting_state.chart_spec,
        "sdk_output": resulting_state.sdk_output
    }
