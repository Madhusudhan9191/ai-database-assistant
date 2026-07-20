import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

# Locate metadata DB in root workspace folder
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assistant_metadata.db"))

def get_metadata_connection():
    """Returns a connection to the local SQLite metadata database."""
    conn = sqlite3.connect(DB_PATH)
    # Enable dict-like Row access
    conn.row_factory = sqlite3.Row
    return conn

def init_metadata_db():
    """Initializes the SQLite database schema if not already present."""
    logger.info(f"Initializing metadata DB at {DB_PATH}")
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        # 1. Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Create query_logs table with telemetry fields
        cur.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                generated_sql TEXT,
                execution_time_ms INTEGER,
                success INTEGER,
                error_message TEXT,
                row_count INTEGER,
                chart_type TEXT,
                question_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. Create saved_reports table with soft delete indicates (is_active)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saved_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_name TEXT NOT NULL,
                question TEXT NOT NULL,
                generated_sql TEXT NOT NULL,
                chart_type TEXT NOT NULL,
                database_type TEXT NOT NULL,
                database_name TEXT NOT NULL,
                schema_hash TEXT NOT NULL,
                schema_version TEXT DEFAULT 'v1',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_execution_time REAL,
                execution_count INTEGER DEFAULT 0
            )
        """)

        # 4. Create favorites table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                generated_sql TEXT NOT NULL,
                database_type TEXT NOT NULL,
                database_name TEXT NOT NULL,
                schema_hash TEXT NOT NULL,
                schema_version TEXT DEFAULT 'v1',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Create user_connections table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_connections (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                db_type TEXT NOT NULL,
                host TEXT NOT NULL,
                port TEXT NOT NULL,
                database TEXT NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6. Create schema_dashboards table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_dashboards (
                schema_hash TEXT PRIMARY KEY,
                dashboard_config TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6b. Create security_events table for auditing
        cur.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                username TEXT,
                client_ip TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6c. Create query_cache table for caching identical queries
        cur.execute("""
            CREATE TABLE IF NOT EXISTS query_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_hash TEXT NOT NULL,
                schema_hash TEXT NOT NULL,
                generated_sql TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # 7. Dynamically alter tables to add user_id column
        for table in ["query_logs", "saved_reports", "favorites"]:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)")
                conn.commit()
                logger.info(f"Successfully added user_id column to {table}")
            except sqlite3.OperationalError as op_err:
                if "duplicate column name" in str(op_err).lower():
                    # Already added, ignore
                    pass
                else:
                    logger.warning(f"Operational error adding user_id to {table}: {op_err}")
            except Exception as alter_err:
                logger.warning(f"Error altering table {table}: {alter_err}")

        # 8. Dynamically add is_admin column to users table
        try:
            cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            conn.commit()
            logger.info("Successfully added is_admin column to users")
        except sqlite3.OperationalError as op_err:
            if "duplicate column name" in str(op_err).lower():
                pass
            else:
                logger.warning(f"Operational error adding is_admin to users: {op_err}")
        except Exception as alter_err:
            logger.warning(f"Error altering users table: {alter_err}")

        # 8b. Dynamically add refresh_token column to users table
        try:
            cur.execute("ALTER TABLE users ADD COLUMN refresh_token TEXT")
            conn.commit()
            logger.info("Successfully added refresh_token column to users")
        except sqlite3.OperationalError as op_err:
            if "duplicate column name" in str(op_err).lower():
                pass
            else:
                logger.warning(f"Operational error adding refresh_token to users: {op_err}")
        except Exception as alter_err:
            logger.warning(f"Error altering users table: {alter_err}")

        # 9. Dynamically add repair_attempted and repaired columns to query_logs table
        for col in ["repair_attempted", "repaired"]:
            try:
                cur.execute(f"ALTER TABLE query_logs ADD COLUMN {col} INTEGER DEFAULT 0")
                conn.commit()
                logger.info(f"Successfully added {col} column to query_logs")
            except sqlite3.OperationalError as op_err:
                if "duplicate column name" in str(op_err).lower():
                    pass
                else:
                    logger.warning(f"Operational error adding {col} to query_logs: {op_err}")
            except Exception as alter_err:
                logger.warning(f"Error altering query_logs table for {col}: {alter_err}")

    except Exception as e:
        logger.exception(f"Failed to initialize metadata DB: {e}")
    finally:
        cur.close()
        conn.close()


