"""Aggregation and trend analysis methods for the Analysis SDK."""
from typing import Any, Dict, List
from collections import defaultdict
from .base import sdk, AnalysisResult

@sdk.register(
    name="group_aggregation",
    description="Calculate aggregated metrics (sum, avg, count, min, max) grouped by a categorical dimension",
    required_inputs=["group_by", "metric_column"]
)
def calculate_group_aggregation(
    data: List[Dict[str, Any]],
    group_col: str = None,
    value_col: str = None,
    agg_func: str = "avg",
    **kwargs
) -> AnalysisResult:
    if not isinstance(data, list) or len(data) == 0:
        return AnalysisResult("group_aggregation", "error", None, 0, error="Data must be a non-empty list of records")

    # If already aggregated (e.g. from SQL GROUP BY query), parse directly
    if not group_col or not value_col:
        cols = list(data[0].keys())
        if len(cols) >= 2:
            group_col = group_col or cols[0]
            value_col = value_col or cols[1]
        else:
            return AnalysisResult("group_aggregation", "error", None, 0, error="Need group column and value column")

    buckets = defaultdict(list)
    for row in data:
        grp = row.get(group_col)
        val = row.get(value_col)
        if grp is not None and val is not None:
            try:
                buckets[str(grp)].append(float(val))
            except (ValueError, TypeError):
                continue

    results = []
    total_val = 0.0
    for grp, vals in buckets.items():
        if not vals:
            continue
        cnt = len(vals)
        total = sum(vals)
        avg = total / cnt
        maximum = max(vals)
        minimum = min(vals)

        if agg_func == "sum":
            computed = total
        elif agg_func == "count":
            computed = cnt
        elif agg_func == "max":
            computed = maximum
        elif agg_func == "min":
            computed = minimum
        else:
            computed = avg

        total_val += computed
        results.append({
            group_col: grp,
            "metric": round(computed, 4),
            "count": cnt,
            "sum": round(total, 4),
            "avg": round(avg, 4),
            "min": round(minimum, 4),
            "max": round(maximum, 4)
        })

    # Sort descending by metric
    results.sort(key=lambda x: x["metric"], reverse=True)

    # Calculate share / percentage of total
    if total_val > 0:
        for r in results:
            r["share_pct"] = round((r["metric"] / total_val) * 100.0, 2)

    top_item = results[0][group_col] if results else "None"
    top_val = results[0]["metric"] if results else 0

    return AnalysisResult(
        method="group_aggregation",
        status="success",
        value=results,
        sample_size=len(data),
        metric=f"{agg_func}_{value_col}_by_{group_col}",
        summary=f"Group aggregation of '{value_col}' by '{group_col}' ({agg_func}). Top category is '{top_item}' with value {top_val}.",
        details={
            "group_column": group_col,
            "value_column": value_col,
            "agg_func": agg_func,
            "category_count": len(results),
            "results": results
        }
    )

@sdk.register(
    name="time_series_trend",
    description="Analyze temporal trend across dates or periods, including growth rate and change",
    required_inputs=["date_col", "value_col"]
)
def calculate_trend(
    data: List[Dict[str, Any]],
    date_col: str = None,
    value_col: str = None,
    **kwargs
) -> AnalysisResult:
    if not isinstance(data, list) or len(data) < 2:
        return AnalysisResult("time_series_trend", "error", None, len(data) if isinstance(data, list) else 0, error="Need at least 2 points for trend")

    if not date_col or not value_col:
        cols = list(data[0].keys())
        date_col = date_col or cols[0]
        value_col = value_col or cols[1]

    parsed = []
    for row in data:
        d = row.get(date_col)
        v = row.get(value_col)
        if d is not None and v is not None:
            try:
                parsed.append({"period": str(d), "value": float(v)})
            except (ValueError, TypeError):
                continue

    if len(parsed) < 2:
        return AnalysisResult("time_series_trend", "error", None, len(parsed), error="Insufficient valid numerical records")

    first_val = parsed[0]["value"]
    last_val = parsed[-1]["value"]
    overall_change = last_val - first_val
    growth_rate = ((last_val - first_val) / abs(first_val) * 100.0) if first_val != 0 else 0.0

    trend_direction = "increasing" if overall_change > 0 else "decreasing" if overall_change < 0 else "flat"

    return AnalysisResult(
        method="time_series_trend",
        status="success",
        value={
            "series": parsed,
            "overall_change": round(overall_change, 4),
            "growth_rate_pct": round(growth_rate, 2),
            "trend_direction": trend_direction
        },
        sample_size=len(parsed),
        metric="time_series_trend",
        summary=f"Trend across {len(parsed)} periods is {trend_direction} with an overall growth of {growth_rate:.2f}%.",
        details={
            "date_column": date_col,
            "value_column": value_col,
            "direction": trend_direction,
            "growth_pct": round(growth_rate, 2),
            "points": len(parsed)
        }
    )
