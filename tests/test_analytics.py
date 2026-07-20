import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Bootstrap app import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.trend_detection import detect_trends
from app.services.chart_decision_service import get_chart_decision, _validate_and_sanitize_chart

class TestAnalytics(unittest.TestCase):

    def test_trend_detection_empty_data(self):
        # Test empty list and non-list cases
        self.assertEqual(detect_trends([]), {"summary": "No data to analyze."})
        self.assertEqual(detect_trends(None), {"summary": "No data to analyze."})
        self.assertEqual(detect_trends("not a list"), {"summary": "No data to analyze."})

    def test_trend_detection_growth_and_decline(self):
        # 1. Growth trend
        growth_data = [
            {"val": 10}, {"val": 20}, {"val": 30}, {"val": 40}, {"val": 50}
        ]
        res = detect_trends(growth_data)
        self.assertEqual(res["row_count"], 5)
        # Check that growth was detected
        trends = res["numeric_trends"]
        self.assertTrue(any("GROWTH" in t for t in trends))

        # 2. Decline trend
        decline_data = [
            {"val": 100}, {"val": 80}, {"val": 60}, {"val": 40}, {"val": 20}
        ]
        res = detect_trends(decline_data)
        trends = res["numeric_trends"]
        self.assertTrue(any("DECLINE" in t for t in trends))

    def test_trend_detection_outliers(self):
        # Outlier check using IQR (requires at least 4 items)
        data = [
            {"val": 10}, {"val": 11}, {"val": 10}, {"val": 12}, 
            {"val": 11}, {"val": 10}, {"val": 1000}
        ]
        res = detect_trends(data)
        outliers = res["outliers"]
        self.assertTrue(len(outliers) > 0)
        self.assertTrue(any("1,000" in o or "1000" in o for o in outliers))

    def test_trend_detection_concentration_risk(self):
        # Concentration risk: single top element dominates
        data = [
            {"val": 900}, {"val": 50}, {"val": 50}
        ]
        res = detect_trends(data)
        patterns = res["patterns"]
        self.assertTrue(any("CONCENTRATION RISK" in p for p in patterns))

    def test_trend_detection_time_based(self):
        # Combined date/time trend
        data = [
            {"date": "2026-01-01", "val": 10},
            {"date": "2026-01-02", "val": 20},
            {"date": "2026-01-03", "val": 30},
            {"date": "2026-01-04", "val": 40}
        ]
        res = detect_trends(data)
        trends = res["numeric_trends"]
        self.assertTrue(any("Consistent UPWARD" in t for t in trends))

    def test_chart_decision_heuristics_time_series(self):
        # Heuristics: Has time and > 8 rows -> Area
        data_large_time = [
            {"date": f"2026-06-{i:02d}", "val": i * 10} for i in range(1, 10)
        ]
        decision = get_chart_decision("show daily trend", data_large_time)
        self.assertTrue(decision["show_chart"])
        self.assertEqual(decision["chart_type"], "area")

        # Heuristics: Has time and <= 8 rows -> Line
        data_small_time = [
            {"date": f"2026-06-{i:02d}", "val": i * 10} for i in range(1, 5)
        ]
        decision = get_chart_decision("show daily trend", data_small_time)
        self.assertTrue(decision["show_chart"])
        self.assertEqual(decision["chart_type"], "line")

    def test_chart_decision_heuristics_distribution(self):
        # Distribution: 2-6 categories, numeric positive -> Pie
        data_pie = [
            {"category": "Rent", "val": 2000},
            {"category": "Bills", "val": 500},
            {"category": "Salary", "val": 4000}
        ]
        decision = get_chart_decision("show expense share", data_pie)
        self.assertTrue(decision["show_chart"])
        self.assertEqual(decision["chart_type"], "pie")

    def test_chart_decision_sanitization_rules(self):
        # Rule 1: No numeric cols -> none
        no_num_data = [{"name": "alice"}, {"name": "bob"}]
        self.assertEqual(
            _validate_and_sanitize_chart({"show_chart": True, "chart_type": "bar"}, no_num_data),
            {"show_chart": False, "chart_type": "none"}
        )

        # Rule 2: Single record with <= 1 numeric column -> none
        single_record = [{"name": "alice", "val": 100}]
        self.assertEqual(
            _validate_and_sanitize_chart({"show_chart": True, "chart_type": "bar"}, single_record),
            {"show_chart": False, "chart_type": "none"}
        )

        # Rule 3: Pie chart demoted to bar if rows > 8 or < 2
        too_many_rows_for_pie = [{"cat": f"Cat{i}", "val": i} for i in range(10)]
        res = _validate_and_sanitize_chart({"show_chart": True, "chart_type": "pie"}, too_many_rows_for_pie)
        self.assertTrue(res["show_chart"])
        self.assertEqual(res["chart_type"], "bar")

        # Rule 4: Scatter demoted if numeric cols < 2
        scatter_data = [{"cat": "A", "val": 10}, {"cat": "B", "val": 20}]
        res = _validate_and_sanitize_chart({"show_chart": True, "chart_type": "scatter"}, scatter_data)
        self.assertEqual(res["chart_type"], "bar")

        # Rule 5: Line and Area demoted to bar if no temporal columns
        no_time_data = [{"cat": "A", "val1": 10, "val2": 20}, {"cat": "B", "val1": 20, "val2": 30}]
        res = _validate_and_sanitize_chart({"show_chart": True, "chart_type": "line"}, no_time_data)
        self.assertEqual(res["chart_type"], "bar")

    @patch("app.core.ai_client.client.chat.completions.create")
    def test_chart_decision_ai_fallback(self, mock_create):
        # AI decision mocks for ambiguous cases
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        # Mock LLM returns bar decision
        mock_response.choices[0].message.content = '{"show_chart": true, "chart_type": "bar"}'
        mock_create.return_value = mock_response

        # Ambiguous categories data (more than 6 rows, no time field)
        data = [{"cat": f"Cat{i}", "val": i} for i in range(7)]
        decision = get_chart_decision("compare values", data)
        self.assertTrue(decision["show_chart"])
        self.assertEqual(decision["chart_type"], "bar")

if __name__ == "__main__":
    unittest.main()
