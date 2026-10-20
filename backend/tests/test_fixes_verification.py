import os
import sys
import unittest
import json
import re

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database import query_one

class TestFixesVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_homepage_tagline_no_mysql(self):
        """Verify homepage tagline has been updated and contains no MySQL or DB references."""
        html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/index.html'))
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Must have the new clean tagline
        self.assertIn("AI-Powered Travel Decisions for Smarter Journeys", content)
        # Must NOT have the old MySQL claim
        self.assertNotIn("AI-Powered Travel Decisions Grounded in MySQL", content)

    def test_02_api_base_configuration(self):
        """Verify frontend api.js contains /api/v1 in remote production URL and sanitizes endpoints."""
        api_js_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/js/api.js'))
        with open(api_js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("https://flywise-0equ.onrender.com/api/v1", content)
        search_js_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/js/search.js'))
        with open(search_js_path, 'r', encoding='utf-8') as f:
            search_content = f.read()
        self.assertIn("window.openWhatIfSimulator", search_content)

    def test_03_what_if_date_simulator_endpoint(self):
        """Verify POST /api/v1/simulation/alternatives returns 7 days with live/estimated flags and fare diffs."""
        res = self.client.post('/api/v1/simulation/alternatives', json={
            "origin": "TIR",
            "destination": "DEL",
            "departure_date": "2026-10-23",
            "travel_class": "economy"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("origin"), "TIR")
        self.assertEqual(data.get("destination"), "DEL")
        self.assertEqual(data.get("travel_class"), "economy")
        self.assertIn("baseline_fare", data)
        self.assertIn("timeline", data)
        self.assertEqual(len(data["timeline"]), 7)

        # Check shifts -3 to +3
        shifts = [t["shift_days"] for t in data["timeline"]]
        self.assertEqual(shifts, [-3, -2, -1, 0, 1, 2, 3])

        for t in data["timeline"]:
            self.assertIn("fare_difference", t)
            self.assertIn("is_live_schedule", t)
            self.assertIn("price_type", t)
            self.assertIn("lowest_fare", t)
            self.assertIsInstance(t["lowest_fare"], (int, float))

    def test_04_ai_assistant_travel_query(self):
        """Verify AI assistant responds to flight query and grounds with itineraries."""
        res = self.client.post('/api/v1/assistant/chat', json={
            "message": "tirupati to delhi flights"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIsNotNone(data.get("reply"))
        self.assertTrue(len(data.get("reply")) > 20)
        self.assertIn("conversation_id", data)
        # Should have found matching flights between TIR and DEL
        self.assertIn("itineraries", data)
        self.assertTrue(len(data["itineraries"]) > 0)

    def test_05_ai_assistant_general_query(self):
        """Verify AI assistant responds to general knowledge questions."""
        res = self.client.post('/api/v1/assistant/chat', json={
            "message": "Why is the sky blue?"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIsNotNone(data.get("reply"))
        self.assertTrue(len(data.get("reply")) > 20)

    def test_06_health_and_db_connectivity(self):
        """Verify backend health endpoint reports DB connected."""
        res = self.client.get('/api/v1/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertTrue(data.get("database_connected"))

if __name__ == '__main__':
    unittest.main()
