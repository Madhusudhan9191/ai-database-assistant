import unittest
import os
import sys
import time
from fastapi.testclient import TestClient

# Bootstrap app import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.rate_limiter import login_limiter, ask_limiter, check_lockout, register_failed_login, reset_failed_logins
from app.db.metadata_db import get_metadata_connection

client = TestClient(app)

class TestAuth(unittest.TestCase):

    def setUp(self):
        import uuid
        from app.db.connection_store import active_connection
        # Reset connection context
        active_connection.clear()
        active_connection.update({
            "db_type": None,
            "host": None,
            "port": None,
            "database": None,
            "username": None,
            "password": None,
        })
        uid = uuid.uuid4().hex[:10]
        self.username = f"authuser_{uid}"
        self.email = f"{self.username}@example.com"
        self.password = "StrongPass123!"

    def tearDown(self):
        # Reset rate limiters and lockouts to keep environment clean
        login_limiter.history.clear()
        ask_limiter.history.clear()
        reset_failed_logins(self.username)

    def test_registration_validation(self):
        # 1. Invalid Email
        payload_bad_email = {
            "username": self.username,
            "email": "invalid_email_format",
            "password": self.password
        }
        res = client.post("/auth/register", json=payload_bad_email)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid email", res.json()["detail"])

        # 2. Too Short Password
        payload_short_pass = {
            "username": self.username,
            "email": self.email,
            "password": "Short1!"
        }
        res = client.post("/auth/register", json=payload_short_pass)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Password must be at least 8 characters", res.json()["detail"])

        # 3. Missing Uppercase
        payload_no_upper = {
            "username": self.username,
            "email": self.email,
            "password": "weakpassword123!"
        }
        res = client.post("/auth/register", json=payload_no_upper)
        self.assertEqual(res.status_code, 400)

        # 4. Valid Registration
        payload_valid = {
            "username": self.username,
            "email": self.email,
            "password": self.password
        }
        res = client.post("/auth/register", json=payload_valid)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    def test_login_and_token_refresh(self):
        # Register user first
        reg_payload = {"username": self.username, "email": self.email, "password": self.password}
        client.post("/auth/register", json=reg_payload)

        # 1. Successful Login
        login_payload = {"username": self.username, "password": self.password}
        res = client.post("/auth/login", json=login_payload)
        self.assertEqual(res.status_code, 200)
        tokens = res.json()
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)
        
        refresh_token = tokens["refresh_token"]

        # 2. Refresh Token Rotation
        res_ref = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        self.assertEqual(res_ref.status_code, 200)
        rotated_tokens = res_ref.json()
        self.assertIn("access_token", rotated_tokens)
        self.assertIn("refresh_token", rotated_tokens)
        self.assertNotEqual(refresh_token, rotated_tokens["refresh_token"])

    def test_account_lockout_logic(self):
        username = self.username.lower()
        
        # Verify initially not locked
        is_locked, _ = check_lockout(username)
        self.assertFalse(is_locked)

        # Fail 4 times
        for _ in range(4):
            newly_locked = register_failed_login(username)
            self.assertFalse(newly_locked)
            
        # 5th failure triggers lockout
        newly_locked = register_failed_login(username)
        self.assertTrue(newly_locked)

        # Verify locked out
        is_locked, remaining = check_lockout(username)
        self.assertTrue(is_locked)
        self.assertTrue(remaining > 0)

        # Reset and verify unlocked
        reset_failed_logins(username)
        is_locked, _ = check_lockout(username)
        self.assertFalse(is_locked)

    def test_sliding_window_rate_limiter(self):
        # test client IP sliding-window
        ip = "192.168.1.100"
        
        # First 10 requests pass
        for _ in range(10):
            self.assertFalse(login_limiter.is_rate_limited(ip))
            
        # 11th is rate limited
        self.assertTrue(login_limiter.is_rate_limited(ip))

if __name__ == "__main__":
    unittest.main()
