"""Correlation methods for the Analysis SDK."""
import math
from typing import Any, Dict, List, Tuple
from .base import sdk, AnalysisResult

def _extract_paired_columns(data: List[Dict[str, Any]], col_x: str, col_y: str) -> Tuple[List[float], List[float]]:
    """Extract and validate matching pairs of numeric values."""
    xs, ys = [], []
    for row in data:
        vx = row.get(col_x)
        vy = row.get(col_y)
        if vx is not None and vy is not None:
            try:
                fx = float(vx)
                fy = float(vy)
                xs.append(fx)
                ys.append(fy)
            except (ValueError, TypeError):
                continue
    return xs, ys

@sdk.register(
    name="pearson_correlation",
    description="Calculate Pearson product-moment correlation coefficient between two numeric variables",
    required_inputs=["x", "y"]
)
def calculate_pearson(data: List[Dict[str, Any]], x_col: str = None, y_col: str = None, **kwargs) -> AnalysisResult:
    if not isinstance(data, list) or len(data) == 0:
        return AnalysisResult("pearson_correlation", "error", None, 0, error="Data must be a non-empty list of records")

    # If columns not specified, attempt to infer first two numeric keys
    if not x_col or not y_col:
        keys = list(data[0].keys())
        numeric_keys = [k for k in keys if isinstance(data[0].get(k), (int, float))]
        if len(numeric_keys) >= 2:
            x_col = x_col or numeric_keys[0]
            y_col = y_col or numeric_keys[1]
        elif len(keys) >= 2:
            x_col = x_col or keys[0]
            y_col = y_col or keys[1]
        else:
            return AnalysisResult("pearson_correlation", "error", None, 0, error="At least two variables are required for correlation")

    xs, ys = _extract_paired_columns(data, x_col, y_col)
    n = len(xs)
    if n < 3:
        return AnalysisResult("pearson_correlation", "error", None, n, error=f"Need at least 3 paired values for correlation, got {n}")

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)

    denom = math.sqrt(var_x * var_y)
    if denom == 0:
        return AnalysisResult("pearson_correlation", "error", None, n, error="Standard deviation of one or both variables is zero")

    r = cov / denom
    r = max(-1.0, min(1.0, r))  # clamp precision bounds

    # Interpret correlation
    abs_r = abs(r)
    strength = "very strong" if abs_r >= 0.8 else "strong" if abs_r >= 0.6 else "moderate" if abs_r >= 0.4 else "weak" if abs_r >= 0.2 else "negligible"
    direction = "positive" if r > 0 else "negative" if r < 0 else "zero"

    return AnalysisResult(
        method="pearson_correlation",
        status="success",
        value=round(r, 4),
        sample_size=n,
        metric="pearson_r",
        summary=f"Pearson correlation between '{x_col}' and '{y_col}' is {r:.4f} ({strength} {direction} correlation, N={n}).",
        details={
            "x_column": x_col,
            "y_column": y_col,
            "r": round(r, 4),
            "r_squared": round(r ** 2, 4),
            "strength": strength,
            "direction": direction,
            "mean_x": round(mean_x, 4),
            "mean_y": round(mean_y, 4),
            "sample_size": n
        }
    )

@sdk.register(
    name="spearman_correlation",
    description="Calculate Spearman rank-order correlation coefficient",
    required_inputs=["x", "y"]
)
def calculate_spearman(data: List[Dict[str, Any]], x_col: str = None, y_col: str = None, **kwargs) -> AnalysisResult:
    xs, ys = _extract_paired_columns(data, x_col, y_col)
    n = len(xs)
    if n < 3:
        return AnalysisResult("spearman_correlation", "error", None, n, error="Need at least 3 paired values")

    def rank(arr):
        sorted_indices = sorted(range(len(arr)), key=lambda k: arr[k])
        ranks = [0.0] * len(arr)
        i = 0
        while i < len(arr):
            j = i
            while j + 1 < len(arr) and arr[sorted_indices[j + 1]] == arr[sorted_indices[i]]:
                j += 1
            avg_rank = (i + j + 2) / 2.0
            for k in range(i, j + 1):
                ranks[sorted_indices[k]] = avg_rank
            i = j + 1
        return ranks

    rank_x = rank(xs)
    rank_y = rank(ys)

    # Pearson of ranks
    mean_rx = sum(rank_x) / n
    mean_ry = sum(rank_y) / n
    cov = sum((rx - mean_rx) * (ry - mean_ry) for rx, ry in zip(rank_x, rank_y))
    denom = math.sqrt(sum((rx - mean_rx) ** 2 for rx in rank_x) * sum((ry - mean_ry) ** 2 for ry in rank_y))

    rho = cov / denom if denom > 0 else 0.0

    return AnalysisResult(
        method="spearman_correlation",
        status="success",
        value=round(rho, 4),
        sample_size=n,
        metric="spearman_rho",
        summary=f"Spearman rank correlation is {rho:.4f} (N={n}).",
        details={"rho": round(rho, 4), "sample_size": n}
    )
