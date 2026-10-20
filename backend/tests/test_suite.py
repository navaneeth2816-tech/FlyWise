import unittest
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from database import query_one, query_all
from services.flight_service import search_flights
from services.recommendation_service import score_and_rank_itineraries
from services.cost_service import calculate_journey_cost
from services.risk_service import assess_connection_risk
from services.booking_service import create_booking, cancel_booking

class TestFlyWiseSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_database_health(self):
        """Verify DB connection and views exist."""
        resp = self.client.get('/api/v1/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertTrue(data['database_connected'])

    def test_02_views_demonstration(self):
        """Verify B.Tech DBMS Views execute correctly."""
        search_view = query_all("SELECT * FROM v_flight_search LIMIT 5;")
        self.assertGreater(len(search_view), 0)
        
        perf_view = query_all("SELECT * FROM v_airline_performance LIMIT 5;")
        self.assertGreater(len(perf_view), 0)

        route_view = query_all("SELECT * FROM v_route_analytics LIMIT 5;")
        self.assertGreater(len(route_view), 0)

    def test_03_flight_search_tirupati_to_delhi(self):
        """User story test: Tirupati (TIR) to Delhi (DEL)."""
        resp = self.client.get('/api/v1/flights/search?origin=TIR&destination=DEL&date=2026-10-23')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['count'] > 0)
        
        # Check that top flight has recommendation score and explanations
        first_it = data['itineraries'][0]
        self.assertIn('recommendation_score', first_it)
        self.assertIn('explanations', first_it)
        self.assertIn('connection_risk', first_it)
        self.assertIn('estimated_journey_cost', first_it)

    def test_04_journey_cost_calculator(self):
        """Verify itemized cost calculation without double counting."""
        res = calculate_journey_cost(
            base_fare=5000,
            origin_code="DEL",
            destination_code="BOM",
            baggage_kg=20, # 5kg excess
            seat_type="standard_window",
            ground_transport="cab"
        )
        self.assertGreater(res['estimated_total_journey_cost'], 5000)
        self.assertEqual(res['baggage_charges']['requested_kg'], 20)
        self.assertGreater(res['baggage_charges']['charge'], 0)

    def test_05_connection_risk_evaluation(self):
        """Verify direct vs tight layover risk categorization."""
        direct_it = {"stops": 0}
        direct_risk = assess_connection_risk(direct_it)
        self.assertEqual(direct_risk['risk_level'], 'LOW')

        tight_conn = {
            "stops": 1,
            "connection_info": {
                "layover_minutes": 35,
                "layover_airport": "BOM",
                "same_airline": False
            }
        }
        tight_risk = assess_connection_risk(tight_conn)
        self.assertEqual(tight_risk['risk_level'], 'HIGH')

    def test_06_booking_acid_transaction_and_cancellation(self):
        """Verify transactional booking creation, seat locking, and cancellation."""
        # Find flight with available seats
        seats = query_all("SELECT seat_id, flight_id FROM seats WHERE seat_status = 'available' LIMIT 1;")
        self.assertGreater(len(seats), 0)
        seat = seats[0]
        
        # 1. Create booking
        booking_res = create_booking(
            user_id=1,
            itinerary_id=f"dir_{seat['flight_id']}",
            flight_ids=[seat['flight_id']],
            passengers_list=[{"full_name": "Test Passenger", "email": "test@flywise.ai"}],
            seat_assignments=[{"seat_id": seat['seat_id']}],
            total_amount=5600.0,
            payment_mode="card"
        )
        self.assertEqual(booking_res['status'], 'confirmed')
        self.assertTrue(booking_res['booking_reference'].startswith('FW-'))

        # Check seat is now booked
        seat_check = query_one("SELECT seat_status FROM seats WHERE seat_id = %s;", (seat['seat_id'],))
        self.assertEqual(seat_check['seat_status'], 'booked')

        # 2. Cancel booking
        cancel_res = cancel_booking(
            booking_id=booking_res['booking_id'],
            user_id=1,
            reason="Trip schedule rescheduled"
        )
        self.assertEqual(cancel_res['status'], 'processed')

        # Check seat is released back to available
        seat_check2 = query_one("SELECT seat_status FROM seats WHERE seat_id = %s;", (seat['seat_id'],))
        self.assertEqual(seat_check2['seat_status'], 'available')

    def test_07_scam_verification(self):
        """Verify booking fraud detection analyzer."""
        resp = self.client.post('/api/v1/verification/analyze-message', json={
            "message_text": "URGENT: Your Air India ticket will be CANCELLED in 10 minutes unless you pay verification fee ₹499 by scanning QR code or sending to upi@fake"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['verdict'], 'HIGH RISK — LIKELY FRAUDULENT')
        self.assertGreater(len(data['red_flags']), 1)

    def test_08_gemini_assistant_chat(self):
        """Verify conversational assistant responds with grounded flight details."""
        resp = self.client.post('/api/v1/assistant/chat', json={
            "message": "Find flights from Tirupati to Delhi next Friday under ₹7000"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("reply", data)
        self.assertGreater(len(data['reply']), 20)

if __name__ == '__main__':
    unittest.main()
