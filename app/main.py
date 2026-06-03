from fastapi import FastAPI, HTTPException

from app.models.schemas import UserQuestion, QueryResponse
from app.services.ai_service import generate_sql
from app.services.query_service import execute_query
from app.services.history_service import save_query,get_query_history,get_history_count,get_latest_queries
import time
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "message": "AI Database Assistant API"
    }


@app.post("/ask", response_model=QueryResponse)
def ask_question(data: UserQuestion):

    try:

        question = data.question

        # Generate SQL using AI
        sql = generate_sql(question)

        # Clean SQL output
        sql = sql.replace("```sql", "")
        sql = sql.replace("```", "")
        sql = sql.strip()

        # Security Check
        if not sql.lower().startswith("select"):
            raise HTTPException(
                status_code=400,
                detail="Only SELECT queries are allowed."
            )
        
        start_time = time.time()
        result = execute_query(sql)
        execution_time_ms = int(
           (time.time() - start_time) * 1000)

        save_query(question, sql,execution_time_ms)
        

        return {
            "question": question,
            "generated_sql": sql,
            "execution_time_ms": execution_time_ms,
            "data": result
            
        }

    except Exception as e:
        raise HTTPException(
          status_code=500,
           detail=str(e)
    )
    
    
@app.get("/history")
def history():
        return get_query_history()

@app.get("/history/count")
def history_count():
    return get_history_count()

@app.get("/history/latest")
def history_latest():
    return get_latest_queries()


