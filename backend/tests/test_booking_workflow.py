import unittest
import requests
import pymysql
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config

BASE_URL = "http://127.0.0.1:5000/api/v1"

class TestBookingWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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
        cls.session = requests.Session()
        # Login with test user
        res = cls.session.post(f"{BASE_URL}/auth/login", json={
            "email": "navaneeth@flywise.ai",
            "password": "Password@123"
        })
        assert res.status_code == 200, "Login failed in setup"

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_01_direct_booking_blocked_without_otp(self):
        """
        Verify that attempting to bypass OTP verification by calling POST /bookings directly
        is blocked by the Flask backend with HTTP 403 Forbidden.
        """
        res = self.session.post(f"{BASE_URL}/bookings", json={
            "flight_ids": [1],
            "passengers": [{
                "full_name": "Bypass Attempt",
                "email": "bypass@flywise.ai",
                "phone": "+91 9876543210"
            }],
            "seat_assignments": [],
            "payment_mode": "card"
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn("OTP verification is mandatory", res.json().get('message', ''))

    def test_02_send_demonstration_otp(self):
        """
        Verify that calling POST /bookings/otp/send generates a 6-digit demonstration OTP,
        stores it in session, and clearly labels it as a demonstration sandbox code.
        """
        res = self.session.post(f"{BASE_URL}/bookings/otp/send", json={
            "phone": "+91 9876543210",
            "full_name": "Navaneeth Naidu"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertTrue(data.get('is_demonstration'))
        self.assertIn('demo_otp', data)
        self.assertEqual(len(data['demo_otp']), 6)
        self.assertTrue(data['demo_otp'].isdigit())
        self.assertIn('Demonstration', data.get('note', ''))

    def test_03_verify_otp_invalid_code(self):
        """
        Verify that submitting an incorrect OTP code fails with HTTP 400 Bad Request.
        """
        res = self.session.post(f"{BASE_URL}/bookings/otp/verify", json={
            "otp": "000000",
            "phone": "+91 9876543210"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid OTP", res.json().get('message', ''))

    def test_04_verify_otp_success_token(self):
        """
        Verify that submitting the correct demonstration OTP succeeds with HTTP 200
        and issues a single-use verification token.
        """
        # Request new OTP
        send_res = self.session.post(f"{BASE_URL}/bookings/otp/send", json={
            "phone": "+91 9876543210",
            "full_name": "Navaneeth Naidu"
        })
        self.assertEqual(send_res.status_code, 200)
        otp = send_res.json()['demo_otp']

        # Verify with received code
        verify_res = self.session.post(f"{BASE_URL}/bookings/otp/verify", json={
            "otp": otp,
            "phone": "+91 9876543210"
        })
        self.assertEqual(verify_res.status_code, 200)
        vdata = verify_res.json()
        self.assertEqual(vdata.get('status'), 'success')
        self.assertTrue(vdata.get('is_demonstration'))
        self.assertIn('verification_token', vdata)
        self.assertGreater(len(vdata['verification_token']), 10)

    def test_05_booking_validation_after_otp(self):
        """
        Verify passenger and flight validation after OTP is verified.
        Invalid inputs must return HTTP 400.
        """
        # Obtain OTP verification first
        send_res = self.session.post(f"{BASE_URL}/bookings/otp/send", json={
            "phone": "+91 9876543210",
            "full_name": "Navaneeth Naidu"
        })
        otp = send_res.json()['demo_otp']
        verify_res = self.session.post(f"{BASE_URL}/bookings/otp/verify", json={
            "otp": otp,
            "phone": "+91 9876543210"
        })
        token = verify_res.json()['verification_token']

        # 1. Invalid passenger name (too short)
        res = self.session.post(f"{BASE_URL}/bookings", json={
            "flight_ids": [1],
            "passengers": [{"full_name": "A", "email": "valid@email.com"}],
            "verification_token": token
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("minimum 2 characters", res.json().get('message', ''))

        # 2. Non-existent flight ID
        res = self.session.post(f"{BASE_URL}/bookings", json={
            "flight_ids": [999999],
            "passengers": [{"full_name": "Rahul Sharma", "email": "rahul@example.com"}],
            "verification_token": token
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("not found", res.json().get('message', '').lower())

    def test_06_booking_success_fare_recalc_and_mysql_save(self):
        """
        Complete end-to-end booking flow:
        1. Request Demo OTP
        2. Verify Demo OTP to receive verification token
        3. Submit booking with flight, available seat, add-ons, and payment mode
        4. Verify backend recalculates fare, executes payment, reserves seat, and saves to MySQL
        """
        # Step 1: Send OTP
        send_res = self.session.post(f"{BASE_URL}/bookings/otp/send", json={
            "phone": "+91 9876543210",
            "full_name": "Arjun Varma"
        })
        self.assertEqual(send_res.status_code, 200)
        otp = send_res.json()['demo_otp']

        # Step 2: Verify OTP
        verify_res = self.session.post(f"{BASE_URL}/bookings/otp/verify", json={
            "otp": otp,
            "phone": "+91 9876543210"
        })
        self.assertEqual(verify_res.status_code, 200)
        token = verify_res.json()['verification_token']

        # Find an available flight and seat
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT f.flight_id, s.seat_id, s.seat_number 
                FROM flights f 
                JOIN seats s ON f.flight_id = s.flight_id 
                WHERE s.seat_status = 'available' 
                LIMIT 1;
            """)
            row = cur.fetchone()
            self.assertIsNotNone(row, "Need at least one flight with available seats")
            flight_id = row['flight_id']
            seat_id = row['seat_id']

        payload = {
            "flight_ids": [flight_id],
            "passengers": [{
                "full_name": "Arjun Varma",
                "email": "arjun.varma@example.com",
                "phone": "+91 9876543210",
                "gender": "M",
                "date_of_birth": "1998-05-12"
            }],
            "seat_assignments": [{"seat_id": seat_id}],
            "add_ons": {
                "meal": True,
                "insurance": True,
                "priority": False
            },
            "payment_mode": "upi",
            "verification_token": token
        }

        # Step 3: Submit booking
        res = self.session.post(f"{BASE_URL}/bookings", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('booking', data)
        booking = data['booking']

        # Verify PNR format
        pnr = booking.get('booking_reference')
        self.assertTrue(pnr.startswith('FW-'))

        # Verify simulated payment reference in UPI mode
        self.assertTrue('SIM-PAY-UPI' in booking.get('provider_reference', ''))

        # Verify fare breakdown
        fb = booking.get('fare_breakdown', {})
        self.assertTrue(fb.get('is_simulated_payment'))
        self.assertGreater(fb.get('base_fare', 0), 0)
        self.assertGreater(fb.get('taxes_and_fees', 0), 0)
        self.assertEqual(fb.get('addons_fee'), 549.0) # meal (350) + insurance (199)

        # Verify MySQL persistence directly
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM bookings WHERE booking_reference = %s", (pnr,))
            db_booking = cur.fetchone()
            self.assertIsNotNone(db_booking)
            self.assertEqual(db_booking['booking_status'], 'confirmed')

            # Verify payment record in MySQL
            cur.execute("SELECT * FROM payments WHERE booking_id = %s", (db_booking['booking_id'],))
            db_payment = cur.fetchone()
            self.assertIsNotNone(db_payment)
            self.assertEqual(db_payment['payment_status'], 'success')
            self.assertIn('SIM-PAY-UPI', db_payment['provider_reference'])

            # Verify seat status updated to booked
            cur.execute("SELECT seat_status FROM seats WHERE seat_id = %s", (seat_id,))
            db_seat = cur.fetchone()
            self.assertEqual(db_seat['seat_status'], 'booked')

    def test_07_replay_protection_prevents_duplicate_booking(self):
        """
        Verify replay protection: After a booking is confirmed, the OTP session state
        is cleared. Attempting to submit another booking with the same session or token
        must fail with HTTP 403 Forbidden.
        """
        res = self.session.post(f"{BASE_URL}/bookings", json={
            "flight_ids": [1],
            "passengers": [{
                "full_name": "Replay Attempt",
                "email": "replay@flywise.ai",
                "phone": "+91 9876543210"
            }],
            "seat_assignments": [],
            "payment_mode": "card"
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn("OTP verification is mandatory", res.json().get('message', ''))

    def test_08_duplicate_seat_booking_conflict(self):
        """
        Test concurrency: attempting to book an already booked seat must fail with 400.
        """
        # Step 1: Send & verify OTP for this attempt
        send_res = self.session.post(f"{BASE_URL}/bookings/otp/send", json={
            "phone": "+91 9876543210",
            "full_name": "Conflict User"
        })
        otp = send_res.json()['demo_otp']
        verify_res = self.session.post(f"{BASE_URL}/bookings/otp/verify", json={
            "otp": otp,
            "phone": "+91 9876543210"
        })
        token = verify_res.json()['verification_token']

        # Find a seat that is already booked
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT f.flight_id, s.seat_id, s.seat_number 
                FROM flights f 
                JOIN seats s ON f.flight_id = s.flight_id 
                WHERE s.seat_status = 'booked' 
                LIMIT 1;
            """)
            row = cur.fetchone()
            if row:
                flight_id = row['flight_id']
                seat_id = row['seat_id']

                payload = {
                    "flight_ids": [flight_id],
                    "passengers": [{
                        "full_name": "Conflict User",
                        "email": "conflict@example.com"
                    }],
                    "seat_assignments": [{"seat_id": seat_id}],
                    "payment_mode": "card",
                    "verification_token": token
                }

                res = self.session.post(f"{BASE_URL}/bookings", json=payload)
                self.assertEqual(res.status_code, 400)
                self.assertIn("no longer available", res.json().get('message', '').lower())

    def test_09_ticket_retrieval_by_pnr(self):
        """Test retrieving booking and ticket details by PNR reference."""
        # Find any existing booking
        with self.conn.cursor() as cur:
            cur.execute("SELECT booking_reference FROM bookings ORDER BY created_at DESC LIMIT 1;")
            row = cur.fetchone()
            self.assertIsNotNone(row)
            pnr = row['booking_reference']

        res = self.session.get(f"{BASE_URL}/bookings/{pnr}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'success')
        booking = data.get('booking')
        self.assertEqual(booking.get('booking_reference'), pnr)
        self.assertGreater(len(booking.get('passengers', [])), 0)
        self.assertGreater(len(booking.get('segments', [])), 0)
        self.assertIn('fare_breakdown', booking)

if __name__ == '__main__':
    unittest.main()
