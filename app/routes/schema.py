from fastapi import APIRouter, HTTPException, Depends
import re

from app.db.database import get_connection, get_db_type
from app.db.connection_store import active_connection
from app.services.auth_service import get_current_user

router = APIRouter()


def _validate_identifier(name):
    """Validates that a name contains only safe SQL identifier characters.
    This prevents SQL injection for all database types."""
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_$.]*$', name):
        raise HTTPException(
            status_code=400,
            detail="Invalid table name",
        )
    return name


def _quote_identifier(name, db_type):
    """Quote an identifier safely for the given DB type."""
    name = _validate_identifier(name)
    if db_type == "mysql":
        return f"`{name}`"
    else:
        return f'"{name}"'


def _check_connection_active():
    """Raises HTTPException if no active database connection exists."""
    if not active_connection.get("host"):
        raise HTTPException(
            status_code=400,
            detail="No active database connection. Please connect a database first.",
        )


@router.get("/schema/fingerprint")
def get_fingerprint(current_user: dict = Depends(get_current_user)):
    from app.services.schema_service import get_schema_hash
    db_type = active_connection.get("db_type") or "postgres"
    db_name = active_connection.get("database") or ""
    try:
        schema_hash = get_schema_hash()
    except Exception:
        schema_hash = "unknown"
    return {
        "database_type": db_type,
        "database_name": db_name,
        "schema_hash": schema_hash
    }


@router.get("/schema")
def get_schema(current_user: dict = Depends(get_current_user)):
    _check_connection_active()

    db_type = get_db_type()
    conn = get_connection()
    cur = conn.cursor()

    if db_type == "oracle":
        cur.execute("""
            SELECT table_name
            FROM user_tables
            ORDER BY table_name
        """)
    elif db_type == "mysql":
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            ORDER BY table_name
        """)
    else:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

    tables = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return {
        "tables": tables
    }


@router.get("/table-columns/{table_name}")
def get_table_columns(table_name: str, current_user: dict = Depends(get_current_user)):
    _check_connection_active()

    db_type = get_db_type()
    conn = get_connection()
    cur = conn.cursor()

    if db_type == "oracle":
        cur.execute("""
            SELECT column_name
            FROM user_tab_columns
            WHERE table_name = :1
            ORDER BY column_id
        """, (table_name.upper(),))
    elif db_type == "mysql":
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
    else:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))

    columns = [
        row[0]
        for row in cur.fetchall()
    ]

    cur.close()
    conn.close()

    return {
        "table": table_name,
        "columns": columns
    }


@router.get("/table-data/{table_name}")
def get_table_data(table_name: str, current_user: dict = Depends(get_current_user)):
    _check_connection_active()

    db_type = get_db_type()
    conn = get_connection()
    cur = conn.cursor()

    quoted = _quote_identifier(table_name, db_type)

    if db_type == "oracle":
        cur.execute(
            f"SELECT * FROM {quoted} FETCH FIRST 15 ROWS ONLY"
        )
    else:
        cur.execute(
            f"SELECT * FROM {quoted} LIMIT 15"
        )

    columns = [
        desc[0]
        for desc in cur.description
    ]

    rows = cur.fetchall()

    data = [
        dict(zip(columns, row))
        for row in rows
    ]

    cur.close()
    conn.close()

    return {
        "table": table_name,
        "data": data
    }


@router.get("/table-counts")
def get_table_counts(current_user: dict = Depends(get_current_user)):
    _check_connection_active()

    db_type = get_db_type()
    conn = get_connection()
    cur = conn.cursor()

    if db_type == "oracle":
        cur.execute("""
            SELECT table_name
            FROM user_tables
            ORDER BY table_name
        """)
    elif db_type == "mysql":
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            ORDER BY table_name
        """)
    else:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

    tables = [row[0] for row in cur.fetchall()]

    counts = {}

    for table in tables:
        quoted = _quote_identifier(table, db_type)
        cur.execute(
            f"SELECT COUNT(*) FROM {quoted}"
        )
        counts[table] = cur.fetchone()[0]

    cur.close()
    conn.close()

    return counts