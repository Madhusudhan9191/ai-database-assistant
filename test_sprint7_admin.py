import sys
import os
import time

# Add current workspace directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.db.metadata_db import get_metadata_connection, init_metadata_db, create_admin_from_env

client = TestClient(app, raise_server_exceptions=False)

def test_sprint7_admin_analytics():
    print("\n--- Running Sprint 7 Monitoring & Admin Analytics Tests ---")

    # Initialize DB schema and seed admin
    init_metadata_db()
    create_admin_from_env()

    # 1. Verify /api/health Endpoint
    print("\n1. Testing /api/health endpoint...")
    res = client.get("/api/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert res.json() == {"status": "ok"}, f"Unexpected response: {res.json()}"
    print("Health check endpoint verified successfully.")

    # 2. Verify /api/version Endpoint
    print("\n2. Testing /api/version endpoint...")
    res = client.get("/api/version")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "version" in data
    assert "environment" in data
    assert "uptime_seconds" in data
    assert data["version"] == settings.app_version
    assert data["environment"] == settings.environment
    assert data["uptime_seconds"] >= 0
    print(f"Version check endpoint verified. Uptime is {data['uptime_seconds']} seconds.")

    # 3. Verify /admin/stats security (Unauthorized / Forbidden)
    print("\n3. Testing /admin/stats authorization controls...")
    # Test 3a: No credentials (should fail with 401)
    res_no_auth = client.get("/admin/stats")
    assert res_no_auth.status_code == 401, f"Expected 401, got {res_no_auth.status_code}"
    
    # Test 3b: Non-admin user (should fail with 403)
    # First, let's create a regular user
    reg_username = f"user_{int(time.time())}"
    reg_email = f"{reg_username}@example.com"
    reg_password = "Password123!"
    
    reg_res = client.post("/auth/register", json={
        "username": reg_username,
        "email": reg_email,
        "password": reg_password
    })
    assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
    reg_token = reg_res.json()["access_token"]
    
    # Verify non-admin gets 403
    headers_reg = {"Authorization": f"Bearer {reg_token}"}
    res_forbidden = client.get("/admin/stats", headers=headers_reg)
    assert res_forbidden.status_code == 403, f"Expected 403 for regular user, got {res_forbidden.status_code}"
    print("Access controls successfully blocked non-admin access.")

    # 4. Verify /admin/stats for admin user (Success)
    print("\n4. Testing /admin/stats access with admin credentials...")
    # Register/Login as admin (credentials from settings)
    admin_res = client.post("/auth/login", json={
        "username": settings.admin_username,
        "password": settings.admin_password
    })
    
    # If the admin is not seeded/login fails, seed them explicitly for testing
    if admin_res.status_code != 200:
        # Check if username exists, if not, register them as admin via DB
        conn = get_metadata_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id FROM users WHERE username = ?", (settings.admin_username,))
            if not cur.fetchone():
                from app.services.auth_service import hash_password
                hashed = hash_password(settings.admin_password)
                cur.execute(
                    "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 1)",
                    (settings.admin_username, settings.admin_email, hashed)
                )
                conn.commit()
        finally:
            cur.close()
            conn.close()
        
        # Retry login
        admin_res = client.post("/auth/login", json={
            "username": settings.admin_username,
            "password": settings.admin_password
        })
        
    assert admin_res.status_code == 200, f"Admin login failed: {admin_res.text}"
    admin_token = admin_res.json()["access_token"]
    assert admin_res.json()["user"]["is_admin"] is True, "User should be flagged is_admin=True"
    
    # Fetch stats
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    stats_res = client.get("/admin/stats", headers=headers_admin)
    assert stats_res.status_code == 200, f"Expected 200, got {stats_res.status_code}"
    stats_data = stats_res.json()
    
    # Assert stats fields
    for field in [
        "total_users", "total_reports", "total_queries", "success_queries",
        "failed_queries", "total_favorites", "repair_attempts", "repair_successes",
        "repair_success_rate", "daily_metrics"
    ]:
        assert field in stats_data, f"Missing stats field: {field}"
        
    assert stats_data["total_users"] >= 1
    assert isinstance(stats_data["daily_metrics"], list)
    print("Admin stats fetched and validated successfully.")

    # 5. Verify SQL Repair Telemetry Logging
    print("\n5. Testing telemetry logs for query execution and repair attempts...")
    conn = get_metadata_connection()
    cur = conn.cursor()
    # Count initial rows
    cur.execute("SELECT COUNT(*) FROM query_logs")
    initial_log_count = cur.fetchone()[0]
    cur.close()
    conn.close()

    # Trigger a dummy successful ask
    # Mocking ask question or running it directly (since it might need database active connection)
    # We can invoke save_query directly to verify DB inserts, or ask endpoint
    from app.services.history_service import save_query
    
    save_query(
        question="What is the average rent?",
        sql="SELECT AVG(rent) FROM properties",
        execution_time_ms=120,
        success=True,
        user_id=reg_res.json()["user"]["id"],
        repair_attempted=1,
        repaired=1
    )
    
    conn = get_metadata_connection()
    cur = conn.cursor()
    cur.execute("SELECT repair_attempted, repaired, success FROM query_logs ORDER BY id DESC LIMIT 1")
    last_log = cur.fetchone()
    assert last_log["repair_attempted"] == 1
    assert last_log["repaired"] == 1
    assert last_log["success"] == 1
    cur.close()
    conn.close()
    print("Query repair telemetry successfully verified in metadata database.")
    
    print("\nAll Sprint 7 monitoring and admin analytics tests completed successfully!")

if __name__ == "__main__":
    test_sprint7_admin_analytics()
