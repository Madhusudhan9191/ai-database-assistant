from app.db.database import get_connection, get_db_type
from app.db.connection_store import active_connection

_schema_cache = None
_schema_cache_key = None


def get_database_schema():
    """Generates a schema description including table names, columns, 
    data types, and up to 3 distinct sample values for text columns.
    Results are cached in memory and reset when connection parameters change."""

    global _schema_cache, _schema_cache_key

    # Build connection key to detect switches
    current_key = (
        active_connection.get("db_type"),
        active_connection.get("host"),
        active_connection.get("port"),
        active_connection.get("database"),
        active_connection.get("username")
    )

    if _schema_cache is not None and _schema_cache_key == current_key:
        return _schema_cache

    # Cache miss - retrieve schema from database
    db_type = get_db_type()
    conn = None
    cur = None
    rows = []

    try:
        conn = get_connection()
        cur = conn.cursor()

        if db_type == "oracle":
            cur.execute("""
                SELECT table_name,
                       column_name,
                       data_type
                FROM user_tab_columns
                ORDER BY table_name, column_id
            """)
        elif db_type == "mysql":
            cur.execute("""
                SELECT table_name,
                       column_name,
                       data_type
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                ORDER BY table_name, ordinal_position
            """)
        else:
            cur.execute("""
                SELECT table_name,
                       column_name,
                       data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """)

        rows = cur.fetchall()
    except Exception:
        # Fallback if query fails
        rows = []
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

    if not rows:
        return "No schema metadata found."

    schema = ""
    current_table = None

    # We open a separate connection block to fetch samples to keep it clean
    sample_conn = None
    sample_cur = None
    try:
        sample_conn = get_connection()
        sample_cur = sample_conn.cursor()

        for table_name, column_name, data_type in rows:
            # Skip query history / internal tables if possible, but keep simple
            if table_name.lower() in ["query_logs", "query_history"]:
                continue

            if table_name != current_table:
                schema += f"\nTable Name: {table_name}\n"
                current_table = table_name

            samples_str = ""
            dtype_lower = data_type.lower()
            
            # Fetch samples for character/text types
            if any(term in dtype_lower for term in ["char", "text", "varchar", "clob"]):
                try:
                    q_col = f"`{column_name}`" if db_type == "mysql" else f'"{column_name}"'
                    q_tbl = f"`{table_name}`" if db_type == "mysql" else f'"{table_name}"'
                    
                    if db_type == "oracle":
                        query = f"SELECT DISTINCT {q_col} FROM {q_tbl} WHERE {q_col} IS NOT NULL FETCH FIRST 3 ROWS ONLY"
                    else:
                        query = f"SELECT DISTINCT {q_col} FROM {q_tbl} WHERE {q_col} IS NOT NULL LIMIT 3"
                    
                    sample_cur.execute(query)
                    samples = [str(r[0]) for r in sample_cur.fetchall() if r[0] is not None]
                    
                    if samples:
                        # Clean up formatting for short samples
                        samples_str = f" [Samples: {', '.join(samples[:3])}]"
                except Exception:
                    # Ignore failures for specific columns (e.g. permission or type issues)
                    pass

            schema += f"- {column_name} ({data_type}){samples_str}\n"

    except Exception:
        pass
    finally:
        if sample_cur:
            try:
                sample_cur.close()
            except Exception:
                pass
        if sample_conn:
            try:
                sample_conn.close()
            except Exception:
                pass

    # Save to cache
    _schema_cache = schema
    _schema_cache_key = current_key
    
    return schema


def get_schema_hash():
    """Computes a SHA256 hash of the current database schema representation."""
    import hashlib
    schema_text = get_database_schema()
    return hashlib.sha256(schema_text.encode("utf-8")).hexdigest()