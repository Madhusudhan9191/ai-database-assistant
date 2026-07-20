from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.models.schemas import BulkDeleteRequest
from app.services.auth_service import get_current_user
from app.services.history_service import (
    get_query_history,
    get_history_count,
    get_latest_queries,
    delete_query_log,
    delete_all_query_logs,
    delete_bulk_query_logs,
)

router = APIRouter()


@router.get("/history")
def history(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    return get_query_history(current_user["id"], limit=limit, offset=offset)


@router.get("/history/count")
def history_count(current_user: dict = Depends(get_current_user)):
    return get_history_count(current_user["id"])


@router.get("/history/latest")
def history_latest(current_user: dict = Depends(get_current_user)):
    return get_latest_queries(current_user["id"])


@router.delete("/history")
def clear_history(current_user: dict = Depends(get_current_user)):
    success = delete_all_query_logs(current_user["id"])
    if not success:
        raise HTTPException(status_code=400, detail="Failed to clear history")
    return {"message": "All query logs cleared"}


@router.delete("/history/{id}")
def delete_single_log(id: int, current_user: dict = Depends(get_current_user)):
    success = delete_query_log(id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Query log not found")
    return {"message": "Query deleted successfully"}


@router.post("/history/bulk-delete")
def delete_bulk_logs(data: BulkDeleteRequest, current_user: dict = Depends(get_current_user)):
    success = delete_bulk_query_logs(data.ids, current_user["id"])
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete selected queries")
    return {"message": "Selected queries deleted successfully"}
