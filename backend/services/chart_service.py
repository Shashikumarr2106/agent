"""Chart Specification Generator Service."""
import uuid
from typing import Any, Dict, List, Optional
from ..sdk.base import AnalysisResult

class ChartService:
    def generate_chart_spec(
        self,
        method: str,
        sdk_result: AnalysisResult,
        question: str = "",
        dataset_data: List[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Generates a standardized chart specification JSON matching Section 28 & 29."""
        chart_id = f"chart_{uuid.uuid4().hex[:6]}"

        if method == "pearson_correlation" or method == "linear_regression":
            # Scatter Plot with regression line
            details = sdk_result.details or {}
            x_col = details.get("x_column", "x")
            y_col = details.get("y_column", "y")
            data_points = []
            if dataset_data:
                for row in dataset_data[:150]:
                    vx = row.get(x_col)
                    vy = row.get(y_col)
                    if vx is not None and vy is not None:
                        try:
                            data_points.append({"x": float(vx), "y": float(vy)})
                        except (ValueError, TypeError):
                            pass

            return {
                "id": chart_id,
                "type": "scatter",
                "title": f"Correlation: {x_col} vs {y_col}",
                "xAxis": {"label": x_col, "type": "number"},
                "yAxis": {"label": y_col, "type": "number"},
                "data": data_points,
                "series": [
                    {
                        "name": f"{x_col} vs {y_col}",
                        "data": data_points
                    }
                ],
                "metadata": {
                    "r": details.get("r"),
                    "r_squared": details.get("r_squared"),
                    "equation": details.get("equation")
                }
            }

        elif method == "group_aggregation":
            # Bar Chart or Pie Chart
            details = sdk_result.details or {}
            grp_col = details.get("group_column", "category")
            val_col = details.get("value_column", "value")
            results = details.get("results", [])

            categories = [r.get(grp_col, "") for r in results]
            values = [r.get("metric", 0) for r in results]

            chart_type = "pie" if len(categories) <= 5 and "share" in question.lower() else "bar"

            return {
                "id": chart_id,
                "type": chart_type,
                "title": f"{val_col.replace('_', ' ').title()} by {grp_col.replace('_', ' ').title()}",
                "xAxis": {"label": grp_col, "categories": categories},
                "yAxis": {"label": val_col, "type": "number"},
                "data": results,
                "series": [
                    {
                        "name": val_col,
                        "data": values
                    }
                ]
            }

        elif method == "time_series_trend":
            # Line Chart
            val_obj = sdk_result.value or {}
            series_data = val_obj.get("series", [])
            categories = [s.get("period", "") for s in series_data]
            values = [s.get("value", 0) for s in series_data]
            details = sdk_result.details or {}
            val_col = details.get("value_column", "value")

            return {
                "id": chart_id,
                "type": "line",
                "title": f"Trend Analysis: {val_col.replace('_', ' ').title()} Over Time",
                "xAxis": {"label": details.get("date_column", "Period"), "categories": categories},
                "yAxis": {"label": val_col, "type": "number"},
                "data": series_data,
                "series": [
                    {
                        "name": val_col,
                        "data": values
                    }
                ]
            }

        elif method == "summary_statistics" or method == "coefficient_of_variation":
            # Bar chart of key descriptive statistics
            stats = sdk_result.details or {}
            metrics = ["min", "q25", "median", "mean", "q75", "max"]
            available = [m for m in metrics if m in stats and stats[m] is not None]
            categories = [m.upper() for m in available]
            values = [stats[m] for m in available]

            return {
                "id": chart_id,
                "type": "bar",
                "title": f"Distribution Summary ({sdk_result.metric})",
                "xAxis": {"label": "Statistic", "categories": categories},
                "yAxis": {"label": "Value", "type": "number"},
                "data": [{"metric": c, "value": v} for c, v in zip(categories, values)],
                "series": [
                    {
                        "name": "Value",
                        "data": values
                    }
                ]
            }

        return None

chart_service = ChartService()
