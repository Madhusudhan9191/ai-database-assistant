"""
KPI Detection Service
Automatically detects and calculates KPI metrics
from query results: totals, averages, growth rates,
counts, min/max values.
"""


def detect_kpis(data):
    """Analyze query data and return auto-detected KPIs."""

    if not data or not isinstance(data, list):
        return []

    kpis = []
    keys = list(data[0].keys())

    ignore_patterns = [
        "_id", "id", "phone", "mobile", "code", "date",
        "year", "month", "day", "latitude", "longitude",
        "zip", "zipcode"
    ]
    positive_keywords = [
        "amount", "revenue", "rent", "fee", "expense", "cost",
        "profit", "bed", "room", "capacity", "occupancy",
        "payment", "collection"
    ]

    for key in keys:
        key_lower = key.lower()

        # Check if column should be ignored (e.g. is an ID, code, phone)
        should_ignore = False
        for pattern in ignore_patterns:
            if pattern == "id":
                if key_lower == "id" or key_lower.endswith("_id"):
                    should_ignore = True
                    break
            elif pattern in key_lower:
                should_ignore = True
                break

        # Check if column contains a positive KPI keyword
        has_positive = any(kw in key_lower for kw in positive_keywords)

        if should_ignore or not has_positive:
            continue

        values = [
            row[key] for row in data
            if row.get(key) is not None
            and _is_numeric(row[key])
        ]

        if not values:
            continue

        nums = [float(v) for v in values]
        col_label = key.replace("_", " ").title()

        # Total
        total = sum(nums)
        kpis.append({
            "label": f"Total {col_label}",
            "value": _format_number(total),
            "type": "total",
        })

        # Average
        avg = total / len(nums)
        kpis.append({
            "label": f"Avg {col_label}",
            "value": _format_number(avg),
            "type": "average",
        })

        # Growth rate (if sequential data)
        if len(nums) >= 2:
            first = nums[0]
            last = nums[-1]
            if first != 0:
                growth = (
                    (last - first) / abs(first) * 100
                )
                kpis.append({
                    "label": f"{col_label} Change",
                    "value": f"{growth:+.1f}%",
                    "type": (
                        "positive" if growth >= 0
                        else "negative"
                    ),
                })

    # Limit to top 6 KPIs to keep it clean
    return kpis[:6]


def _is_numeric(value):
    """Check if a value is numeric."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _format_number(num):
    """Format large numbers for readability."""

    if abs(num) >= 1_000_000:
        return f"{num / 1_000_000:,.1f}M"
    elif abs(num) >= 1_000:
        return f"{num / 1_000:,.1f}K"
    elif num == int(num):
        return f"{int(num):,}"
    else:
        return f"{num:,.2f}"
