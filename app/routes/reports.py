from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.models.schemas import SavedReportRequest
from app.services.auth_service import get_current_user
from app.services.saved_reports_service import (
    save_report,
    get_compatible_reports,
    delete_saved_report,
)

router = APIRouter()


@router.post("/saved-reports")
def save_new_report(data: SavedReportRequest, current_user: dict = Depends(get_current_user)):
    from app.services.schema_service import get_schema_hash
    from app.db.connection_store import active_connection
    db_type = active_connection.get("db_type") or "postgres"
    db_name = active_connection.get("database") or ""
    try:
        schema_hash = get_schema_hash()
    except Exception:
        schema_hash = "unknown"
    report_id = save_report(
        report_name=data.report_name,
        question=data.question,
        generated_sql=data.generated_sql,
        chart_type=data.chart_type,
        db_type=db_type,
        db_name=db_name,
        schema_hash=schema_hash,
        user_id=current_user["id"]
    )
    if not report_id:
        raise HTTPException(status_code=400, detail="Failed to save report")
    return {"message": "Report saved successfully", "id": report_id}


@router.get("/saved-reports")
def get_reports(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    from app.services.schema_service import get_schema_hash
    from app.db.connection_store import active_connection
    db_type = active_connection.get("db_type") or "postgres"
    db_name = active_connection.get("database") or ""
    try:
        schema_hash = get_schema_hash()
    except Exception:
        schema_hash = "unknown"
    return get_compatible_reports(db_type, db_name, schema_hash, current_user["id"], limit=limit, offset=offset)


@router.delete("/saved-reports/{id}")
def delete_report(id: int, current_user: dict = Depends(get_current_user)):
    success = delete_saved_report(id, current_user["id"])
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete report")
    return {"message": "Report soft deleted successfully"}
