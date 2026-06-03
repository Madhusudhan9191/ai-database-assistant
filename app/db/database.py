import psycopg2
from app.config import (
    DB_NAME,
    DB_USER,
    DB_HOST,
    DB_PORT
)

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        host=DB_HOST,
        port=DB_PORT
    )