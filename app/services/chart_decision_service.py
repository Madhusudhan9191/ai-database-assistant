"""
Chart Decision Service — Phase 4 Upgrade
AI-powered automatic chart type selection.
Supports: Line, Bar, Pie, Scatter, Area
"""

from app.core.ai_client import client
import json


def get_chart_decision(question, data):

    # Empty result
    if not data:
        return {
            "show_chart": False,
            "chart_type": "none",
        }

    # Single record
    if isinstance(data, list) and len(data) == 1:
        row = data[0]
        numeric_columns = sum(
            isinstance(v, (int, float))
            for v in row.values()
        )
        if numeric_columns <= 1:
            return {
                "show_chart": False,
                "chart_type": "none",
            }

    # --- Smart heuristics (no AI call needed) ---

    if isinstance(data, list) and len(data) > 0:
        columns = [
            str(col).lower()
            for col in data[0].keys()
        ]

        time_keywords = [
            "month", "date", "year", "quarter",
            "week", "day", "period", "time",
            "created", "updated",
        ]

        has_time = any(
            any(tw in col for tw in time_keywords)
            for col in columns
        )

        row_count = len(data)

        # Time series with many points → area chart
        if has_time and row_count > 8:
            return {
                "show_chart": True,
                "chart_type": "area",
            }

        # Time series with few points → line chart
        if has_time:
            return {
                "show_chart": True,
                "chart_type": "line",
            }

        # Distribution check (few categories) → pie
        if 2 <= row_count <= 6:
            numeric_vals = []
            for row in data:
                for v in row.values():
                    if isinstance(v, (int, float)):
                        numeric_vals.append(v)
            if numeric_vals and all(
                v >= 0 for v in numeric_vals
            ):
                return {
                    "show_chart": True,
                    "chart_type": "pie",
                }

    # --- AI decision for ambiguous cases ---

    sample_data = (
        data[:10]
        if isinstance(data, list)
        else data
    )

    prompt = f"""
You are a data visualization expert.

Question: {question}

Data: {sample_data}

Which chart type best visualizes this data?

Chart Selection Rules:

LINE: Time series with few data points, trends over time
AREA: Time series with many data points, cumulative data, volume over time
BAR: Category comparisons, rankings, top-N, grouped data
PIE: Percentage/share/distribution (2-8 categories only)
SCATTER: Correlation between two numeric variables
NONE: Single value, no visual benefit

Return ONLY valid JSON:
{{"show_chart": true, "chart_type": "bar"}}

Allowed chart_type values: line, area, bar, pie, scatter, none
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        content = (
            response.choices[0]
            .message.content.strip()
        )
        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

        decision = json.loads(content)

        if (
            "show_chart" in decision
            and "chart_type" in decision
        ):
            return _validate_and_sanitize_chart(decision, data)

    except Exception:
        pass

    # Fallback
    return _validate_and_sanitize_chart({
        "show_chart": True,
        "chart_type": "bar",
    }, data)


def _validate_and_sanitize_chart(decision, data):
    """Validate and correct the chart type based on the actual shape of the returned data."""

    if not data or not isinstance(data, list):
        return {"show_chart": False, "chart_type": "none"}

    row_count = len(data)
    if row_count == 0:
        return {"show_chart": False, "chart_type": "none"}

    first_row = data[0]
    keys = list(first_row.keys())

    # 1. Identify numeric columns
    numeric_cols = []
    for k in keys:
        # Check if the column is numeric in at least one row
        is_num = False
        for r in data[:10]:
            val = r.get(k)
            if val is not None:
                try:
                    float(val)
                    is_num = True
                    break
                except (ValueError, TypeError):
                    pass
        if is_num:
            numeric_cols.append(k)

    # 2. Identify time columns
    time_keywords = [
        "month", "date", "year", "quarter", "week", "day", 
        "period", "time", "created", "updated"
    ]
    time_cols = [
        k for k in keys 
        if any(tw in k.lower() for tw in time_keywords)
    ]

    has_time = len(time_cols) > 0
    num_numeric = len(numeric_cols)

    # Rule 1: No numeric data to chart -> none
    if num_numeric == 0:
        return {"show_chart": False, "chart_type": "none"}

    # Rule 2: Single record with 1 value -> none
    if row_count == 1 and num_numeric <= 1:
        return {"show_chart": False, "chart_type": "none"}

    # Get requested chart type
    chart_type = decision.get("chart_type", "bar").lower()

    # Rule 3: Demote pie chart if categories are out of 2-8 bounds
    if chart_type == "pie":
        if row_count > 8 or row_count < 2:
            chart_type = "bar"

    # Rule 4: Demote scatter chart if fewer than 2 numeric columns
    if chart_type == "scatter":
        if num_numeric < 2:
            chart_type = "bar"

    # Rule 5: Line and Area require temporal trend data
    if chart_type in ["line", "area"]:
        if not has_time:
            chart_type = "bar"
        else:
            # Volume threshold: Area for > 8 points, Line for <= 8 points
            chart_type = "area" if row_count > 8 else "line"

    if chart_type not in ["line", "area", "bar", "pie", "scatter"]:
        return {"show_chart": False, "chart_type": "none"}

    return {
        "show_chart": True,
        "chart_type": chart_type
    }