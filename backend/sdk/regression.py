"""Regression methods for the Analysis SDK."""
import math
from typing import Any, Dict, List
from .base import sdk, AnalysisResult
from .correlation import _extract_paired_columns

@sdk.register(
    name="linear_regression",
    description="Ordinary least squares simple linear regression (y = mx + b)",
    required_inputs=["x", "y"]
)
def calculate_linear_regression(data: List[Dict[str, Any]], x_col: str = None, y_col: str = None, **kwargs) -> AnalysisResult:
    if not isinstance(data, list) or len(data) == 0:
        return AnalysisResult("linear_regression", "error", None, 0, error="Data must be a non-empty list of records")

    if not x_col or not y_col:
        keys = list(data[0].keys())
        if len(keys) >= 2:
            x_col = x_col or keys[0]
            y_col = y_col or keys[1]
        else:
            return AnalysisResult("linear_regression", "error", None, 0, error="At least two variables required")

    xs, ys = _extract_paired_columns(data, x_col, y_col)
    n = len(xs)
    if n < 3:
        return AnalysisResult("linear_regression", "error", None, n, error=f"Need at least 3 points, got {n}")

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    ss_yy = sum((y - mean_y) ** 2 for y in ys)

    if ss_xx == 0:
        return AnalysisResult("linear_regression", "error", None, n, error="Variance in X is zero; vertical line")

    slope = ss_xy / ss_xx
    intercept = mean_y - (slope * mean_x)

    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy) if (ss_xx * ss_yy) > 0 else 0.0

    # Residual sum of squares
    residuals = [y - (slope * x + intercept) for x, y in zip(xs, ys)]
    ss_res = sum(r ** 2 for r in residuals)
    std_err = math.sqrt(ss_res / (n - 2)) if n > 2 else 0.0

    eq = f"{y_col} = {slope:.4f} * {x_col} + {intercept:.4f}"

    return AnalysisResult(
        method="linear_regression",
        status="success",
        value={
            "slope": round(slope, 4),
            "intercept": round(intercept, 4),
            "r_squared": round(r_squared, 4),
            "std_err": round(std_err, 4),
            "equation": eq
        },
        sample_size=n,
        metric="linear_regression",
        summary=f"Linear regression equation: {eq} (R² = {r_squared:.4f}, N = {n}).",
        details={
            "x_column": x_col,
            "y_column": y_col,
            "slope": round(slope, 4),
            "intercept": round(intercept, 4),
            "r_squared": round(r_squared, 4),
            "std_err": round(std_err, 4),
            "equation": eq,
            "sample_size": n
        }
    )
