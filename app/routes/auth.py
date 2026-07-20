from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, EmailStr
from app.db.metadata_db import get_metadata_connection, log_security_event
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from app.core.rate_limiter import (
    login_limiter,
    check_lockout,
    register_failed_login,
    reset_failed_logins
)
import sqlite3
import logging
import re

auth_logger = logging.getLogger("auth")

router = APIRouter(prefix="/auth", tags=["auth"])

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

@router.post("/register")
def register(data: UserRegister, request: Request):
    username = data.username.strip()
    email = data.email.strip().lower()
    password = data.password
    client_ip = request.client.host if request.client else "unknown"
    
    if not username or not email or not password:
        raise HTTPException(status_code=400, detail="Username, email, and password are required")
        
    # Enforce email format validation using custom regex (dependency-free)
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        raise HTTPException(status_code=400, detail="Invalid email format.")
        
    # Enforce password complexity rules
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter.")
    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character.")

    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        
        # Check if username or email already exists
        cur.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username or email is already registered")
            
        # Hash password and insert
        hashed = hash_password(password)
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, hashed)
        )
        conn.commit()
        user_id = cur.lastrowid
        
        # Log successful registration
        log_security_event(
            event_type="USER_REGISTERED",
            username=username,
            client_ip=client_ip,
            details=f"User registered successfully. ID: {user_id}"
        )

        # Generate token
        token = create_access_token({"user_id": user_id, "username": username})
        import secrets
        from app.db.metadata_db import save_refresh_token
        refresh_token = secrets.token_hex(32)
        save_refresh_token(user_id, refresh_token)
        return {
            "access_token": token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "is_admin": False
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Registration failed. Please contact the administrator.")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@router.post("/login")
def login(data: UserLogin, request: Request):
    username = data.username.strip()
    password = data.password
    client_ip = request.client.host if request.client else "unknown"
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username/Email and password are required")

    # 1. Check Rate Limiter
    if login_limiter.is_rate_limited(client_ip):
        log_security_event(
            event_type="RATE_LIMIT_TRIGGERED",
            username=username,
            client_ip=client_ip,
            details="Rate limit exceeded on /auth/login (10 requests/minute)"
        )
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again in a minute."
        )

    # 2. Check Account Lockout
    is_locked, remaining = check_lockout(username)
    if is_locked:
        log_security_event(
            event_type="LOCKED_OUT_ATTEMPT",
            username=username,
            client_ip=client_ip,
            details=f"Attempted login on locked account. Lockout active for another {remaining} seconds."
        )
        raise HTTPException(
            status_code=403,
            detail=f"Account is temporarily locked due to multiple failed login attempts. Please try again in {remaining} seconds."
        )
        
    conn = None
    cur = None
    try:
        conn = get_metadata_connection()
        cur = conn.cursor()
        
        # Look up by username or email
        cur.execute("SELECT id, username, email, password_hash, is_admin FROM users WHERE username = ? OR email = ?", (username, username.lower()))
        row = cur.fetchone()
        
        if not row or not verify_password(password, row["password_hash"]):
            # Register failed login attempt
            is_now_locked = register_failed_login(username)
            reason = "Invalid password" if row else "Username not found"
            
            if is_now_locked:
                log_security_event(
                    event_type="ACCOUNT_LOCKED",
                    username=username,
                    client_ip=client_ip,
                    details="Account locked out for 15 minutes after 5 consecutive failed login attempts."
                )
            else:
                log_security_event(
                    event_type="FAILED_LOGIN",
                    username=username,
                    client_ip=client_ip,
                    details=f"Failed login attempt: {reason}"
                )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
            
        user_id = row["id"]
        
        # Success: reset failed login attempts
        reset_failed_logins(username)
        log_security_event(
            event_type="SUCCESSFUL_LOGIN",
            username=username,
            client_ip=client_ip,
            details="User successfully authenticated."
        )

        # Generate token
        token = create_access_token({"user_id": user_id, "username": row["username"]})
        import secrets
        from app.db.metadata_db import save_refresh_token
        refresh_token = secrets.token_hex(32)
        save_refresh_token(user_id, refresh_token)
        return {
            "access_token": token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "username": row["username"],
                "email": row["email"],
                "is_admin": bool(row["is_admin"])
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Authentication error. Please contact the administrator.")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh_token(data: RefreshRequest):
    from app.db.metadata_db import get_user_by_refresh_token, save_refresh_token
    import secrets
    user = get_user_by_refresh_token(data.refresh_token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )
    # Generate new access token
    new_access_token = create_access_token({"user_id": user["id"], "username": user["username"]})
    # Rotate the refresh token
    new_refresh_token = secrets.token_hex(32)
    save_refresh_token(user["id"], new_refresh_token)
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user": user
    }

