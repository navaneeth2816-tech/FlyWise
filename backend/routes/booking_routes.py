import secrets
import time
from flask import Blueprint, request, jsonify, session
from routes.auth_routes import login_required, get_current_user
from services.booking_service import create_booking, get_booking_details, cancel_booking
from database import query_all

booking_bp = Blueprint('bookings', __name__, url_prefix='/api/v1/bookings')

@booking_bp.route('/otp/send', methods=['POST'])
@login_required
def send_booking_otp(user):
    """
    Demonstration OTP generator for mobile verification before payment.
    Generates a secure 6-digit sandbox OTP and stores it in the authenticated session.
    """
    data = request.get_json() or {}
    phone = (data.get('phone') or '').strip()
    passenger_name = (data.get('full_name') or user.get('full_name') or 'Traveler').strip()

    if not phone or len(phone) < 7:
        return jsonify({
            "status": "error",
            "message": "A valid mobile phone number is required for demonstration verification."
        }), 400

    # Generate 6-digit demonstration OTP
    demo_otp = str(secrets.randbelow(900000) + 100000)

    # Store in session with 10-minute expiration
    session['booking_otp'] = {
        'code': demo_otp,
        'phone': phone,
        'user_id': user['user_id'],
        'expires_at': time.time() + 600
    }
    # Clear any previous verification
    session.pop('booking_otp_verified', None)

    return jsonify({
        "status": "success",
        "message": f"Demonstration OTP generated for {phone}.",
        "demo_otp": demo_otp,
        "phone": phone,
        "passenger_name": passenger_name,
        "is_demonstration": True,
        "note": "Demonstration Sandbox Mode: No actual SMS gateway was triggered. Use this test OTP to verify."
    }), 200

@booking_bp.route('/otp/verify', methods=['POST'])
@login_required
def verify_booking_otp(user):
    """
    Demonstration OTP verification endpoint.
    Verifies the submitted 6-digit code against the session.
    """
    data = request.get_json() or {}
    submitted_otp = (data.get('otp') or '').strip()
    phone = (data.get('phone') or '').strip()

    otp_record = session.get('booking_otp')
    if not otp_record or otp_record.get('user_id') != user['user_id']:
        return jsonify({
            "status": "error",
            "message": "No active OTP request found. Please click 'Send OTP' first."
        }), 400

    if time.time() > otp_record.get('expires_at', 0):
        session.pop('booking_otp', None)
        return jsonify({
            "status": "error",
            "message": "Demonstration OTP has expired. Please request a new OTP code."
        }), 400

    if otp_record.get('code') != submitted_otp:
        return jsonify({
            "status": "error",
            "message": "Invalid OTP code. Please enter the exact 6-digit demonstration code shown."
        }), 400

    # Verification successful: generate single-use verification token
    verification_token = secrets.token_hex(16)
    session['booking_otp_verified'] = {
        'phone': otp_record['phone'],
        'user_id': user['user_id'],
        'token': verification_token,
        'verified_at': time.time()
    }

    return jsonify({
        "status": "success",
        "message": "Mobile number verified successfully (Demonstration Mode).",
        "verification_token": verification_token,
        "phone": otp_record['phone'],
        "is_demonstration": True
    }), 200

@booking_bp.route('', methods=['POST'])
@login_required
def make_booking(user):
    data = request.get_json() or {}
    itinerary_id = data.get('itinerary_id')
    flight_ids = data.get('flight_ids', [])
    passengers_list = data.get('passengers', [])
    seat_assignments = data.get('seat_assignments', [])
    total_amount = data.get('total_amount', 0.0)
    payment_mode = data.get('payment_mode', 'card')
    add_ons = data.get('add_ons')
    verification_token = data.get('verification_token')

    if not flight_ids or not passengers_list:
        return jsonify({
            "status": "error",
            "message": "Missing required booking details (flight_ids and passengers list are required)."
        }), 400

    # Backend Validation: Enforce demonstration OTP verification before allowing booking
    otp_verified = session.get('booking_otp_verified')
    if not otp_verified or otp_verified.get('user_id') != user['user_id']:
        return jsonify({
            "status": "error",
            "message": "Mobile OTP verification is mandatory before proceeding to payment and confirmation."
        }), 403

    if verification_token and otp_verified.get('token') != verification_token:
        return jsonify({
            "status": "error",
            "message": "Verification token mismatch or expired. Please re-verify mobile OTP."
        }), 403

    try:
        result = create_booking(
            user_id=user['user_id'],
            itinerary_id=itinerary_id,
            flight_ids=flight_ids,
            passengers_list=passengers_list,
            seat_assignments=seat_assignments,
            total_amount=total_amount,
            payment_mode=payment_mode,
            add_ons=add_ons
        )
        full_booking = get_booking_details(result['booking_id'], user_id=user['user_id'])

        # Invalidate OTP session state so it cannot be re-used for duplicate bookings
        session.pop('booking_otp_verified', None)
        session.pop('booking_otp', None)

        return jsonify({
            "status": "success",
            "message": "Flight booked and confirmed successfully!",
            "booking": full_booking or result
        }), 201
    except ValueError as ve:
        return jsonify({"status": "error", "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Booking transaction failed: {str(e)}"}), 500

@booking_bp.route('', methods=['GET'])
@login_required
def get_user_bookings(user):
    # Fetch all bookings for this user with origin, destination, departure
    bookings = query_all("""
        SELECT b.booking_id, b.booking_reference, b.booking_status, b.total_amount, b.created_at,
               j.journey_id, j.journey_status, j.planned_departure, j.planned_arrival,
               orig.iata_code AS origin_code, orig.city AS origin_city,
               dest.iata_code AS destination_code, dest.city AS destination_city,
               al.airline_name, al.iata_code AS airline_code, f.flight_number
        FROM bookings b
        LEFT JOIN journeys j ON b.booking_id = j.booking_id
        LEFT JOIN booking_segments bs ON b.booking_id = bs.booking_id AND bs.segment_order = 1
        LEFT JOIN flights f ON bs.flight_id = f.flight_id
        LEFT JOIN airlines al ON f.airline_id = al.airline_id
        LEFT JOIN airports orig ON f.origin_airport_id = orig.airport_id
        LEFT JOIN airports dest ON f.destination_airport_id = dest.airport_id
        WHERE b.user_id = %s
        ORDER BY b.created_at DESC;
    """, (user['user_id'],))

    return jsonify({"status": "success", "bookings": bookings})

@booking_bp.route('/<identifier>', methods=['GET'])
def get_single_booking(identifier):
    # Can be accessed by logged in user or with booking reference (PNR)
    user = get_current_user()
    user_id = user['user_id'] if (user and user.get('role') != 'admin') else None
    
    booking = get_booking_details(identifier, user_id=user_id)
    if not booking:
        return jsonify({"status": "error", "message": "Booking not found or access denied."}), 404
        
    return jsonify({"status": "success", "booking": booking})

@booking_bp.route('/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel(user, booking_id):
    data = request.get_json() or {}
    reason = data.get('reason', 'Cancelled by traveler')
    try:
        res = cancel_booking(booking_id=booking_id, user_id=user['user_id'], reason=reason)
        return jsonify({"status": "success", "message": "Booking cancelled successfully.", "cancellation": res})
    except ValueError as ve:
        return jsonify({"status": "error", "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Cancellation error: {str(e)}"}), 500
