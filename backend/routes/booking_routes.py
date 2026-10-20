import secrets
import time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from routes.auth_routes import login_required, get_current_user
from services.booking_service import create_booking, get_booking_details, cancel_booking
from database import query_all, query_one, execute_commit

booking_bp = Blueprint('bookings', __name__, url_prefix='/api/v1/bookings')

# Thread-safe in-memory OTP cache for instant cross-request fallback
_otp_memory_store = {}

def ensure_otp_table():
    try:
        execute_commit("""
            CREATE TABLE IF NOT EXISTS otp_verifications (
                verification_id INT AUTO_INCREMENT PRIMARY KEY,
                request_id VARCHAR(64) NOT NULL UNIQUE,
                user_id INT NULL,
                phone VARCHAR(32) NOT NULL,
                otp_code VARCHAR(10) NOT NULL,
                verification_token VARCHAR(64) NULL,
                status ENUM('pending', 'verified', 'expired', 'used') DEFAULT 'pending',
                attempts INT DEFAULT 0,
                expires_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                verified_at DATETIME NULL,
                INDEX idx_req_id (request_id),
                INDEX idx_phone (phone)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
    except Exception as e:
        print(f"Notice: otp_verifications table check: {e}")

ensure_otp_table()

@booking_bp.route('/otp/send', methods=['POST'])
@login_required
def send_booking_otp(user):
    """
    Demonstration OTP generator for mobile verification before payment.
    Creates a valid server-side verification request stored in MySQL and memory.
    Generates a 6-digit sandbox demonstration OTP.
    """
    data = request.get_json() or {}
    phone = (data.get('phone') or '').strip()
    passenger_name = (data.get('full_name') or user.get('full_name') or 'Traveler').strip()

    if not phone or len(phone) < 7:
        return jsonify({
            "status": "error",
            "message": "A valid mobile phone number is required for demonstration verification."
        }), 400

    # Invalidate any previous pending OTP requests for this user/phone
    try:
        execute_commit("""
            UPDATE otp_verifications 
            SET status = 'expired' 
            WHERE user_id = %s AND phone = %s AND status = 'pending';
        """, (user['user_id'], phone))
    except Exception as e:
        print(f"Notice: Previous OTP expiration notice: {e}")

    # Generate unique server-side verification request ID and 6-digit sandbox OTP
    request_id = f"otp_req_{secrets.token_hex(12)}"
    demo_otp = str(secrets.randbelow(900000) + 100000)
    expires_at_epoch = time.time() + 600 # 10 minutes

    # Store in MySQL database for cross-instance and cross-origin state
    try:
        execute_commit("""
            INSERT INTO otp_verifications 
            (request_id, user_id, phone, otp_code, status, attempts, expires_at)
            VALUES (%s, %s, %s, %s, 'pending', 0, DATE_ADD(NOW(), INTERVAL 10 MINUTE));
        """, (request_id, user['user_id'], phone, demo_otp))
    except Exception as dbe:
        print(f"Notice: DB insert otp_verifications error: {dbe}")

    # Dual-layer storage in server-side memory store
    _otp_memory_store[request_id] = {
        'request_id': request_id,
        'code': demo_otp,
        'phone': phone,
        'user_id': user['user_id'],
        'status': 'pending',
        'attempts': 0,
        'expires_at': expires_at_epoch
    }

    # Also save in session for backward compatibility
    session['booking_otp'] = {
        'request_id': request_id,
        'code': demo_otp,
        'phone': phone,
        'user_id': user['user_id'],
        'expires_at': expires_at_epoch
    }
    session.pop('booking_otp_verified', None)

    return jsonify({
        "status": "success",
        "message": f"Demonstration OTP generated for {phone}.",
        "request_id": request_id,
        "demo_otp": demo_otp,
        "phone": phone,
        "passenger_name": passenger_name,
        "expires_in_seconds": 600,
        "is_demonstration": True,
        "note": "Demonstration Sandbox Mode: No actual SMS was sent and no charges apply. Use this test OTP to verify."
    }), 200

@booking_bp.route('/otp/verify', methods=['POST'])
@login_required
def verify_booking_otp(user):
    """
    Demonstration OTP verification endpoint.
    Verifies the submitted 6-digit code against server-side request state.
    """
    data = request.get_json() or {}
    submitted_otp = (data.get('otp') or '').strip()
    phone = (data.get('phone') or '').strip()
    request_id = (data.get('request_id') or '').strip()

    # Prevent verification if no OTP request was created first
    if not request_id:
        return jsonify({
            "status": "error",
            "message": "No active OTP request found. Please click 'Send OTP' first."
        }), 400

    if not submitted_otp:
        return jsonify({
            "status": "error",
            "message": "Please enter the 6-digit demonstration OTP code."
        }), 400

    # Retrieve record by request_id
    record = None
    try:
        record = query_one("""
            SELECT * FROM otp_verifications 
            WHERE request_id = %s;
        """, (request_id,))
    except Exception as dbe:
        print(f"Notice: DB query otp_verifications error: {dbe}")

    # Memory store fallback if DB query returned nothing
    if not record and request_id in _otp_memory_store:
        record = _otp_memory_store[request_id]

    # If still no active verification request found
    if not record:
        return jsonify({
            "status": "error",
            "message": "No active OTP request found. Please click 'Send OTP' first."
        }), 400

    # Verify user ownership if user_id is set
    if record.get('user_id') and record.get('user_id') != user['user_id']:
        return jsonify({
            "status": "error",
            "message": "No active OTP request found. Please click 'Send OTP' first."
        }), 400

    # Verify phone match if provided
    if phone and record.get('phone') and record.get('phone') != phone:
        return jsonify({
            "status": "error",
            "message": "Mobile phone number does not match the active OTP request."
        }), 400

    rec_status = record.get('status', 'pending')
    req_id = record.get('request_id')

    if rec_status == 'used':
        return jsonify({
            "status": "error",
            "message": "This demonstration OTP has already been verified and used. Please request a new OTP code."
        }), 400

    # Check expiration
    expires_at = record.get('expires_at')
    is_expired = False
    if isinstance(expires_at, (int, float)):
        is_expired = time.time() > expires_at
    elif expires_at:
        try:
            if isinstance(expires_at, str):
                expires_dt = datetime.fromisoformat(expires_at)
            else:
                expires_dt = expires_at
            is_expired = datetime.now() > expires_dt
        except Exception:
            is_expired = False

    if is_expired or rec_status == 'expired':
        try:
            execute_commit("""
                UPDATE otp_verifications SET status = 'expired' WHERE request_id = %s;
            """, (req_id,))
        except Exception:
            pass
        if req_id in _otp_memory_store:
            _otp_memory_store[req_id]['status'] = 'expired'
        session.pop('booking_otp', None)
        return jsonify({
            "status": "error",
            "message": "Demonstration OTP has expired. Please request a new OTP code."
        }), 400

    # Check attempts
    attempts = record.get('attempts', 0)
    if attempts >= 5:
        return jsonify({
            "status": "error",
            "message": "Maximum verification attempts exceeded. Please request a new OTP code."
        }), 429

    # Validate submitted OTP
    expected_otp = str(record.get('otp_code') or record.get('code') or '')
    if submitted_otp != expected_otp:
        new_attempts = attempts + 1
        try:
            execute_commit("""
                UPDATE otp_verifications SET attempts = %s WHERE request_id = %s;
            """, (new_attempts, req_id))
        except Exception:
            pass
        if req_id in _otp_memory_store:
            _otp_memory_store[req_id]['attempts'] = new_attempts
        return jsonify({
            "status": "error",
            "message": "Invalid OTP code. Please enter the exact 6-digit demonstration code shown."
        }), 400

    # Verification successful: generate single-use verification token
    verification_token = secrets.token_hex(16)
    try:
        execute_commit("""
            UPDATE otp_verifications 
            SET status = 'verified', verification_token = %s, verified_at = NOW() 
            WHERE request_id = %s;
        """, (verification_token, req_id))
    except Exception as dbe:
        print(f"Notice: DB update verified error: {dbe}")

    if req_id in _otp_memory_store:
        _otp_memory_store[req_id]['status'] = 'verified'
        _otp_memory_store[req_id]['verification_token'] = verification_token

    session['booking_otp_verified'] = {
        'phone': record.get('phone'),
        'user_id': user['user_id'],
        'token': verification_token,
        'verified_at': time.time()
    }

    return jsonify({
        "status": "success",
        "message": "Mobile number verified successfully (Demonstration Mode).",
        "verification_token": verification_token,
        "request_id": req_id,
        "phone": record.get('phone'),
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
    token_valid = False

    if verification_token:
        try:
            ver_row = query_one("""
                SELECT * FROM otp_verifications 
                WHERE verification_token = %s AND user_id = %s AND status = 'verified';
            """, (verification_token, user['user_id']))
            if ver_row:
                token_valid = True
                # Mark as used so it cannot be re-used
                execute_commit("""
                    UPDATE otp_verifications SET status = 'used' WHERE verification_id = %s;
                """, (ver_row['verification_id'],))
        except Exception as dbe:
            print(f"Notice: Verification token DB lookup error: {dbe}")

    # Check memory store fallback
    if not token_valid and verification_token:
        for req_k, mem_rec in _otp_memory_store.items():
            if mem_rec.get('verification_token') == verification_token and mem_rec.get('user_id') == user['user_id'] and mem_rec.get('status') == 'verified':
                token_valid = True
                mem_rec['status'] = 'used'
                break

    # Session fallback
    if not token_valid:
        otp_verified = session.get('booking_otp_verified')
        if otp_verified and otp_verified.get('user_id') == user['user_id'] and (not verification_token or otp_verified.get('token') == verification_token):
            token_valid = True
            session.pop('booking_otp_verified', None)

    if not token_valid:
        return jsonify({
            "status": "error",
            "message": "Mobile OTP verification is mandatory before proceeding to payment and confirmation."
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
            "booking": full_booking
        }), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@booking_bp.route('/<int:booking_id>', methods=['GET'])
@login_required
def get_booking(user, booking_id):
    booking = get_booking_details(booking_id, user_id=user['user_id'])
    if not booking:
        return jsonify({"status": "error", "message": "Booking not found or unauthorized access"}), 404
    return jsonify({"status": "success", "booking": booking})

@booking_bp.route('/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel(user, booking_id):
    data = request.get_json() or {}
    reason = data.get('reason', 'User requested cancellation')
    try:
        cancel_record = cancel_booking(booking_id, user_id=user['user_id'], reason=reason)
        return jsonify({
            "status": "success",
            "message": "Booking cancelled successfully and refund processed.",
            "cancellation": cancel_record
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@booking_bp.route('/user', methods=['GET'])
@login_required
def get_user_bookings(user):
    bookings = query_all("""
        SELECT b.booking_id, b.booking_reference, b.booking_status, b.total_amount,
               b.currency, b.payment_status, b.created_at, b.confirmed_at,
               f.flight_number, f.scheduled_departure, f.scheduled_arrival,
               orig.iata_code AS origin_code, orig.city AS origin_city,
               dest.iata_code AS destination_code, dest.city AS destination_city,
               al.airline_name, al.iata_code AS airline_code
        FROM bookings b
        JOIN booking_segments bs ON b.booking_id = bs.booking_id AND bs.segment_order = 1
        JOIN flights f ON bs.flight_id = f.flight_id
        JOIN airlines al ON f.airline_id = al.airline_id
        JOIN airports orig ON f.origin_airport_id = orig.airport_id
        JOIN airports dest ON f.destination_airport_id = dest.airport_id
        WHERE b.user_id = %s
        ORDER BY b.created_at DESC;
    """, (user['user_id'],))
    return jsonify({"status": "success", "bookings": bookings})
