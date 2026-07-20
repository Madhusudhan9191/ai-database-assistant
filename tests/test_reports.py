import unittest
from unittest.mock import patch
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

@patch("app.services.schema_service.get_schema_hash")
class TestReports(unittest.TestCase):

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

        # Set up a test user
        uid = uuid.uuid4().hex[:10]
        cls.username = f"reportuser_{uid}"
        cls.email = f"{cls.username}@example.com"
        cls.password = "ReportPass123!"

        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 0)",
            (cls.username, cls.email, hash_password(cls.password))
        )
        cls.user_id = cur.lastrowid
        conn.commit()
        cur.close()
        conn.close()

        cls.token = create_access_token({"user_id": cls.user_id, "username": cls.username})
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_01_favorites_crud_and_pagination(self, mock_hash):
        mock_hash.return_value = "unknown"

        # 1. Add favorite via POST
        payload = {
            "question": "what is the query?",
            "generated_sql": "SELECT * FROM queries"
        }
        res = client.post("/favorites", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        fav_id = res.json()["id"]

        # 2. Get favorites list
        res = client.get("/favorites", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(len(data) > 0)
        self.assertEqual(data[0]["question"], "what is the query?")

        # 3. Seed additional items to test pagination
        conn = get_metadata_connection()
        cur = conn.cursor()
        for i in range(5):
            cur.execute("""
                INSERT INTO favorites (question, generated_sql, database_type, database_name, schema_hash, user_id)
                VALUES (?, ?, 'postgres', '', 'unknown', ?)
            """, (f"Paginated Favorite {i}", f"SELECT {i}", self.user_id))
        conn.commit()
        cur.close()
        conn.close()

        # Get favorites with limit=2, offset=1
        res = client.get("/favorites?limit=2&offset=1", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        paginated_data = res.json()
        self.assertEqual(len(paginated_data), 2)
        self.assertEqual(paginated_data[0]["question"], "Paginated Favorite 0")
        self.assertEqual(paginated_data[1]["question"], "Paginated Favorite 1")

        # 4. Delete favorite
        res = client.delete(f"/favorites/{fav_id}", headers=self.headers)
        self.assertEqual(res.status_code, 200)

    def test_02_saved_reports_crud_and_pagination(self, mock_hash):
        mock_hash.return_value = "unknown"

        # 1. Add report via POST
        payload = {
            "report_name": "Test Report",
            "question": "show me test data",
            "generated_sql": "SELECT 1",
            "chart_type": "bar"
        }
        res = client.post("/saved-reports", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        report_id = res.json()["id"]

        # 2. Get reports list
        res = client.get("/saved-reports", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(len(data) > 0)
        self.assertEqual(data[0]["report_name"], "Test Report")

        # 3. Seed additional reports
        conn = get_metadata_connection()
        cur = conn.cursor()
        for i in range(5):
            cur.execute("""
                INSERT INTO saved_reports (report_name, question, generated_sql, chart_type, database_type, database_name, schema_hash, user_id)
                VALUES (?, ?, ?, 'bar', 'postgres', '', 'unknown', ?)
            """, (f"Paginated Report Name {i}", f"Paginated Report Question {i}", f"SELECT {i}", self.user_id))
        conn.commit()
        cur.close()
        conn.close()

        # Get reports with limit=2, offset=1
        res = client.get("/saved-reports?limit=2&offset=1", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        paginated_data = res.json()
        self.assertEqual(len(paginated_data), 2)
        self.assertEqual(paginated_data[0]["report_name"], "Paginated Report Name 0")
        self.assertEqual(paginated_data[1]["report_name"], "Paginated Report Name 1")

        # 4. Delete report
        res = client.delete(f"/saved-reports/{report_id}", headers=self.headers)
        self.assertEqual(res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
