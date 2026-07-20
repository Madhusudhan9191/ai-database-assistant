import unittest
import contextvars
import asyncio
import threading
import os
import sys
import time
from fastapi.testclient import TestClient

# Bootstrap app import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.connection_store import active_connection, active_connection_ctx
from app.services.auth_service import create_access_token, hash_password
from app.db.metadata_db import get_metadata_connection, get_user_connection

client = TestClient(app)

class TestConnections(unittest.TestCase):

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
        cls.username = f"connuser_{uid}"
        cls.email = f"{cls.username}@example.com"
        cls.password = "ConnectionPass123!"

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

    def test_connection_contextvar_concurrency(self):
        # 1. Test thread isolation of contextvars
        def thread_task(db_type_val, output_list):
            # Set the contextvar inside the thread
            active_connection_ctx.set({"db_type": db_type_val})
            time.sleep(0.05) # Wait to allow context switches / concurrent executions
            output_list.append(active_connection["db_type"])

        outputs = []
        t1 = threading.Thread(target=thread_task, args=("postgres", outputs))
        t2 = threading.Thread(target=thread_task, args=("oracle", outputs))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Both values should be correctly read by respective threads without overlap/leakage
        self.assertIn("postgres", outputs)
        self.assertIn("oracle", outputs)

        # 2. Test async context isolation of contextvars
        async def async_task(db_type_val):
            active_connection_ctx.set({"db_type": db_type_val})
            await asyncio.sleep(0.02)
            return active_connection["db_type"]

        async def run_async():
            return await asyncio.gather(
                async_task("mysql"),
                async_task("sqlite")
            )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_async())
        loop.close()

        self.assertEqual(results, ["mysql", "sqlite"])

    def test_test_connection_and_disconnect_endpoints(self):
        # 1. POST /test-connection
        conn_payload = {
            "db_type": "postgres",
            "host": "localhost",
            "port": 5432,
            "database": "ai_database_assistant",
            "username": "ai_readonly",
            "password": "readonly123"
        }
        res = client.post("/test-connection", json=conn_payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["message"], "Connection successful")

        # Verify cached connection values inside metadata database
        cached = get_user_connection(self.user_id)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["db_type"], "postgres")
        self.assertEqual(cached["username"], "ai_readonly")

        # 2. POST /disconnect
        res_disc = client.post("/disconnect", headers=self.headers)
        self.assertEqual(res_disc.status_code, 200)
        self.assertIn("Disconnected", res_disc.json()["message"])

        # Verify connection credentials are deleted from metadata database
        self.assertIsNone(get_user_connection(self.user_id))

if __name__ == "__main__":
    unittest.main()
