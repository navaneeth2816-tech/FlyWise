import unittest
import requests
import pymysql
import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config

BASE_URL = "http://127.0.0.1:5000/api/v1"

class TestImprovements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Direct DB connection to verify hashing and clean up test data if needed
        cls.conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        # Remove any previous test user
        with cls.conn.cursor() as cur:
            cur.execute("DELETE FROM journeys WHERE user_id IN (SELECT user_id FROM users WHERE email = 'test_verify@flywise.com')")
            cur.execute("DELETE FROM bookings WHERE user_id IN (SELECT user_id FROM users WHERE email = 'test_verify@flywise.com')")
            cur.execute("DELETE FROM users WHERE email = 'test_verify@flywise.com'")

    @classmethod
    def tearDownClass(cls):
        with cls.conn.cursor() as cur:
            cur.execute("DELETE FROM journeys WHERE user_id IN (SELECT user_id FROM users WHERE email = 'test_verify@flywise.com')")
            cur.execute("DELETE FROM bookings WHERE user_id IN (SELECT user_id FROM users WHERE email = 'test_verify@flywise.com')")
            cur.execute("DELETE FROM users WHERE email = 'test_verify@flywise.com'")
        cls.conn.close()

    def test_01_registration_password_strength_enforcement(self):
        """Verify that weak passwords and mismatched confirm_passwords are rejected with 400."""
        # 1. Too short
        res = requests.post(f"{BASE_URL}/auth/register", json={
            "email": "test_verify@flywise.com",
            "full_name": "Test Verify User",
            "password": "Ab1!",
            "confirm_password": "Ab1!"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("at least 8 characters", res.json().get('message', '').lower())

        # 2. No uppercase
        res = requests.post(f"{BASE_URL}/auth/register", json={
            "email": "test_verify@flywise.com",
            "full_name": "Test Verify User",
            "password": "password@123",
            "confirm_password": "password@123"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("uppercase", res.json().get('message', '').lower())

        # 3. No special character
        res = requests.post(f"{BASE_URL}/auth/register", json={
            "email": "test_verify@flywise.com",
            "full_name": "Test Verify User",
            "password": "Password123",
            "confirm_password": "Password123"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("special character", res.json().get('message', '').lower())

        # 4. Mismatch
        res = requests.post(f"{BASE_URL}/auth/register", json={
            "email": "test_verify@flywise.com",
            "full_name": "Test Verify User",
            "password": "Password@2026!",
            "confirm_password": "Password@2026?mismatch"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("match", res.json().get('message', '').lower())

    def test_02_registration_success_and_hashing(self):
        """Verify successful registration with a strong password, secure password hashing in DB."""
        session = requests.Session()
        res = session.post(f"{BASE_URL}/auth/register", json={
            "email": "test_verify@flywise.com",
            "full_name": "Test Verify User",
            "phone": "+91 9988776655",
            "password": "Password@2026!",
            "confirm_password": "Password@2026!"
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertEqual(data['user']['full_name'], "Test Verify User")
        self.assertEqual(data['user']['email'], "test_verify@flywise.com")

        # Verify password is NOT stored as plaintext in MySQL
        with self.conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM users WHERE email = 'test_verify@flywise.com'")
            user_row = cur.fetchone()
            self.assertIsNotNone(user_row)
            stored_hash = user_row['password_hash']
            self.assertNotEqual(stored_hash, "Password@2026!")
            self.assertTrue(stored_hash.startswith("scrypt:") or stored_hash.startswith("pbkdf2:") or stored_hash.startswith("$2b$"))

    def test_03_login_and_user_profile(self):
        """Verify login with newly created account returns user details and sets session cookie."""
        session = requests.Session()
        res = session.post(f"{BASE_URL}/auth/login", json={
            "email": "test_verify@flywise.com",
            "password": "Password@2026!"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertEqual(data['user']['full_name'], "Test Verify User")
        self.assertEqual(data['user']['email'], "test_verify@flywise.com")

        # Verify /auth/me returns the logged-in profile
        me_res = session.get(f"{BASE_URL}/auth/me")
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.json()
        self.assertEqual(me_data.get('status'), 'authenticated')
        self.assertEqual(me_data['user']['full_name'], "Test Verify User")
        self.assertEqual(me_data['user']['email'], "test_verify@flywise.com")

    def test_04_user_dashboard_empty_state_and_existing_bookings(self):
        """Verify new user has empty bookings/journeys list ([]), and existing user has actual bookings."""
        # New user session
        new_session = requests.Session()
        new_session.post(f"{BASE_URL}/auth/login", json={
            "email": "test_verify@flywise.com",
            "password": "Password@2026!"
        })
        new_bookings_res = new_session.get(f"{BASE_URL}/bookings")
        self.assertEqual(new_bookings_res.status_code, 200)
        self.assertEqual(new_bookings_res.json().get('bookings'), [])

        new_journeys_res = new_session.get(f"{BASE_URL}/journeys")
        self.assertEqual(new_journeys_res.status_code, 200)
        self.assertEqual(new_journeys_res.json().get('journeys'), [])

        # Existing user session (Navaneeth)
        existing_session = requests.Session()
        existing_session.post(f"{BASE_URL}/auth/login", json={
            "email": "navaneeth@flywise.ai",
            "password": "Password@123"
        })
        existing_bookings_res = existing_session.get(f"{BASE_URL}/bookings")
        self.assertEqual(existing_bookings_res.status_code, 200)
        bookings = existing_bookings_res.json().get('bookings')
        self.assertIsInstance(bookings, list)
        self.assertGreaterEqual(len(bookings), 1)
        self.assertIn("booking_reference", bookings[0])

        existing_journeys_res = existing_session.get(f"{BASE_URL}/journeys")
        self.assertEqual(existing_journeys_res.status_code, 200)
        journeys = existing_journeys_res.json().get('journeys')
        self.assertIsInstance(journeys, list)
        self.assertGreaterEqual(len(journeys), 1)

    def test_05_gemini_ai_general_and_travel_queries(self):
        """Verify Gemini AI responds to general questions and travel questions."""
        # 1. General question
        res_general = requests.post(f"{BASE_URL}/assistant/chat", json={
            "message": "Explain what photosynthesis is in 2 sentences."
        })
        self.assertEqual(res_general.status_code, 200)
        gen_data = res_general.json()
        self.assertEqual(gen_data.get('status'), 'success')
        self.assertTrue(len(gen_data.get('reply', '')) > 20)
        self.assertIn("photosynthesis", gen_data.get('reply', '').lower())

        # 2. Travel question
        res_travel = requests.post(f"{BASE_URL}/assistant/chat", json={
            "message": "Are there flights from Tirupati to Delhi?"
        })
        self.assertEqual(res_travel.status_code, 200)
        travel_data = res_travel.json()
        self.assertEqual(travel_data.get('status'), 'success')
        self.assertTrue(len(travel_data.get('reply', '')) > 20)

if __name__ == '__main__':
    unittest.main()
