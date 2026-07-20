import unittest
import time
import os
import sys
import uuid

# Dynamically include workspace root in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.db.metadata_db import get_metadata_connection

client = TestClient(app)

class TestPriority2Enhancements(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Setup dummy connection credentials for test connection
        cls.username = f"testuser_{int(time.time())}"
        cls.email = f"{cls.username}@example.com"
        cls.password = "SecurePassword123!"
        
    def test_01_registration_and_refresh_token(self):
        # 1. Register new user
        reg_payload = {
            "username": self.username,
            "email": self.email,
            "password": self.password
        }
        res = client.post("/auth/register", json=reg_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertIn("user", data)
        
        refresh_token_1 = data["refresh_token"]
        self.user_id = data["user"]["id"]
        
        # 2. Refresh the token
        refresh_payload = {
            "refresh_token": refresh_token_1
        }
        res_ref = client.post("/auth/refresh", json=refresh_payload)
        self.assertEqual(res_ref.status_code, 200)
        ref_data = res_ref.json()
        
        self.assertIn("access_token", ref_data)
        self.assertIn("refresh_token", ref_data)
        self.assertNotEqual(refresh_token_1, ref_data["refresh_token"])
        
    def test_02_disconnect_connection(self):
        # Register and login to get auth token
        login_res = client.post("/auth/login", json={"username": self.username, "password": self.password})
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Setup active connection parameters in DB
        conn_payload = {
            "db_type": "postgres",
            "host": "localhost",
            "port": 5432,
            "database": "ai_database_assistant",
            "username": "ai_readonly",
            "password": "readonly123"
        }
        
        # Verify test-connection is authenticated
        res_test = client.post("/test-connection", json=conn_payload, headers=headers)
        self.assertEqual(res_test.status_code, 200)
        
        # Disconnect
        res_disc = client.post("/disconnect", headers=headers)
        self.assertEqual(res_disc.status_code, 200)
        self.assertIn("Disconnected", res_disc.json()["message"])
        
        # Verify database connection parameters are removed for this user
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM user_connections WHERE user_id = (SELECT id FROM users WHERE username = ?)", (self.username,))
        self.assertIsNone(cur.fetchone())
        cur.close()
        conn.close()

    def test_03_pagination(self):
        # Register and login
        login_res = client.post("/auth/login", json={"username": self.username, "password": self.password})
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Seed query logs manually for pagination test
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = ?", (self.username,))
        user_id = cur.fetchone()[0]
        
        for i in range(5):
            cur.execute("""
                INSERT INTO query_logs (question, generated_sql, success, user_id)
                VALUES (?, ?, 1, ?)
            """, (f"Paginated Question {i}", "SELECT 1;", user_id))
        conn.commit()
        cur.close()
        conn.close()
        
        # Fetch with limit=2, offset=1
        res = client.get("/history?limit=2&offset=1", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["question"], "Paginated Question 3")
        self.assertEqual(data[1]["question"], "Paginated Question 2")

    def test_04_query_caching(self):
        # Login
        login_res = client.post("/auth/login", json={"username": self.username, "password": self.password})
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Establish connection first
        conn_payload = {
            "db_type": "postgres",
            "host": "localhost",
            "port": 5432,
            "database": "ai_database_assistant",
            "username": "ai_readonly",
            "password": "readonly123"
        }
        client.post("/test-connection", json=conn_payload, headers=headers)
        
        # Set up a mock cached entry directly to guarantee a hit
        import hashlib
        import json
        question = "show payments for room 1"
        q_hash = hashlib.sha256(question.strip().lower().encode('utf-8')).hexdigest()
        
        from app.services.schema_service import get_schema_hash
        try:
            s_hash = get_schema_hash()
        except Exception:
            s_hash = "unknown"
            
        dummy_result = {
            "question": question,
            "generated_sql": "SELECT * FROM payments WHERE room_id = 1",
            "execution_time_ms": 10,
            "data": [{"id": 1, "amount": 1200}],
            "insights": ["Insight 1"],
            "kpis": [],
            "show_chart": False,
            "chart_type": None,
            "chart_data": {},
            "explanation": "Explanation test"
        }
        
        from app.db.metadata_db import cache_query
        cache_query(q_hash, s_hash, dummy_result["generated_sql"], json.dumps(dummy_result))
        
        # Call /ask and verify it hits cache (returns dummy result instantly)
        res = client.post("/ask", json={"question": question}, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertEqual(data["generated_sql"], dummy_result["generated_sql"])
        self.assertEqual(data["data"], dummy_result["data"])
        self.assertEqual(data["explanation"], dummy_result["explanation"])

    def test_05_admin_audit_trail_export(self):
        # 1. Access without admin should be blocked
        login_res = client.post("/auth/login", json={"username": self.username, "password": self.password})
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        res_block = client.get("/admin/audit-trail/export", headers=headers)
        self.assertEqual(res_block.status_code, 403)
        
        # 2. Access with admin should succeed
        # Create an admin user first
        conn = get_metadata_connection()
        cur = conn.cursor()
        # Ensure admin exists
        from app.services.auth_service import hash_password
        try:
            cur.execute(
                "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 1)",
                ("testadmin", "admin@test.com", hash_password("AdminPassword123!"))
            )
            conn.commit()
        except Exception:
            pass # Admin already exists
        cur.close()
        conn.close()
        
        admin_login = client.post("/auth/login", json={"username": "testadmin", "password": "AdminPassword123!"})
        self.assertEqual(admin_login.status_code, 200)
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Fetch audit trail export
        res_export = client.get("/admin/audit-trail/export", headers=admin_headers)
        self.assertEqual(res_export.status_code, 200)
        self.assertIn("text/csv", res_export.headers["content-type"])
        self.assertIn("attachment", res_export.headers["content-disposition"])
        self.assertIn("ID,Event Type,Username,Client IP,Details,Timestamp", res_export.text)

if __name__ == "__main__":
    unittest.main()
