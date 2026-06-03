from pydantic import BaseModel
from typing import Any

class UserQuestion(BaseModel):
    question: str

class QuestionRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    question: str
    generated_sql: str
    execution_time_ms: int
    data: list[Any]