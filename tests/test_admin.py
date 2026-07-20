import unittest
import os
import sys
import time
from fastapi.testclient import TestClient

# Bootstrap app import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.services.auth_service import create_access_token, hash_password
from app.db.metadata_db import get_metadata_connection

client = TestClient(app)

class TestAdmin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
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

        # Set up a regular user and an admin user
        uid = uuid.uuid4().hex[:10]
        cls.username_user = f"regular_{uid}"
        cls.username_admin = f"admin_{uid}"
        
        cls.email_user = f"{cls.username_user}@example.com"
        cls.email_admin = f"{cls.username_admin}@example.com"
        
        cls.password = "AdminPass123!"

        # Write to SQLite
        conn = get_metadata_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 0)",
            (cls.username_user, cls.email_user, hash_password(cls.password))
        )
        cls.user_id = cur.lastrowid
        
        cur.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 1)",
            (cls.username_admin, cls.email_admin, hash_password(cls.password))
        )
        cls.admin_id = cur.lastrowid
        
        # Log a security event manually to populate the export log
        cur.execute(
            "INSERT INTO security_events (event_type, username, client_ip, details) VALUES (?, ?, ?, ?)",
            ("TEST_EVENT", cls.username_user, "127.0.0.1", "Sample audit detail entry")
        )
        
        conn.commit()
        cur.close()
        conn.close()

        # Create JWTs
        cls.token_user = create_access_token({"user_id": cls.user_id, "username": cls.username_user})
        cls.token_admin = create_access_token({"user_id": cls.admin_id, "username": cls.username_admin})

    def test_admin_stats_authorization(self):
        # 1. Non-admin request blocked
        headers_user = {"Authorization": f"Bearer {self.token_user}"}
        res = client.get("/admin/stats", headers=headers_user)
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["detail"], "Admin access required")

        # 2. Admin request permitted
        headers_admin = {"Authorization": f"Bearer {self.token_admin}"}
        res = client.get("/admin/stats", headers=headers_admin)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        # Verify structure keys
        self.assertIn("total_users", data)
        self.assertIn("total_queries", data)
        self.assertIn("failed_queries", data)
        self.assertIn("repair_attempts", data)

    def test_admin_audit_trail_export_authorization(self):
        # 1. Non-admin request blocked
        headers_user = {"Authorization": f"Bearer {self.token_user}"}
        res = client.get("/admin/audit-trail/export", headers=headers_user)
        self.assertEqual(res.status_code, 403)

        # 2. Admin request permitted
        headers_admin = {"Authorization": f"Bearer {self.token_admin}"}
        res = client.get("/admin/audit-trail/export", headers=headers_admin)
        self.assertEqual(res.status_code, 200)
        
        # Verify headers and content
        self.assertIn("text/csv", res.headers["content-type"])
        self.assertIn("attachment", res.headers["content-disposition"])
        csv_text = res.text
        self.assertIn("ID,Event Type,Username,Client IP,Details,Timestamp", csv_text)
        self.assertIn("TEST_EVENT", csv_text)
        self.assertIn("Sample audit detail entry", csv_text)

if __name__ == "__main__":
    unittest.main()
