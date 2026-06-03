from app.db.database import get_connection

def save_query(question, sql,execution_time_ms):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO query_history
        (question, generated_sql,execution_time_ms)
        VALUES (%s, %s, %s)
        """,
        (question, sql, execution_time_ms)
    )

    conn.commit()

    cur.close()
    conn.close()




def get_query_history():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT question,
               generated_sql,
               execution_time_ms,
               created_at
        FROM query_history
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    result = []

    for row in rows:
        result.append({
            "question": row[0],
            "generated_sql": row[1],
            "execution_time_ms": row[2],
            "created_at": row[3]
        })

    cur.close()
    conn.close()

    return result

def get_history_count():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM query_history"
    )

    count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return {"total_queries": count}

def get_latest_queries(limit=10):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT question,
               MAX(created_at) AS latest_time
        FROM query_history
        GROUP BY question
        ORDER BY latest_time DESC
        LIMIT %s
    """, (limit,))

    rows = cur.fetchall()

    result = []

    for row in rows:
        result.append({
            "question": row[0],
            "created_at": row[1]
        })

    cur.close()
    conn.close()

    return result