def create_admin_from_env():
    """Seeds an administrator user if credentials exist in the environment settings and no admin exists."""
    from app.core.config import settings
    from app.services.auth_service import hash_password
    
    username = settings.admin_username
    email = settings.admin_email
    password = settings.admin_password

    if not username or not email or not password:
        logger.info("Admin seeding skipped: admin credentials not fully specified in environment.")
        return

    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        
        # Check if any admin exists
        cur.execute("SELECT id FROM users WHERE is_admin = 1")
        if cur.fetchone():
            logger.info("Admin seeding skipped: administrator account already exists.")
            return
            
        # Hash password and insert admin
        password_hash = hash_password(password)
        cur.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 1)",
            (username, email, password_hash)
        )
        conn.commit()
        logger.info(f"Successfully seeded administrator account: {username}")
    except Exception as e:
        logger.warning(f"Failed to seed administrator account: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def save_user_connection(user_id: int, db_type: str, host: str, port: str, database: str, username: str, password: str):
    """Saves or updates database connection details for a specific user."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id FROM user_connections WHERE user_id = ?", (user_id,))
        if cur.fetchone():
            cur.execute("""
                UPDATE user_connections
                SET db_type=?, host=?, port=?, database=?, username=?, password=?, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=?
            """, (db_type, host, port, database, username, password, user_id))
        else:
            cur.execute("""
                INSERT INTO user_connections (user_id, db_type, host, port, database, username, password)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, db_type, host, port, database, username, password))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save user connection for user {user_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_user_connection(user_id: int):
    """Fetches database connection details for a specific user."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT db_type, host, port, database, username, password
            FROM user_connections
            WHERE user_id = ?
        """, (user_id,))
        row = cur.fetchone()
        if row:
            return {
                "db_type": row["db_type"],
                "host": row["host"],
                "port": row["port"],
                "database": row["database"],
                "username": row["username"],
                "password": row["password"]
            }
        return None
    except Exception as e:
        logger.error(f"Failed to fetch user connection for user {user_id}: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def save_schema_dashboard(schema_hash: str, dashboard_config: str):
    """Saves the dynamic dashboard config mapped to a schema hash."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT OR REPLACE INTO schema_dashboards (schema_hash, dashboard_config)
            VALUES (?, ?)
        """, (schema_hash, dashboard_config))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save schema dashboard for hash {schema_hash}: {e}")
    finally:
        cur.close()
        conn.close()

def get_schema_dashboard(schema_hash: str):
    """Fetches the dynamic dashboard config for a schema hash."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT dashboard_config FROM schema_dashboards WHERE schema_hash = ?", (schema_hash,))
        row = cur.fetchone()
        if row:
            return row["dashboard_config"]
        return None
    except Exception as e:
        logger.error(f"Failed to fetch schema dashboard for hash {schema_hash}: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def log_security_event(event_type: str, username: str, client_ip: str, details: str):
    """Logs a security event to the SQLite database and internal warnings log."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO security_events (event_type, username, client_ip, details)
            VALUES (?, ?, ?, ?)
        """, (event_type, username, client_ip, details))
        conn.commit()
        # Also write to security log
        logger.warning(f"[SECURITY EVENT] type={event_type} user={username} ip={client_ip} details={details}")
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")
    finally:
        cur.close()
        conn.close()

def save_refresh_token(user_id: int, refresh_token: str):
    """Saves the refresh token for a user."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET refresh_token = ? WHERE id = ?", (refresh_token, user_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save refresh token: {e}")
    finally:
        cur.close()
        conn.close()

def get_user_by_refresh_token(refresh_token: str):
    """Retrieves a user by their active refresh token."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, username, email, is_admin FROM users WHERE refresh_token = ?", (refresh_token,))
        row = cur.fetchone()
        if row:
            return {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "is_admin": bool(row["is_admin"])
            }
        return None
    except Exception as e:
        logger.error(f"Failed to fetch user by refresh token: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def clear_refresh_token(user_id: int):
    """Clears the refresh token for a user."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET refresh_token = NULL WHERE id = ?", (user_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to clear refresh token: {e}")
    finally:
        cur.close()
        conn.close()

def delete_user_connection(user_id: int):
    """Removes a user's database connection credentials from metadata db."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM user_connections WHERE user_id = ?", (user_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to delete user connection for user {user_id}: {e}")
    finally:
        cur.close()
        conn.close()

def get_cached_query(question_hash: str, schema_hash: str):
    """Fetches a cached query result if present."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT generated_sql, result_json, created_at
            FROM query_cache
            WHERE question_hash = ? AND schema_hash = ?
            ORDER BY created_at DESC LIMIT 1
        """, (question_hash, schema_hash))
        row = cur.fetchone()
        if row:
            return {
                "generated_sql": row["generated_sql"],
                "result_json": row["result_json"],
                "created_at": row["created_at"]
            }
        return None
    except Exception as e:
        logger.error(f"Failed to fetch cached query: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def cache_query(question_hash: str, schema_hash: str, generated_sql: str, result_json: str):
    """Stores a generated query and result in the cache."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO query_cache (question_hash, schema_hash, generated_sql, result_json)
            VALUES (?, ?, ?, ?)
        """, (question_hash, schema_hash, generated_sql, result_json))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to cache query: {e}")
    finally:
        cur.close()
        conn.close()

def clear_expired_cache(ttl_seconds: int):
    """Clears cache entries older than the TTL seconds."""
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM query_cache
            WHERE datetime(created_at) < datetime('now', ?)
        """, (f"-{ttl_seconds} seconds",))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to clear expired cache: {e}")
    finally:
        cur.close()
        conn.close()

# DB initialization is called explicitly during application lifespan to avoid circular imports


