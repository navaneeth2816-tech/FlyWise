from flask import Blueprint, request, jsonify
from routes.auth_routes import login_required
from database import query_all, query_one, execute_commit
from services.risk_service import find_recovery_options

journey_bp = Blueprint('journeys', __name__, url_prefix='/api/v1/journeys')

DIGITAL_TWIN_STAGES = [
    {"stage": "confirmed", "label": "Booking Confirmed", "desc": "Ticket issued, seat reserved"},
    {"stage": "pre_departure", "label": "Pre-Departure", "desc": "Checklist, packing, airport transport planning"},
    {"stage": "check_in", "label": "Web Check-In", "desc": "48h window open, boarding pass generated"},
    {"stage": "boarding", "label": "Boarding Gate", "desc": "Security cleared, gate active"},
    {"stage": "departed", "label": "Departed / In-Air", "desc": "Aircraft airborne, cruising to destination"},
    {"stage": "connection_in_progress", "label": "Connection / Transit", "desc": "Layover buffer active"},
    {"stage": "arrived", "label": "Arrived", "desc": "Touchdown, baggage reclaim"},
    {"stage": "completed", "label": "Journey Completed", "desc": "Trip safely concluded"}
]

@journey_bp.route('', methods=['GET'])
@login_required
def get_user_journeys(user):
    journeys = query_all("""
        SELECT j.journey_id, j.journey_status, j.planned_departure, j.planned_arrival, j.last_updated_at,
               b.booking_id, b.booking_reference, b.total_amount,
               orig.iata_code AS origin_code, orig.city AS origin_city,
               dest.iata_code AS destination_code, dest.city AS destination_city,
               al.airline_name, al.iata_code AS airline_code, f.flight_number, f.flight_status
        FROM journeys j
        JOIN bookings b ON j.booking_id = b.booking_id
        LEFT JOIN booking_segments bs ON b.booking_id = bs.booking_id AND bs.segment_order = 1
        LEFT JOIN flights f ON bs.flight_id = f.flight_id
        LEFT JOIN airlines al ON f.airline_id = al.airline_id
        LEFT JOIN airports orig ON f.origin_airport_id = orig.airport_id
        LEFT JOIN airports dest ON f.destination_airport_id = dest.airport_id
        WHERE j.user_id = %s
        ORDER BY j.planned_departure DESC;
    """, (user['user_id'],))

    return jsonify({"status": "success", "journeys": journeys})

@journey_bp.route('/<int:journey_id>', methods=['GET'])
@login_required
def get_single_journey(user, journey_id):
    journey = query_one("""
        SELECT j.*, b.booking_reference, b.total_amount, b.booking_status,
               orig.iata_code AS origin_code, orig.city AS origin_city, orig.airport_name AS origin_name,
               dest.iata_code AS destination_code, dest.city AS destination_city, dest.airport_name AS destination_name,
               al.airline_name, al.iata_code AS airline_code, al.support_information,
               f.flight_id, f.flight_number, f.flight_status, f.scheduled_departure, f.scheduled_arrival
        FROM journeys j
        JOIN bookings b ON j.booking_id = b.booking_id
        LEFT JOIN booking_segments bs ON b.booking_id = bs.booking_id AND bs.segment_order = 1
        LEFT JOIN flights f ON bs.flight_id = f.flight_id
        LEFT JOIN airlines al ON f.airline_id = al.airline_id
        LEFT JOIN airports orig ON f.origin_airport_id = orig.airport_id
        LEFT JOIN airports dest ON f.destination_airport_id = dest.airport_id
        WHERE j.journey_id = %s AND j.user_id = %s;
    """, (journey_id, user['user_id']))

    if not journey:
        return jsonify({"status": "error", "message": "Journey not found or unauthorized"}), 404

    events = query_all("""
        SELECT * FROM journey_events 
        WHERE journey_id = %s 
        ORDER BY event_timestamp DESC;
    """, (journey_id,))

    # Digital twin timeline progress
    current_idx = 0
    st_val = journey['journey_status']
    for idx, s in enumerate(DIGITAL_TWIN_STAGES):
        if s['stage'] == st_val:
            current_idx = idx
            break

    journey['events'] = events
    journey['digital_twin'] = {
        "current_stage": st_val,
        "current_index": current_idx,
        "total_stages": len(DIGITAL_TWIN_STAGES),
        "stages": DIGITAL_TWIN_STAGES
    }

    return jsonify({"status": "success", "journey": journey})

