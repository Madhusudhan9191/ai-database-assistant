import unittest
import os
import sys
import hashlib
import json
import time

# Bootstrap app import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.metadata_db import (
    get_metadata_connection,
    cache_query,
    get_cached_query,
    clear_expired_cache
)

class TestCache(unittest.TestCase):

    def setUp(self):
        # Generate unique hashes for tests to avoid collision
        self.question = f"test question {time.time()}"
        self.q_hash = hashlib.sha256(self.question.encode("utf-8")).hexdigest()
        self.s_hash = "schema_hash_123"
        self.sql = "SELECT 1"
        self.result = {"data": [1, 2, 3]}

    def test_cache_lifecycle_save_and_retrieve(self):
        # 1. Miss initially
        cached = get_cached_query(self.q_hash, self.s_hash)
        self.assertIsNone(cached)

        # 2. Save cache
        cache_query(self.q_hash, self.s_hash, self.sql, json.dumps(self.result))

        # 3. Hit
        cached = get_cached_query(self.q_hash, self.s_hash)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["generated_sql"], self.sql)
        self.assertEqual(json.loads(cached["result_json"]), self.result)

    def test_cache_ttl_expiration(self):
        # 1. Insert entry that is current
        cache_query(self.q_hash, self.s_hash, self.sql, json.dumps(self.result))
        
        # 2. Insert entry that is in the past
        past_q_hash = self.q_hash + "_past"
        cache_query(past_q_hash, self.s_hash, self.sql, json.dumps(self.result))
        
        # Modify the created_at field manually in SQLite to simulate it being older (e.g. 20 minutes ago)
        conn = get_metadata_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE query_cache SET created_at = datetime('now', '-20 minutes') WHERE question_hash = ?",
            (past_q_hash,)
        )
        conn.commit()
        cur.close()
        conn.close()

        # 3. Call expiration clear with TTL = 10 minutes (600 seconds)
        clear_expired_cache(600)

        # 4. Verify the past entry is cleared and the current one remains
        self.assertIsNone(get_cached_query(past_q_hash, self.s_hash))
        self.assertIsNotNone(get_cached_query(self.q_hash, self.s_hash))

if __name__ == "__main__":
    unittest.main()
