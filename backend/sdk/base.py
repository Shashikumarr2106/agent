"""Base module for the Analysis SDK."""
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class AnalysisResult:
    """Standardized output structure for deterministic SDK computations."""
    method: str
    status: str  # "success" | "error"
    value: Any
    sample_size: int
    metric: Optional[str] = None
    summary: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class AnalysisSDKRegistry:
    """Registry for deterministic statistical and mathematical calculation methods."""

    def __init__(self):
        self._methods: Dict[str, Callable] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str = "", required_inputs: List[str] = None):
        """Decorator to register an analytical calculation method."""
        def decorator(func: Callable):
            self._methods[name] = func
            self._metadata[name] = {
                "name": name,
                "description": description,
                "required_inputs": required_inputs or [],
            }
            return func
        return decorator

    def run(self, method: str, data: Any, **kwargs) -> AnalysisResult:
        """Execute a registered analysis method deterministically."""
        if method not in self._methods:
            return AnalysisResult(
                method=method,
                status="error",
                value=None,
                sample_size=0,
                error=f"Method '{method}' is not registered in Analysis SDK. Available: {list(self._methods.keys())}"
            )
        try:
            func = self._methods[method]
            return func(data, **kwargs)
        except Exception as e:
            return AnalysisResult(
                method=method,
                status="error",
                value=None,
                sample_size=0,
                error=f"Execution error in '{method}': {str(e)}"
            )

    def list_methods(self) -> List[Dict[str, Any]]:
        return list(self._metadata.values())

    def has_method(self, name: str) -> bool:
        return name in self._methods

# Global singleton SDK instance
sdk = AnalysisSDKRegistry()