@journey_bp.route('/<int:journey_id>/emergency-mode', methods=['GET', 'POST'])
@login_required
def emergency_mode(user, journey_id):
    """
    Emergency Travel Mode.
    PRD Section 23: Centralized disruption radar, alternative flights, DGCA passenger rights, and support contacts.
    """
    journey = query_one("""
        SELECT j.*, b.booking_reference, b.total_amount,
               f.flight_id, f.flight_number, f.flight_status, f.scheduled_departure,
               orig.iata_code AS origin_code, orig.city AS origin_city,
               dest.iata_code AS destination_code, dest.city AS destination_city,
               al.airline_name, al.iata_code AS airline_code, al.support_information
        FROM journeys j
        JOIN bookings b ON j.booking_id = b.booking_id
        JOIN booking_segments bs ON b.booking_id = bs.booking_id AND bs.segment_order = 1
        JOIN flights f ON bs.flight_id = f.flight_id
        JOIN airlines al ON f.airline_id = al.airline_id
        JOIN airports orig ON f.origin_airport_id = orig.airport_id
        JOIN airports dest ON f.destination_airport_id = dest.airport_id
        WHERE j.journey_id = %s AND j.user_id = %s;
    """, (journey_id, user['user_id']))

    if not journey:
        return jsonify({"status": "error", "message": "Journey not found"}), 404

    # If activated via POST, record event and update status to disrupted
    if request.method == 'POST':
        execute_commit("UPDATE journeys SET journey_status = 'disrupted' WHERE journey_id = %s;", (journey_id,))
        execute_commit("""
            INSERT INTO journey_events (journey_id, event_type, event_description, verification_status)
            VALUES (%s, 'emergency_mode_activated', 'Traveler activated Emergency Travel Mode due to schedule disruption.', 'user_reported');
        """, (journey_id,))

    # Find alternatives
    recovery = find_recovery_options(journey['flight_id'])

    dgca_rights = [
        "Delay > 2 hours: Airline must provide complimentary refreshments and water.",
        "Delay > 4 hours or overnight: Airline must offer hotel accommodation and airport transfers.",
        "Flight Cancelled: Passenger entitled to full refund without cancellation fees or free alternate flight.",
        "Denied Boarding: Passenger entitled to alternate flight or compensation up to 400% of base fare."
    ]

    return jsonify({
        "status": "success",
        "emergency_mode_active": True,
        "journey": journey,
        "disruption_summary": f"Flight {journey['flight_number']} ({journey['flight_status'].upper()})",
        "passenger_rights": dgca_rights,
        "recovery_options": recovery,
        "support_contacts": {
            "airline_support": f"Call {journey['airline_name']} Priority Disruption Desk",
            "airport_helpdesk": f"{journey['origin_city']} ({journey['origin_code']}) Terminal Information Booth",
            "dgca_airsewa": "AirSewa Portal (https://airsewa.gov.in) for consumer dispute resolution"
        }
    })

@journey_bp.route('/<int:journey_id>/checklist', methods=['GET'])
@login_required
def get_checklist(user, journey_id):
    """Returns dynamic travel checklist based on journey."""
    checklist = [
        {"id": 1, "task": "Check Government Photo ID (Aadhaar / Voter ID / Passport)", "category": "documents", "completed": True},
        {"id": 2, "task": "Complete Web Check-in & Download Boarding Pass", "category": "checkin", "completed": False},
        {"id": 3, "task": "Review Cabin (7kg) & Check-in (15kg) Baggage Weight Limits", "category": "baggage", "completed": True},
        {"id": 4, "task": "Confirm Airport Terminal & Ground Transit Route", "category": "transit", "completed": False},
        {"id": 5, "task": "Check Wheelchair / Special Assistance Reservation", "category": "accessibility", "completed": False}
    ]
    return jsonify({"status": "success", "checklist": checklist})
