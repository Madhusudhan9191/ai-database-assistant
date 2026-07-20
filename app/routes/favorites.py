from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.models.schemas import FavoriteRequest
from app.services.auth_service import get_current_user
from app.services.favorites_service import (
    add_favorite,
    get_compatible_favorites,
    delete_favorite,
)

router = APIRouter()


@router.post("/favorites")
def add_fav(data: FavoriteRequest, current_user: dict = Depends(get_current_user)):
    from app.services.schema_service import get_schema_hash
    from app.db.connection_store import active_connection
    db_type = active_connection.get("db_type") or "postgres"
    db_name = active_connection.get("database") or ""
    try:
        schema_hash = get_schema_hash()
    except Exception:
        schema_hash = "unknown"
    fav_id = add_favorite(
        question=data.question,
        generated_sql=data.generated_sql,
        db_type=db_type,
        db_name=db_name,
        schema_hash=schema_hash,
        user_id=current_user["id"]
    )
    if not fav_id:
        raise HTTPException(status_code=400, detail="Failed to save favorite query")
    return {"message": "Query added to favorites", "id": fav_id}


@router.get("/favorites")
def get_favs(
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
    return get_compatible_favorites(db_type, db_name, schema_hash, current_user["id"], limit=limit, offset=offset)


@router.delete("/favorites/{id}")
def remove_fav(id: int, current_user: dict = Depends(get_current_user)):
    success = delete_favorite(id, current_user["id"])
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete favorite query")
    return {"message": "Favorite query removed successfully"}
