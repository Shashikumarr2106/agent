"""Chart MCP Tools generating interactive chart specifications."""
from typing import Any, Dict, List, Optional
from ..services.chart_service import chart_service
from ..sdk.base import AnalysisResult

def generate_chart(
    method: str,
    sdk_result_dict: Dict[str, Any],
    question: str = "",
    dataset_data: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate a visual chart specification from analysis calculation results."""
    sdk_res = AnalysisResult(
        method=sdk_result_dict.get("method", method),
        status=sdk_result_dict.get("status", "success"),
        value=sdk_result_dict.get("value"),
        sample_size=sdk_result_dict.get("sample_size", 0),
        metric=sdk_result_dict.get("metric"),
        summary=sdk_result_dict.get("summary"),
        details=sdk_result_dict.get("details")
    )
    spec = chart_service.generate_chart_spec(method, sdk_res, question, dataset_data)
    if spec:
        return {"status": "success", "chart_spec": spec}
    return {"status": "none", "chart_spec": None, "message": "No chart visual applicable for this result shape"}
