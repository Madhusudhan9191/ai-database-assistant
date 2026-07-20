import unittest
import os
import sys
import time
from fastapi.testclient import TestClient

# Bootstrap app import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.services.query_validator import validate_sql
from app.services.auth_service import create_access_token, hash_password
from app.db.metadata_db import get_metadata_connection
from datetime import timedelta
from fastapi import HTTPException

client = TestClient(app)

class TestSecurity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import uuid
        from app.db.connection_store import active_connection
        # Reset connection context to prevent state leakage from other tests
        active_connection.clear()
        active_connection.update({
            "db_type": None,
            "host": None,
            "port": None,
            "database": None,
            "username": None,
            "password": None,
        })

        # Create users for testing multi-tenant isolation
        uid = uuid.uuid4().hex[:10]
        cls.username_a = f"usera_{uid}"
        cls.username_b = f"userb_{uid}"
        
        cls.email_a = f"{cls.username_a}@example.com"
        cls.email_b = f"{cls.username_b}@example.com"
        
        cls.password = "SecurePassword123!"
        
        # Insert users into DB
        conn = get_metadata_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 0)",
            (cls.username_a, cls.email_a, hash_password(cls.password))
        )
        cls.user_a_id = cur.lastrowid
        
        cur.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, 0)",
            (cls.username_b, cls.email_b, hash_password(cls.password))
        )
        cls.user_b_id = cur.lastrowid
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Create tokens
        cls.token_a = create_access_token({"user_id": cls.user_a_id, "username": cls.username_a})
        cls.token_b = create_access_token({"user_id": cls.user_b_id, "username": cls.username_b})

    def test_sql_validator_safe_queries(self):
        # Valid queries should pass
        self.assertTrue(validate_sql("SELECT * FROM users"))
        self.assertTrue(validate_sql("WITH cte AS (SELECT 1 AS val) SELECT * FROM cte"))
        self.assertTrue(validate_sql("SELECT name FROM properties WHERE id = 'some-id'"))
        self.assertTrue(validate_sql("SELECT count(*) FROM maintenance WHERE status = 'open';"))

    def test_sql_validator_dangerous_keywords(self):
        # Dangerous actions should raise HTTPException
        dangerous_queries = [
            "DROP TABLE users",
            "DELETE FROM properties",
            "UPDATE contracts SET price = 100",
            "INSERT INTO users (username) VALUES ('hacker')",
            "TRUNCATE TABLE logs",
            "ALTER TABLE users ADD COLUMN is_admin INTEGER",
            "GRANT ALL PRIVILEGES ON db TO hacker",
            "EXECUTE IMMEDIATE 'DROP TABLE users'"
        ]
        for query in dangerous_queries:
            with self.assertRaises(HTTPException) as ctx:
                validate_sql(query)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertTrue(
                "Forbidden SQL operation" in ctx.exception.detail or
                "Only SELECT queries are allowed" in ctx.exception.detail
            )

    def test_sql_validator_sql_injection_patterns(self):
        # SQL injection payloads should raise HTTPException
        payloads = [
            "SELECT * FROM users WHERE username = 'admin' OR 1=1 -- ",
            "SELECT * FROM users; DROP TABLE properties;",
            "SELECT * FROM users UNION ALL SELECT username, password FROM information_schema.columns -- ",
            "SELECT * FROM rooms WHERE id = 1 AND SLEEP(5)",
            "SELECT * FROM rooms WHERE id = 1 AND PG_SLEEP(5)"
        ]
        for payload in payloads:
            with self.assertRaises(HTTPException) as ctx:
                validate_sql(payload)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertTrue(
                "Suspicious SQL pattern" in ctx.exception.detail or
                "Forbidden SQL operation" in ctx.exception.detail or
                "Multiple SQL statements" in ctx.exception.detail or
                "Only SELECT queries are allowed" in ctx.exception.detail
            )

    def test_sql_validator_limits(self):
        # Limit checking: length
        long_query = "SELECT * FROM users WHERE id IN (" + ",".join([str(i) for i in range(1000)]) + ")"
        self.assertTrue(validate_sql(long_query))  # under 5000 chars
        
        too_long_query = "SELECT * FROM users WHERE name = '" + "A"*5000 + "'"
        with self.assertRaises(HTTPException) as ctx:
            validate_sql(too_long_query)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Query too long", ctx.exception.detail)
        
        # Limit checking: depth
        nested_query = "SELECT * FROM (" * 11 + "SELECT 1" + ")" * 11
        with self.assertRaises(HTTPException) as ctx:
            validate_sql(nested_query)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Query too complex", ctx.exception.detail)

    def test_jwt_missing_token(self):
        # Request a protected endpoint without auth header
        res = client.get("/history")
        self.assertEqual(res.status_code, 401)  # HTTPBearer returns 401 for missing credentials

    def test_jwt_invalid_signature_and_format(self):
        # Request with malformed headers
        headers = {"Authorization": "Bearer invalid_token_xyz"}
        res = client.get("/history", headers=headers)
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid or expired session token", res.json()["detail"])

        headers = {"Authorization": "Bearer " + self.token_a + "extra_chars_to_break_signature"}
        res = client.get("/history", headers=headers)
        self.assertEqual(res.status_code, 401)

    def test_jwt_expired_token(self):
        # Create an expired token
        expired_token = create_access_token(
            {"user_id": self.user_a_id, "username": self.username_a},
            expires_delta=timedelta(seconds=-10)
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        res = client.get("/history", headers=headers)
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid or expired session token", res.json()["detail"])

    def test_multi_tenant_isolation(self):
        # User A inserts a query log manually
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO query_logs (question, generated_sql, success, user_id)
            VALUES (?, ?, 1, ?)
        """, ("User A private question", "SELECT * FROM users WHERE id = 1", self.user_a_id))
        user_a_log_id = cur.lastrowid
        
        # User A inserts a favorite query
        cur.execute("""
            INSERT INTO favorites (question, generated_sql, database_type, database_name, schema_hash, user_id)
            VALUES (?, ?, 'sqlite', 'test.db', 'schema123', ?)
        """, ("User A favorite question", "SELECT 1", self.user_a_id))
        user_a_fav_id = cur.lastrowid

        # User A inserts a saved report
        cur.execute("""
            INSERT INTO saved_reports (report_name, question, generated_sql, chart_type, database_type, database_name, schema_hash, user_id)
            VALUES (?, ?, ?, 'bar', 'sqlite', 'test.db', 'schema123', ?)
        """, ("User A report", "User A report question", "SELECT 2", self.user_a_id))
        user_a_rep_id = cur.lastrowid
        
        conn.commit()
        cur.close()
        conn.close()

        # 1. Verify User B cannot fetch User A's history logs
        headers_b = {"Authorization": f"Bearer {self.token_b}"}
        res = client.get("/history", headers=headers_b)
        self.assertEqual(res.status_code, 200)
        history_b = res.json()
        # Verify none of User B's fetched history corresponds to User A's log
        for item in history_b:
            self.assertNotEqual(item["id"], user_a_log_id)
            self.assertNotEqual(item["question"], "User A private question")

        # 2. Verify User B cannot delete User A's history log
        res = client.delete(f"/history/{user_a_log_id}", headers=headers_b)
        self.assertEqual(res.status_code, 404)  # returns 404 when log not found for current user

        # 3. Verify User B cannot fetch User A's favorites
        res = client.get("/favorites", headers=headers_b)
        self.assertEqual(res.status_code, 200)
        favs_b = res.json()
        for item in favs_b:
            self.assertNotEqual(item["id"], user_a_fav_id)
            self.assertNotEqual(item["question"], "User A favorite question")

        # 4. Verify User B cannot delete User A's favorite
        res = client.delete(f"/favorites/{user_a_fav_id}", headers=headers_b)
        self.assertEqual(res.status_code, 400) # returns 400 Bad Request on delete failure

        # 5. Verify User B cannot fetch User A's reports
        res = client.get("/saved-reports", headers=headers_b)
        self.assertEqual(res.status_code, 200)
        reports_b = res.json()
        for item in reports_b:
            self.assertNotEqual(item["id"], user_a_rep_id)
            self.assertNotEqual(item["report_name"], "User A report")

        # 6. Verify User B cannot delete User A's report
        res = client.delete(f"/saved-reports/{user_a_rep_id}", headers=headers_b)
        self.assertEqual(res.status_code, 400) # returns 400 Bad Request on delete failure

if __name__ == "__main__":
    unittest.main()
