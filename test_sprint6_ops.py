import sys
import os
import logging

# Add workspace directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app, raise_server_exceptions=False)

def test_sprint6_operations():
    print("\n--- Running Sprint 6 Operations & Configuration Tests ---")

    # 1. Verify Pydantic Settings
    print("\n1. Verifying Pydantic Settings load...")
    assert settings.groq_api_key is not None, "GROQ_API_KEY should be loaded from .env"
    assert settings.jwt_secret == "ai-database-assistant-super-secret-key-change-in-production", "JWT_SECRET should fall back or load"
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expiry == 60
    print("Pydantic settings loaded and verified successfully.")

    # 2. Verify Logging Setup and Log Files
    print("\n2. Verifying rotating log files configuration...")
    # Clear existing log files if any, to verify new logs write correctly
    for log_file in ["logs/app.log", "logs/errors.log", "logs/auth.log"]:
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
            except Exception:
                pass

    # Setup triggers
    logger = logging.getLogger("app.main")
    auth_logger = logging.getLogger("auth")

    # Log messages to check routing
    logger.info("Test Application event message")
    logger.error("Test Application error message")
    auth_logger.warning("Test Security/Auth login failure message")

    # Assert files exist
    assert os.path.exists("logs/app.log"), "app.log should be created"
    assert os.path.exists("logs/errors.log"), "errors.log should be created"
    assert os.path.exists("logs/auth.log"), "auth.log should be created"

    # Verify app.log contents (should contain Info & Error)
    with open("logs/app.log", "r", encoding="utf-8") as f:
        app_content = f.read()
        assert "Test Application event message" in app_content
        assert "Test Application error message" in app_content

    # Verify errors.log contents (should contain Error but NOT Info)
    with open("logs/errors.log", "r", encoding="utf-8") as f:
        errors_content = f.read()
        assert "Test Application error message" in errors_content
        assert "Test Application event message" not in errors_content

    # Verify auth.log contents (should contain security messages)
    with open("logs/auth.log", "r", encoding="utf-8") as f:
        auth_content = f.read()
        assert "Test Security/Auth login failure message" in auth_content
        assert "Test Application event message" not in auth_content

    print("Log files are successfully generated and events are routed to correct rotating logs.")

    # 3. Verify Health Check endpoint
    print("\n3. Testing /health endpoint...")
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json() == {"status": "ok"}
    print("Health check endpoint verified.")

    # 4. Verify Global Exception Handling
    print("\n4. Testing Global Exception Handler...")
    # Let's dynamically add a route that raises an unhandled error to verify the global exception handler
    @app.get("/test-unhandled-error")
    def trigger_error():
        return 1 / 0

    err_res = client.get("/test-unhandled-error")
    assert err_res.status_code == 500
    assert "internal server error" in err_res.json()["detail"].lower()

    # Verify exception traceback lands in errors.log
    with open("logs/errors.log", "r", encoding="utf-8") as f:
        errors_content = f.read()
        assert "ZeroDivisionError" in errors_content
        assert "Global unhandled exception" in errors_content

    print("Global unhandled exception handler successfully captures stack traces and sanitizes API responses.")
    print("\nAll Sprint 6 operational tests completed successfully!")

if __name__ == "__main__":
    test_sprint6_operations()
