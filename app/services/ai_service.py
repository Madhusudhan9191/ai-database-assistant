from groq import Groq
from app.config import GROQ_API_KEY
from app.services.schema_service import get_database_schema

client = Groq(
    api_key=GROQ_API_KEY
)

def generate_sql(question):

    schema = get_database_schema()

    prompt = f"""
     You are a PostgreSQL expert.

     Database Schema:

     {schema}

     Rules:
     1. Generate PostgreSQL SQL only.
     2. Return ONLY SQL.
     3. Use table and column names exactly as provided.
     4. Do not explain anything.

     Question:
     {question}
     """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content.strip()
