from pydantic import BaseModel
from typing import Any, Optional


class UserQuestion(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    generated_sql: str
    execution_time_ms: int
    data: list[Any]

    # Phase 3: Structured insights (dict with sections)
    insights: Optional[Any] = None

    # Phase 3: Auto-detected KPIs
    kpis: Optional[list] = None

    show_chart: Optional[bool] = None
    chart_type: Optional[str] = None

    chart_data: Optional[dict] = None
    
    # Sprint 3: Plain-English query explanation
    explanation: Optional[str] = None


class BulkDeleteRequest(BaseModel):
    ids: list[int]


class SavedReportRequest(BaseModel):
    report_name: str
    question: str
    generated_sql: str
    chart_type: str


class FavoriteRequest(BaseModel):
    question: str
    generated_sql: str