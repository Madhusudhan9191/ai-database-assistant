"""
History & Audit Trail Service — Scoped to User ID
Stores audit logs inside the local metadata database and scopes operations to user_id.
"""

import logging
import hashlib
from app.db.metadata_db import get_metadata_connection

logger = logging.getLogger(__name__)

def save_query(
    question,
    sql,
    execution_time_ms,
    success=True,
    error_message=None,
    row_count=None,
    chart_type=None,
    user_id=None,
    repair_attempted=0,
    repaired=0,
):
    """Save a query execution to the metadata SQLite DB associated with a user."""
    conn = None
    cur = None
    try:
        # Generate deterministic question hash
        question_hash = hashlib.sha256(question.strip().encode("utf-8")).hexdigest()

        conn = get_metadata_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO query_logs
            (question, generated_sql, execution_time_ms,
             success, error_message, row_count, chart_type, question_hash, user_id, repair_attempted, repaired)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question,
                sql,
                execution_time_ms,
                1 if success else 0,
                error_message,
                row_count,
                chart_type,
                question_hash,
                user_id,
                int(repair_attempted),
                int(repaired)
            ),
        )
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to save query log: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_query_history(user_id, limit: int = None, offset: int = None):
    """Get query history for a specific user from metadata DB with optional pagination."""
    conn = None
    cur = None
    result = []
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()

        query = """
            SELECT id, question, generated_sql, execution_time_ms,
                   success, error_message, row_count, chart_type, created_at
            FROM query_logs
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
        """
        params = [user_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

        cur.execute(query, tuple(params))

        rows = cur.fetchall()
        for row in rows:
            result.append({
                "id": row["id"],
                "question": row["question"],
                "generated_sql": row["generated_sql"],
                "execution_time_ms": row["execution_time_ms"],
                "success": bool(row["success"]),
                "error_message": row["error_message"],
                "row_count": row["row_count"],
                "chart_type": row["chart_type"],
                "created_at": row["created_at"],
            })
    except Exception as e:
        logger.warning(f"Failed to retrieve query history: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return result



def get_history_count(user_id):
    """Get total query count for a user."""
    conn = None
    cur = None
    count = 0
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM query_logs WHERE user_id = ?", (user_id,))
        count = cur.fetchone()[0]
    except Exception as e:
        logger.warning(f"Failed to count query history: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return {"total_queries": count}


def get_latest_queries(user_id, limit=10):
    """Get latest unique queries for a user."""
    conn = None
    cur = None
    result = []
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT question, MAX(created_at) AS latest_time
            FROM query_logs
            WHERE user_id = ?
            GROUP BY question
            ORDER BY latest_time DESC
            LIMIT ?
            """,
            (user_id, limit),
        )

        rows = cur.fetchall()
        for row in rows:
            result.append({
                "question": row["question"],
                "created_at": row["latest_time"],
            })
    except Exception as e:
        logger.warning(f"Failed to retrieve latest queries: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return result


def delete_query_log(log_id, user_id):
    """Delete a single query log by ID, owned by user."""
    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM query_logs WHERE id = ? AND user_id = ?", (log_id, user_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to delete query log {log_id}: {e}")
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def delete_all_query_logs(user_id):
    """Clear all query logs for a user."""
    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM query_logs WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to clear all query logs: {e}")
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def delete_bulk_query_logs(log_ids, user_id):
    """Delete multiple query logs in a single batch, owned by user."""
    if not log_ids:
        return True
    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        placeholders = ",".join(["?"] * len(log_ids))
        cur.execute(
            f"DELETE FROM query_logs WHERE id IN ({placeholders}) AND user_id = ?",
            (*tuple(log_ids), user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to bulk delete query logs: {e}")
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
