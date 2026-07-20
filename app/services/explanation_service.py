from app.core.ai_client import client


def explain_query(sql, question):
    """Generates a 1-sentence user-friendly explanation of what the SQL query is doing."""

    if not sql or not sql.strip():
        return "No query executed."

    prompt = f"""
You are a helpful business intelligence assistant. Your task is to explain a SQL query to a business user in a single, short, clear, plain-English sentence.

User's Original Question: {question}
SQL Query:
{sql}

Rules:
1. Explain what the query is doing in exactly one natural, friendly sentence (e.g. "This query finds the top 5 tenants who paid the most late fees in 2025.").
2. Speak in terms of business entities (properties, rent, tenants, expenses, maintenance requests), not SQL terms (joins, tables, where clause, group by).
3. Do not explain the SQL structure. Keep it high-level and customer-facing.
4. Do not include markdown, code snippets, or formatting.
5. Return ONLY the explanation sentence.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=100
        )

        explanation = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )
        return explanation

    except Exception as e:
        return "This query retrieves data matching your question."
