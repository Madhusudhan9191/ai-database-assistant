from app.db.database import get_connection


def get_database_schema():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name,
               column_name,
               data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    schema = ""

    current_table = None

    for table_name, column_name, data_type in rows:

        if table_name != current_table:
            schema += f"\nTable Name: {table_name}\n"
            current_table = table_name

        schema += f"- {column_name} ({data_type})\n"

    return schema