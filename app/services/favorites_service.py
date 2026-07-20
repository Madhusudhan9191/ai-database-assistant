import logging
from app.db.metadata_db import get_metadata_connection

logger = logging.getLogger(__name__)

def add_favorite(question, generated_sql, db_type, db_name, schema_hash, user_id):
    """Saves a query to favorites in the metadata SQLite database associated with a user."""
    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        
        # Check if already favorited by this user
        cur.execute(
            """
            SELECT id FROM favorites
            WHERE question = ? AND database_type = ? AND database_name = ? AND schema_hash = ? AND user_id = ?
            """,
            (question, db_type, db_name, schema_hash, user_id)
        )
        row = cur.fetchone()
        if row:
            return row["id"]

        cur.execute(
            """
            INSERT INTO favorites
            (question, generated_sql, database_type, database_name, schema_hash, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (question, generated_sql, db_type, db_name, schema_hash, user_id)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        logger.exception(f"Failed to add favorite query: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_compatible_favorites(db_type, db_name, schema_hash, user_id, limit: int = None, offset: int = None):
    """Retrieves all favorite queries compatible with the current active database connection for a user with optional pagination."""
    conn = None
    cur = None
    result = []
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        query = """
            SELECT id, question, generated_sql, database_type, database_name, schema_hash, created_at
            FROM favorites
            WHERE database_type = ?
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
                "question": r["question"],
                "generated_sql": r["generated_sql"],
                "database_type": r["database_type"],
                "database_name": r["database_name"],
                "schema_hash": r["schema_hash"],
                "created_at": r["created_at"],
            })
    except Exception as e:
        logger.exception(f"Failed to retrieve favorites: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return result


def delete_favorite(fav_id, user_id):
    """Deletes a query from favorites for the specified user."""
    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM favorites WHERE id = ? AND user_id = ?", (fav_id, user_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.exception(f"Failed to delete favorite query {fav_id}: {e}")
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
