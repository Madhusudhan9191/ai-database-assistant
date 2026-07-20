from fastapi import APIRouter, HTTPException, Depends

from app.models.connection import ConnectionRequest
from app.db.connection_store import active_connection
from app.services.auth_service import get_current_user

router = APIRouter()


@router.post("/test-connection")
def test_connection(data: ConnectionRequest, current_user: dict = Depends(get_current_user)):

    try:
        # Load password from database if not provided (for secure auto-reconnect)
        password = data.password
        if not password:
            from app.db.metadata_db import get_user_connection
            saved = get_user_connection(current_user["id"])
            if (saved and 
                saved["db_type"] == data.db_type and 
                saved["host"] == data.host and 
                str(saved["port"]) == str(data.port) and 
                saved["database"] == data.database and 
                saved["username"] == data.username):
                password = saved["password"]
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Database password is required."
                )

        if data.db_type == "postgres":
            import psycopg2

            conn = psycopg2.connect(
                dbname=data.database,
                user=data.username,
                password=password,
                host=data.host,
                port=data.port,
            )
            conn.close()

        elif data.db_type == "mysql":
            import pymysql

            conn = pymysql.connect(
                host=data.host,
                port=int(data.port),
                database=data.database,
                user=data.username,
                password=password,
            )
            conn.close()

        elif data.db_type == "oracle":
            import oracledb

            dsn = f"{data.host}:{data.port}/{data.database}"
            conn = oracledb.connect(
                user=data.username,
                password=password,
                dsn=dsn,
            )
            conn.close()

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported database type: {data.db_type}",
            )

        # Save to metadata DB
        from app.db.metadata_db import save_user_connection
        save_user_connection(
            user_id=current_user["id"],
            db_type=data.db_type,
            host=data.host,
            port=str(data.port),
            database=data.database,
            username=data.username,
            password=password
        )

        # Save to active connection store
        active_connection["db_type"] = data.db_type
        active_connection["host"] = data.host
        active_connection["port"] = data.port
        active_connection["database"] = data.database
        active_connection["username"] = data.username
        active_connection["password"] = password

        return {
            "message": "Connection successful"
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post("/disconnect")
def disconnect(current_user: dict = Depends(get_current_user)):
    """Clears the active connection parameters and removes credentials from the metadata db."""
    try:
        from app.db.metadata_db import delete_user_connection
        delete_user_connection(current_user["id"])
        active_connection.clear()
        active_connection.update({
            "db_type": None,
            "host": None,
            "port": None,
            "database": None,
            "username": None,
            "password": None,
        })
        return {
            "message": "Disconnected and connection parameters cleared successfully."
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )