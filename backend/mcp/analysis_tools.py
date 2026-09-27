"""Analysis MCP Tools providing deterministic calculation and sandbox execution."""
from typing import Any, Dict, List, Optional
from ..sdk import sdk, execute_sandboxed_code

def run_analysis(method: str, data: Any, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute a deterministic mathematical analysis using the Analysis SDK."""
    params = params or {}
    if sdk.has_method(method):
        result = sdk.run(method, data, **params)
        return result.to_dict()
    else:
        return {
            "method": method,
            "status": "error",
            "value": None,
            "error": f"Method '{method}' is not in Analysis SDK. Available methods: {[m['name'] for m in sdk.list_methods()]}"
        }

def execute_custom_analysis(code: str, data: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute user-approved sandboxed Python code for dynamic skills."""
    res = execute_sandboxed_code(code, data, context)
    return res.to_dict()

def list_sdk_methods() -> List[Dict[str, Any]]:
    """List all available mathematical and statistical methods built into the SDK."""
    return sdk.list_methods()
