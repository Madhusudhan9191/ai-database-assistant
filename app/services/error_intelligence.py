"""
Error Intelligence Service — Phase 1
Instead of showing generic "Database Error", parse the
error and provide helpful suggestions with possible fixes.
"""

import re
from app.db.database import get_connection, get_db_type


def get_intelligent_error(error, sql=None):
    """Parse a database error and return a helpful message."""

    error_str = str(error).lower()

    # --- Column not found ---
    col_match = re.search(
        r'column "?(\w+)"? (?:does not exist|unknown|not found)',
        error_str,
    ) or re.search(
        r"unknown column '?(\w+)'?",
        error_str,
    )

    if col_match:
        bad_col = col_match.group(1)
        table_name = _extract_table_from_sql(sql)
        possible_cols = _get_table_columns(table_name)

        msg = (
            f"Column '{bad_col}' does not exist."
        )
        if possible_cols:
            msg += "\n\nPossible columns:\n"
            for col in possible_cols[:15]:
                msg += f"  - {col}\n"

        return msg

    # --- Table not found ---
    table_match = re.search(
        r'relation "?(\w+)"? does not exist',
        error_str,
    ) or re.search(
        r"table '?[\w.]*\.?(\w+)'? doesn't exist",
        error_str,
    )

    if table_match:
        bad_table = table_match.group(1)
        possible_tables = _get_all_tables()

        msg = f"Table '{bad_table}' does not exist."
        if possible_tables:
            msg += "\n\nAvailable tables:\n"
            for tbl in possible_tables[:20]:
                msg += f"  - {tbl}\n"

        return msg

    # --- Syntax error ---
    if "syntax error" in error_str:
        position = re.search(
            r'at or near "(\w+)"', error_str
        )
        if position:
            return (
                f"SQL syntax error near "
                f"'{position.group(1)}'.\n"
                f"Check for missing commas, "
                f"parentheses, or keywords."
            )
        return (
            "SQL syntax error.\n"
            "Check for missing commas, "
            "parentheses, or keywords."
        )

    # --- Permission denied ---
    if "permission denied" in error_str:
        return (
            "Permission denied.\n"
            "The database user does not have "
            "access to this table or operation."
        )

    # --- Connection error ---
    if (
        "connection" in error_str
        and ("refused" in error_str or "timeout" in error_str)
    ):
        return (
            "Database connection failed.\n"
            "Check that the database server is "
            "running and accessible."
        )

    # --- Division by zero ---
    if "division by zero" in error_str:
        return (
            "Division by zero in query.\n"
            "Use NULLIF or CASE to handle "
            "zero denominators."
        )

    # --- Type mismatch ---
    if "type" in error_str and (
        "mismatch" in error_str
        or "cannot be cast" in error_str
        or "invalid input" in error_str
    ):
        return (
            "Data type mismatch.\n"
            "Check that column types match "
            "the comparison values."
        )

    # --- Fallback: return cleaned original ---
    clean = str(error)
    # Remove stack trace noise
    if "\n" in clean:
        clean = clean.split("\n")[0]

    return clean


def _extract_table_from_sql(sql):
    """Extract the main table name from a SQL query."""

    if not sql:
        return None

    match = re.search(
        r"\bfrom\s+(\w+)",
        sql, re.IGNORECASE,
    )
    return match.group(1) if match else None


def _get_table_columns(table_name):
    """Get column names for a table."""

    if not table_name:
        return []

    conn = None
    cur = None
    cols = []
    try:
        db_type = get_db_type()
        conn = get_connection()
        cur = conn.cursor()

        if db_type == "postgres":
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
                """,
                (table_name,),
            )
        elif db_type == "mysql":
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
                """,
                (table_name,),
            )
        elif db_type == "oracle":
            cur.execute(
                """
                SELECT column_name
                FROM user_tab_columns
                WHERE table_name = :1
                ORDER BY column_id
                """,
                (table_name.upper(),),
            )
        else:
            return []

        cols = [row[0] for row in cur.fetchall()]
    except Exception:
        pass
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return cols


def _get_all_tables():
    """Get all table names in the database."""

    conn = None
    cur = None
    tables = []
    try:
        db_type = get_db_type()
        conn = get_connection()
        cur = conn.cursor()

        if db_type == "postgres":
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
        elif db_type == "mysql":
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                ORDER BY table_name
            """)
        elif db_type == "oracle":
            cur.execute("""
                SELECT table_name
                FROM user_tables
                ORDER BY table_name
            """)
        else:
            return []

        tables = [row[0] for row in cur.fetchall()]
    except Exception:
        pass
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return tables
