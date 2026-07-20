from decimal import Decimal

from app.db.database import get_connection


def convert_decimal(value):

    if isinstance(value, Decimal):
        return float(value)

    return value


def execute_query(sql):
    sql = sql.strip().rstrip(";")
    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(sql)

        columns = [
            desc[0]
            for desc in cursor.description
        ]

        rows = cursor.fetchall()

        result = []

        for row in rows:

            row_dict = {}

            for col, value in zip(columns, row):

                row_dict[col] = convert_decimal(
                    value
                )

            result.append(row_dict)

        return result

    finally:

        cursor.close()
        conn.close()