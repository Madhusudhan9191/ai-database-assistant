import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Bootstrap app import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.sql_repair_service import repair_sql, fix_postgresql_timestampdiff
from app.services.relationship_service import get_relationships

class TestAISQL(unittest.TestCase):

    def test_fix_postgresql_timestampdiff_basic_units(self):
        # Year diff translation
        sql = "SELECT TIMESTAMPDIFF(YEAR, start_date, end_date) AS diff FROM users"
        expected = "SELECT EXTRACT(YEAR FROM AGE(end_date, start_date)) AS diff FROM users"
        self.assertEqual(fix_postgresql_timestampdiff(sql), expected)

        # Day diff translation
        sql = "SELECT TIMESTAMPDIFF(day, start_date, end_date) FROM users"
        expected = "SELECT (end_date::date - start_date::date) FROM users"
        self.assertEqual(fix_postgresql_timestampdiff(sql), expected)

        # Minute diff translation
        sql = "SELECT TIMESTAMPDIFF(mi, start_date, end_date) FROM users"
        expected = "SELECT (EXTRACT(EPOCH FROM (end_date - start_date)) / 60) FROM users"
        self.assertEqual(fix_postgresql_timestampdiff(sql), expected)

        # Unrecognized fallback unit
        sql = "SELECT TIMESTAMPDIFF(HALLUCINATED_UNIT, start_date, end_date) FROM users"
        expected = "SELECT EXTRACT(YEAR FROM AGE(end_date, start_date)) FROM users"
        self.assertEqual(fix_postgresql_timestampdiff(sql), expected)

    def test_fix_postgresql_timestampdiff_nested_parentheses(self):
        # Nested function arguments (e.g. NOW(), intervals)
        sql = "SELECT TIMESTAMPDIFF(day, NOW(), DATE_ADD(created_at, INTERVAL '5' DAY)) FROM properties"
        expected = "SELECT (DATE_ADD(created_at, INTERVAL '5' DAY)::date - NOW()::date) FROM properties"
        self.assertEqual(fix_postgresql_timestampdiff(sql), expected)

    def test_fix_postgresql_timestampdiff_case_insensitivity(self):
        # Mixed case keyword
        sql = "SELECT TimeStampDiff(Year, t1.created, t2.updated) FROM events"
        expected = "SELECT EXTRACT(YEAR FROM AGE(t2.updated, t1.created)) FROM events"
        self.assertEqual(fix_postgresql_timestampdiff(sql), expected)

    @patch("app.services.sql_repair_service.get_relationships")
    @patch("app.services.sql_repair_service.get_db_type")
    @patch("app.services.sql_repair_service.get_database_schema")
    @patch("app.core.ai_client.client.chat.completions.create")
    def test_repair_sql_llm_invocation(self, mock_create, mock_schema, mock_db_type, mock_rels):
        # Mock dependencies
        mock_db_type.return_value = "postgres"
        mock_schema.return_value = "CREATE TABLE users (id int, name text);"
        mock_rels.return_value = "bookings:\n  room_id -> rooms.id"
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        # LLM returns postgres syntax with TIMESTAMPDIFF which needs post-processing repair
        mock_response.choices[0].message.content = "```sql\nSELECT TIMESTAMPDIFF(day, t1, t2);\n```"
        mock_create.return_value = mock_response

        repaired = repair_sql(
            question="how many days between dates",
            failed_sql="SELECT TIMESTAMPDIFF(day, t1, t2);",
            error_message="operator does not exist: timestampdiff"
        )
        # Semicolon removed, TIMESTAMPDIFF replaced by postgres subtract format
        self.assertEqual(repaired, "SELECT (t2::date - t1::date)")

    @patch("app.services.relationship_service.get_db_type")
    @patch("app.services.relationship_service.get_connection")
    def test_relationship_service_joins(self, mock_conn, mock_db_type):
        mock_db_type.return_value = "postgres"
        
        # Mock cursor and connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("bookings", "room_id", "rooms", "id"),
            ("bookings", "user_id", "users", "id")
        ]
        mock_conn.return_value.cursor.return_value = mock_cursor

        relationships = get_relationships()
        self.assertIn("bookings:", relationships)
        self.assertIn("room_id -> rooms.id", relationships)
        self.assertIn("user_id -> users.id", relationships)

if __name__ == "__main__":
    unittest.main()
