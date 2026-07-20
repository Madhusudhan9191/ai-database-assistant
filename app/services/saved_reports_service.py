import logging
from datetime import datetime
from app.db.metadata_db import get_metadata_connection

logger = logging.getLogger(__name__)

def save_report(report_name, question, generated_sql, chart_type, db_type, db_name, schema_hash, user_id):
    """Saves a report definition in the SQLite metadata database associated with a user."""
    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO saved_reports
            (report_name, question, generated_sql, chart_type, database_type, database_name, schema_hash, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (report_name, question, generated_sql, chart_type, db_type, db_name, schema_hash, user_id)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        logger.exception(f"Failed to save report: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_compatible_reports(db_type, db_name, schema_hash, user_id, limit: int = None, offset: int = None):
    """Retrieves active saved reports matching the database fingerprint and user ID with optional pagination."""
    conn = None
    cur = None
    result = []
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        query = """
            SELECT id, report_name, question, generated_sql, chart_type,
                   database_type, database_name, schema_hash, schema_version,
                   is_active, created_at, updated_at, last_execution_time, execution_count
            FROM saved_reports
            WHERE is_active = 1
              AND database_type = ?
              AND database_name = ?
              AND schema_hash = ?
              AND user_id = ?
            ORDER BY created_at DESC
        """
        params = [db_type, db_name, schema_hash, user_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        for r in rows:
            result.append({
                "id": r["id"],
                "report_name": r["report_name"],
                "question": r["question"],
                "generated_sql": r["generated_sql"],
                "chart_type": r["chart_type"],
                "database_type": r["database_type"],
                "database_name": r["database_name"],
                "schema_hash": r["schema_hash"],
                "schema_version": r["schema_version"],
                "is_active": r["is_active"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "last_execution_time": r["last_execution_time"],
                "execution_count": r["execution_count"],
            })
    except Exception as e:
        logger.exception(f"Failed to retrieve compatible reports: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return result


def delete_saved_report(report_id, user_id):
    """Soft deletes a saved report by setting is_active = 0 for the specified user."""
    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE saved_reports
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (report_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.exception(f"Failed to soft delete report {report_id} for user {user_id}: {e}")
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def increment_report_execution(report_id, execution_time_ms):
    """Increments report statistics after execution."""
    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE saved_reports
            SET execution_count = execution_count + 1,
                last_execution_time = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (float(execution_time_ms), report_id)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.warning(f"Failed to update report statistics: {e}")
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
