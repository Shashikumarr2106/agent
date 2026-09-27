"""Validation node checking calculation integrity."""
from .state import AnalysisState

def validation_node(state: AnalysisState) -> AnalysisState:
    """Validates SDK numerical outputs against statistical sanity rules."""
    if not state.is_relevant or state.status == "awaiting_approval" or state.status == "failed":
        return state

    sdk_out = state.sdk_output or {}
    val = sdk_out.get("value")
    sample_size = sdk_out.get("sample_size", 0)
    method = sdk_out.get("method", "")

    validation_checks = []

    # Rule 1: Sample size check
    if sample_size <= 0:
        state.status = "failed"
        state.error = "Validation failed: Zero valid data points processed."
        return state
    validation_checks.append(f"Sample size validation passed (N={sample_size})")

    # Rule 2: Metric-specific bounds check
    if method == "pearson_correlation":
        if isinstance(val, (int, float)):
            if -1.0 <= val <= 1.0:
                validation_checks.append("Pearson correlation bounded within [-1.0, 1.0]")
            else:
                state.status = "failed"
                state.error = f"Validation failed: Pearson r ({val}) out of statistical bounds [-1.0, 1.0]"
                return state

    elif method == "coefficient_of_variation":
        if isinstance(val, (int, float)):
            if val >= 0:
                validation_checks.append("Coefficient of Variation is non-negative")
            else:
                validation_checks.append("Negative CV detected due to negative mean")

    state.validation_result = {
        "status": "valid",
        "passed_checks": validation_checks
    }
    return state
