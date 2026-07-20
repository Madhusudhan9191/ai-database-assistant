from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
from contextlib import asynccontextmanager
from app.core.logging_config import setup_logging
from app.core.config import settings

STARTUP_TIME = time.time()

# Initialize logging system
setup_logging()

from app.services.auth_service import decode_access_token
from app.routes.connection import router as connection_router
from app.routes.schema import router as schema_router
from app.routes.dashboard import router as dashboard_router
from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.routes.ask import router as ask_router
from app.routes.history import router as history_router
from app.routes.favorites import router as favorites_router
from app.routes.reports import router as reports_router


logger = logging.getLogger(__name__)

async def load_connection_context(request: Request):
    """Global dependency to load the active database connection context for the request's user."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = decode_access_token(token)
            if payload and "user_id" in payload:
                user_id = payload["user_id"]
                from app.db.metadata_db import get_user_connection
                from app.db.connection_store import active_connection_ctx
                db_conn_info = get_user_connection(user_id)
                if db_conn_info:
                    active_connection_ctx.set(db_conn_info)
        except Exception:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize metadata DB and seed admin user
    from app.db.metadata_db import init_metadata_db, create_admin_from_env
    init_metadata_db()
    create_admin_from_env()

    # Production JWT secret safety check
    if settings.environment.lower() == "production" and settings.jwt_secret == "ai-database-assistant-super-secret-key-change-in-production":
        logger.critical("PRODUCTION SECURITY BREACH: jwt_secret cannot be default in production!")
        raise ValueError("PRODUCTION SECURITY BREACH: jwt_secret cannot be default in production!")
    
    logger.info("Application started. Environment loaded. Metadata DB initialized.")
    yield
    logger.info("Application shutdown.")

app = FastAPI(lifespan=lifespan, dependencies=[Depends(load_connection_context)])

# Middleware to inject X-Request-ID
import uuid
@app.middleware("http")
async def add_request_id_header(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

app.include_router(auth_router)
app.include_router(connection_router)
app.include_router(schema_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
app.include_router(ask_router)
app.include_router(history_router)
app.include_router(favorites_router)
app.include_router(reports_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Request-ID"],
)


@app.get("/")
def home():
    return {
        "message": "AI Database Assistant API"
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/health")
def api_health_check():
    return {"status": "ok"}


@app.get("/api/version")
def api_version():
    return {
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": int(time.time() - STARTUP_TIME)
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Global unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact the administrator."},
    )



