"""Statistical methods for the Analysis SDK."""
import math
from typing import Any, Dict, List, Union
from .base import sdk, AnalysisResult

def _extract_numeric_list(data: Any, column: str = None) -> List[float]:
    """Helper to extract a clean list of floats from dicts, lists, or column records."""
    if isinstance(data, list):
        if not data:
            return []
        if isinstance(data[0], dict):
            if not column:
                # pick first numeric key
                for k, v in data[0].items():
                    if isinstance(v, (int, float)):
                        column = k
                        break
            if not column:
                column = list(data[0].keys())[0]
            values = []
            for row in data:
                val = row.get(column)
                if val is not None:
                    try:
                        values.append(float(val))
                    except (ValueError, TypeError):
                        pass
            return values
        else:
            # direct list of numbers
            values = []
            for item in data:
                if item is not None:
                    try:
                        values.append(float(item))
                    except (ValueError, TypeError):
                        pass
            return values
    return []

@sdk.register(
    name="mean",
    description="Calculate arithmetic mean of a numeric variable",
    required_inputs=["values"]
)
def calculate_mean(data: Any, column: str = None, **kwargs) -> AnalysisResult:
    vals = _extract_numeric_list(data, column)
    if not vals:
        return AnalysisResult("mean", "error", None, 0, error="No valid numeric data provided")
    avg = sum(vals) / len(vals)
    return AnalysisResult(
        method="mean",
        status="success",
        value=round(avg, 4),
        sample_size=len(vals),
        metric="mean",
        summary=f"Calculated mean is {avg:.4f} across {len(vals)} data points."
    )

@sdk.register(
    name="standard_deviation",
    description="Calculate standard deviation (sample or population)",
    required_inputs=["values"]
)
def calculate_std(data: Any, column: str = None, ddof: int = 1, **kwargs) -> AnalysisResult:
    vals = _extract_numeric_list(data, column)
    n = len(vals)
    if n <= ddof:
        return AnalysisResult("standard_deviation", "error", None, n, error=f"Need at least {ddof + 1} values for standard deviation")
    avg = sum(vals) / n
    variance = sum((x - avg) ** 2 for x in vals) / (n - ddof)
    std = math.sqrt(variance)
    return AnalysisResult(
        method="standard_deviation",
        status="success",
        value=round(std, 4),
        sample_size=n,
        metric="standard_deviation",
        summary=f"Standard deviation ({'sample' if ddof==1 else 'population'}) is {std:.4f} (N={n}).",
        details={"variance": round(variance, 4), "mean": round(avg, 4), "ddof": ddof}
    )

@sdk.register(
    name="coefficient_of_variation",
    description="Calculate Coefficient of Variation: CV = (std / mean) * 100",
    required_inputs=["values"]
)
def calculate_cv(data: Any, column: str = None, ddof: int = 1, **kwargs) -> AnalysisResult:
    vals = _extract_numeric_list(data, column)
    n = len(vals)
    if n <= ddof:
        return AnalysisResult("coefficient_of_variation", "error", None, n, error=f"Need at least {ddof + 1} values")
    avg = sum(vals) / n
    if avg == 0:
        return AnalysisResult("coefficient_of_variation", "error", None, n, error="Mean is zero; CV is undefined")
    variance = sum((x - avg) ** 2 for x in vals) / (n - ddof)
    std = math.sqrt(variance)
    cv = (std / avg) * 100.0
    return AnalysisResult(
        method="coefficient_of_variation",
        status="success",
        value=round(cv, 4),
        sample_size=n,
        metric="coefficient_of_variation_pct",
        summary=f"Coefficient of Variation is {cv:.2f}% (std={std:.4f}, mean={avg:.4f}, N={n}).",
        details={"std": round(std, 4), "mean": round(avg, 4), "cv_percentage": round(cv, 2)}
    )

@sdk.register(
    name="summary_statistics",
    description="Calculate comprehensive descriptive statistics (mean, median, std, min, max, quartiles)",
    required_inputs=["values"]
)
def calculate_summary(data: Any, column: str = None, **kwargs) -> AnalysisResult:
    vals = _extract_numeric_list(data, column)
    n = len(vals)
    if not vals:
        return AnalysisResult("summary_statistics", "error", None, 0, error="No valid numeric data")
    sorted_vals = sorted(vals)
    avg = sum(vals) / n
    variance = sum((x - avg) ** 2 for x in vals) / (n - 1) if n > 1 else 0.0
    std = math.sqrt(variance)

    # Median & Quartiles
    def percentile(p):
        k = (len(sorted_vals) - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_vals[int(k)]
        return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)

    p25 = percentile(0.25)
    median = percentile(0.50)
    p75 = percentile(0.75)
    iqr = p75 - p25

    stats = {
        "count": n,
        "mean": round(avg, 4),
        "std": round(std, 4),
        "min": round(sorted_vals[0], 4),
        "q25": round(p25, 4),
        "median": round(median, 4),
        "q75": round(p75, 4),
        "max": round(sorted_vals[-1], 4),
        "iqr": round(iqr, 4),
        "cv_pct": round((std / avg) * 100.0, 2) if avg != 0 else None
    }

    return AnalysisResult(
        method="summary_statistics",
        status="success",
        value=stats,
        sample_size=n,
        metric="descriptive_statistics",
        summary=f"Summary for {n} records: Mean={stats['mean']}, Median={stats['median']}, Std={stats['std']}, Min={stats['min']}, Max={stats['max']}.",
        details=stats
    )
