from app.db.database import get_connection


def execute_query(sql):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(sql)

    columns = [desc[0] for desc in cur.description]

    rows = cur.fetchall()

    result = []

    for row in rows:
        result.append(
            dict(zip(columns, row))
        )

    cur.close()
    conn.close()

    return result