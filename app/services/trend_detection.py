"""
Trend Detection Service
Programmatically analyzes query result data to detect:
- Growth / Decline patterns
- Anomalies and outliers
- Concentration risks
- Data distribution patterns
"""

import statistics


def detect_trends(data):
    """Analyze query results and return a dict of detected patterns."""

    if not data or not isinstance(data, list):
        return {"summary": "No data to analyze."}

    findings = {
        "row_count": len(data),
        "numeric_trends": [],
        "outliers": [],
        "patterns": [],
        "distribution": [],
    }

    keys = list(data[0].keys()) if data else []

    # Identify numeric columns
    numeric_cols = []
    for key in keys:
        values = [
            row[key] for row in data
            if row.get(key) is not None
            and _is_numeric(row[key])
        ]
        if len(values) >= 2:
            numeric_cols.append((key, values))

    for col_name, values in numeric_cols:
        nums = [float(v) for v in values]
        analysis = _analyze_numeric(col_name, nums)
        findings["numeric_trends"].append(analysis)

        # Detect outliers
        outliers = _detect_outliers(col_name, nums)
        if outliers:
            findings["outliers"].extend(outliers)

    # Detect concentration risk
    for col_name, values in numeric_cols:
        nums = [float(v) for v in values]
        concentration = _detect_concentration(
            col_name, nums
        )
        if concentration:
            findings["patterns"].append(concentration)

    # Detect time-based trends
    time_cols = _find_time_columns(keys, data)
    if time_cols and numeric_cols:
        for col_name, values in numeric_cols:
            nums = [float(v) for v in values]
            trend = _detect_time_trend(
                col_name, nums
            )
            if trend:
                findings["numeric_trends"].append(trend)

    return findings


def format_trends_for_prompt(findings):
    """Format detected trends as a string for the AI prompt."""

    if not findings or findings.get("summary"):
        return findings.get("summary", "")

    parts = []

    if findings.get("numeric_trends"):
        parts.append("DETECTED PATTERNS:")
        for trend in findings["numeric_trends"]:
            parts.append(f"  - {trend}")

    if findings.get("outliers"):
        parts.append("OUTLIERS DETECTED:")
        for outlier in findings["outliers"]:
            parts.append(f"  - {outlier}")

    if findings.get("patterns"):
        parts.append("RISK PATTERNS:")
        for pattern in findings["patterns"]:
            parts.append(f"  - {pattern}")

    return "\n".join(parts) if parts else ""


def _is_numeric(value):
    """Check if a value is numeric."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _analyze_numeric(col_name, nums):
    """Analyze a numeric column for basic statistics."""

    total = sum(nums)
    avg = statistics.mean(nums)
    min_val = min(nums)
    max_val = max(nums)

    if len(nums) >= 2:
        stdev = statistics.stdev(nums)
        spread = (
            (max_val - min_val) / avg * 100
            if avg != 0 else 0
        )
    else:
        stdev = 0
        spread = 0

    # Detect if values are growing or declining
    direction = ""
    if len(nums) >= 3:
        first_half = statistics.mean(
            nums[: len(nums) // 2]
        )
        second_half = statistics.mean(
            nums[len(nums) // 2:]
        )

        if first_half > 0:
            change_pct = (
                (second_half - first_half)
                / first_half * 100
            )

            if change_pct > 15:
                direction = (
                    f"GROWTH trend detected "
                    f"(+{change_pct:.1f}%)"
                )
            elif change_pct < -15:
                direction = (
                    f"DECLINE trend detected "
                    f"({change_pct:.1f}%)"
                )

    result = (
        f"{col_name}: "
        f"min={min_val:,.2f}, max={max_val:,.2f}, "
        f"avg={avg:,.2f}, spread={spread:.0f}%"
    )

    if direction:
        result += f" | {direction}"

    return result


def _detect_outliers(col_name, nums):
    """Detect outliers using IQR method."""

    if len(nums) < 4:
        return []

    sorted_nums = sorted(nums)
    q1 = sorted_nums[len(sorted_nums) // 4]
    q3 = sorted_nums[3 * len(sorted_nums) // 4]
    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outliers = []
    for val in nums:
        if val < lower or val > upper:
            outliers.append(
                f"{col_name}: value {val:,.2f} is an "
                f"outlier (expected range: "
                f"{lower:,.2f} to {upper:,.2f})"
            )

    return outliers[:3]  # Limit to 3 outliers


def _detect_concentration(col_name, nums):
    """Detect if top entries dominate the total."""

    if len(nums) < 3:
        return None

    total = sum(nums)
    if total == 0:
        return None

    sorted_desc = sorted(nums, reverse=True)
    top_pct = sorted_desc[0] / total * 100

    if top_pct > 50:
        return (
            f"CONCENTRATION RISK: Top entry in "
            f"{col_name} accounts for "
            f"{top_pct:.0f}% of total"
        )

    top2_pct = sum(sorted_desc[:2]) / total * 100
    if top2_pct > 70:
        return (
            f"CONCENTRATION RISK: Top 2 entries in "
            f"{col_name} account for "
            f"{top2_pct:.0f}% of total"
        )

    return None


def _find_time_columns(keys, data):
    """Identify columns that look like time/date."""

    time_keywords = [
        "date", "month", "year", "time",
        "period", "quarter", "week", "day"
    ]

    return [
        k for k in keys
        if any(
            tw in k.lower()
            for tw in time_keywords
        )
    ]


def _detect_time_trend(col_name, nums):
    """Detect monotonic increase/decrease."""

    if len(nums) < 3:
        return None

    increasing = all(
        nums[i] <= nums[i + 1]
        for i in range(len(nums) - 1)
    )
    decreasing = all(
        nums[i] >= nums[i + 1]
        for i in range(len(nums) - 1)
    )

    if increasing:
        growth = (
            (nums[-1] - nums[0]) / nums[0] * 100
            if nums[0] != 0 else 0
        )
        return (
            f"{col_name}: Consistent UPWARD trend "
            f"(+{growth:.1f}% overall)"
        )
    elif decreasing:
        decline = (
            (nums[-1] - nums[0]) / nums[0] * 100
            if nums[0] != 0 else 0
        )
        return (
            f"{col_name}: Consistent DOWNWARD trend "
            f"({decline:.1f}% overall)"
        )

    return None
