import psycopg2
from psycopg2 import pool as pg_pool

from app.db.connection_store import active_connection

_pool = None
_pool_key = None


class PooledConnection:
    """Wraps a pooled connection so .close() returns it to the pool
    instead of actually closing it. This lets all existing code
    continue calling conn.close() without any changes."""

    def __init__(self, conn, connection_pool):
        self._conn = conn
        self._pool = connection_pool

    def close(self):
        try:
            self._conn.rollback()
        except Exception:
            pass
        self._pool.putconn(self._conn)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _get_pool_key():
    """Returns a hashable key from current connection params
    so we can detect when the user switches databases."""
    return (
        active_connection.get("db_type", "postgres"),
        active_connection["host"],
        active_connection["port"],
        active_connection["database"],
        active_connection["username"],
        active_connection["password"],
    )


def get_db_type():
    """Returns the current active database type."""
    return active_connection.get("db_type", "postgres")


def get_connection():
    """Returns a database connection based on the active db_type.
    PostgreSQL uses connection pooling; MySQL and Oracle use
    direct connections."""

    if not active_connection["host"]:
        raise Exception("No active database connection selected.")

    db_type = get_db_type()

    if db_type == "postgres":
        return _get_postgres_connection()
    elif db_type == "mysql":
        return _get_mysql_connection()
    elif db_type == "oracle":
        return _get_oracle_connection()
    else:
        raise Exception(f"Unsupported database type: {db_type}")


def _get_postgres_connection():
    global _pool, _pool_key

    current_key = _get_pool_key()

    if _pool is None or _pool_key != current_key:
        if _pool is not None:
            _pool.closeall()

        _pool = pg_pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dbname=active_connection["database"],
            user=active_connection["username"],
            host=active_connection["host"],
            port=active_connection["port"],
            password=active_connection["password"],
        )
        _pool_key = current_key

    conn = _pool.getconn()
    return PooledConnection(conn, _pool)


def _get_mysql_connection():
    import pymysql

    conn = pymysql.connect(
        host=active_connection["host"],
        port=int(active_connection["port"]),
        database=active_connection["database"],
        user=active_connection["username"],
        password=active_connection["password"],
    )
    return conn


def _get_oracle_connection():
    import oracledb

    dsn = (
        f'{active_connection["host"]}:'
        f'{active_connection["port"]}/'
        f'{active_connection["database"]}'
    )

    conn = oracledb.connect(
        user=active_connection["username"],
        password=active_connection["password"],
        dsn=dsn,
    )
    return conn