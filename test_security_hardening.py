import sys
import os
import time

# Add workspace directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.db.metadata_db import get_metadata_connection, init_metadata_db

client = TestClient(app, raise_server_exceptions=False)

def test_security_features():
    print("\n--- Running Security Hardening Verification Tests ---")

    # Initialize SQLite schema
    init_metadata_db()

    # 1. Verify Request ID Middleware
    print("\n1. Testing X-Request-ID response header...")
    res = client.get("/health")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    request_id = res.headers["X-Request-ID"]
    print(f"X-Request-ID verified successfully: {request_id}")

    # 2. Verify Email Validation
    print("\n2. Testing email validation during registration...")
    bad_email_res = client.post("/auth/register", json={
        "username": f"user_{int(time.time())}",
        "email": "invalid_email_format",
        "password": "Password123!"
    })
    assert bad_email_res.status_code == 400, f"Expected 400, got {bad_email_res.status_code}"
    print("Invalid email format rejected with 400 Bad Request.")

    # 3. Verify Password Complexity Policy
    print("\n3. Testing Password Complexity Policy during registration...")
    username = f"user_{int(time.time())}"
    email = f"{username}@example.com"
    
    # Test 3a: Weak password (too short)
    res_short = client.post("/auth/register", json={
        "username": username, "email": email, "password": "Pw1!"
    })
    assert res_short.status_code == 400
    assert "at least 8 characters" in res_short.json()["detail"]

    # Test 3b: Weak password (no uppercase)
    res_noupper = client.post("/auth/register", json={
        "username": username, "email": email, "password": "password123!"
    })
    assert res_noupper.status_code == 400
    assert "uppercase letter" in res_noupper.json()["detail"]

    # Test 3c: Weak password (no special character)
    res_nospec = client.post("/auth/register", json={
        "username": username, "email": email, "password": "Password123"
    })
    assert res_nospec.status_code == 400
    assert "special character" in res_nospec.json()["detail"]
    print("Password complexity policy verified. Weak passwords rejected with 400.")

    # 4. Verify Rate Limiting
    print("\n4. Testing login rate limiter...")
    # Trigger 11 quick requests to hit the limit of 10/min
    rate_limit_triggered = False
    for i in range(12):
        res_login = client.post("/auth/login", json={
            "username": "non_existent_user",
            "password": "Password123!"
        })
        if res_login.status_code == 429:
            rate_limit_triggered = True
            print(f"Rate limiter triggered on request {i+1}. Status 429 received.")
            break
            
    # Reset limiters for the remainder of the test
    from app.core.rate_limiter import login_limiter
    login_limiter.history.clear()

    # 5. Verify Account Lockout Policy
    print("\n5. Testing account lockout (5 consecutive failed attempts)...")
    target_user = f"lockuser_{int(time.time())}"
    target_email = f"{target_user}@example.com"
    correct_password = "Password123!"
    
    # Register the user
    reg_res = client.post("/auth/register", json={
        "username": target_user,
        "email": target_email,
        "password": correct_password
    })
    assert reg_res.status_code == 200

    # Reset login limiter history
    login_limiter.history.clear()

    # Fail login 5 times
    for i in range(5):
        fail_res = client.post("/auth/login", json={
            "username": target_user,
            "password": "WrongPassword123!"
        })
        assert fail_res.status_code == 401, f"Expected 401, got {fail_res.status_code}"

    # The 6th attempt (even with correct password) should be locked out with 403 Forbidden
    locked_res = client.post("/auth/login", json={
        "username": target_user,
        "password": correct_password
    })
    assert locked_res.status_code == 403, f"Expected 403 locked out, got {locked_res.status_code}"
    assert "temporarily locked" in locked_res.json()["detail"]
    print("Account lockout policy verified. 6th login attempt returned 403 Forbidden.")

    # 6. Verify Security Audit Logs in SQLite
    print("\n6. Verifying security events table logging...")
    conn = get_metadata_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT event_type, username, details FROM security_events ORDER BY id DESC LIMIT 5")
        rows = cur.fetchall()
        print("\nLast 5 security audit logs:")
        for r in rows:
            print(f"  - [{r['event_type']}] user={r['username']} details={r['details']}")
            
        # Ensure we have logged ACCOUNT_LOCKED, FAILED_LOGIN, etc.
        event_types = [r['event_type'] for r in rows]
        assert "ACCOUNT_LOCKED" in event_types or "FAILED_LOGIN" in event_types or "USER_REGISTERED" in event_types
        print("\nSecurity audit logging successfully verified in metadata DB.")
    finally:
        cur.close()
        conn.close()

    print("\nAll Security Hardening Verification Tests completed successfully!")

if __name__ == "__main__":
    test_security_features()
