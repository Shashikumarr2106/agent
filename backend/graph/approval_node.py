"""Human approval breakpoint node for LangGraph workflow."""
from .state import AnalysisState

def human_approval_node(state: AnalysisState) -> AnalysisState:
    """Handles human approval gating before executing newly generated or modified methods."""
    if not state.requires_approval:
        return state

    if state.user_approved is True:
        state.requires_approval = False
        state.status = "executing"
        return state
    elif state.user_approved is False:
        # User rejected or requested modifications
        if state.approval_comment:
            method = state.analysis_method or {}
            method["logic"] = f"{method.get('logic', '')} (Modified per feedback: {state.approval_comment})"
            state.analysis_method = method
            state.status = "awaiting_approval"
        else:
            state.status = "rejected"
            state.error = "Analysis method was rejected by the user."
        return state
    else:
        # Paused awaiting user decision via /analysis/approve or /analysis/reject
        state.status = "awaiting_approval"
        return state
