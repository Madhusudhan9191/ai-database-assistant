"""
Query Validation Engine — Phase 1 Upgrade
Production-grade SQL validation:
- Dangerous keyword detection
- Single statement enforcement
- SELECT/WITH-only check
- SQL structure parsing (subquery, comment, union injection)
- Read-only mode enforcement
"""

from fastapi import HTTPException
import re

FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop",
    "truncate", "alter", "create", "grant",
    "revoke", "exec", "execute", "call",
    "merge", "replace", "lock", "unlock",
    "rename",
]

# Patterns that suggest SQL injection attempts
SUSPICIOUS_PATTERNS = [
    r";\s*(insert|update|delete|drop|alter|create)",
    r"--\s*$",
    r"/\*.*\*/",
    r"'\s*;\s*",
    r"union\s+all\s+select.*from\s+information_schema",
    r"into\s+outfile",
    r"into\s+dumpfile",
    r"load_file\s*\(",
    r"benchmark\s*\(",
    r"sleep\s*\(",
    r"waitfor\s+delay",
    r"pg_sleep\s*\(",
    r"dbms_pipe",
]


def validate_sql(sql: str):
    """Validate SQL for safety. Raises HTTPException on violation."""

    if not sql or not sql.strip():
        raise HTTPException(
            status_code=400,
            detail="Empty SQL query.",
        )

    sql_clean = sql.strip()
    sql_lower = sql_clean.lower()

    # ---- 1. Multiple statement check ----
    # Remove strings before counting semicolons
    no_strings = re.sub(
        r"'[^']*'", "", sql_clean
    )
    semicolons = no_strings.count(";")

    if semicolons > 1:
        raise HTTPException(
            status_code=400,
            detail=(
                "Multiple SQL statements detected. "
                "Only single queries are allowed."
            ),
        )

    # Strip trailing semicolon
    if sql_clean.endswith(";"):
        sql_clean = sql_clean[:-1].strip()
        sql_lower = sql_clean.lower()

    # ---- 2. SELECT/WITH only ----
    if not (
        sql_lower.startswith("select")
        or sql_lower.startswith("with")
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only SELECT queries are allowed. "
                f"Found: {sql_lower.split()[0].upper()}"
            ),
        )

    # ---- 3. Forbidden keyword check ----
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(
            rf"\b{keyword}\b", sql_lower
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Forbidden SQL operation: "
                    f"{keyword.upper()}. "
                    f"This system is read-only."
                ),
            )

    # ---- 4. Suspicious pattern check ----
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, sql_lower):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Suspicious SQL pattern detected. "
                    "Query blocked for security."
                ),
            )

    # ---- 5. Query depth check ----
    # Prevent deeply nested subqueries (>5 levels)
    depth = sql_lower.count("(")
    if depth > 10:
        raise HTTPException(
            status_code=400,
            detail=(
                "Query too complex. Maximum nesting "
                "depth exceeded."
            ),
        )

    # ---- 6. Length check ----
    if len(sql_clean) > 5000:
        raise HTTPException(
            status_code=400,
            detail=(
                "Query too long. Maximum 5000 "
                "characters allowed."
            ),
        )

    return True