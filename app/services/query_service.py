from app.db.database import get_connection


def execute_query(sql):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(sql)

    columns = [desc[0] for desc in cursor.description]

    rows = cursor.fetchall()

    result = [
        dict(zip(columns, row))
        for row in rows
    ]

    cursor.close()
    conn.close()

    return result