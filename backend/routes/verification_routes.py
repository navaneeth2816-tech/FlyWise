import re
from flask import Blueprint, request, jsonify
from database import query_one

verification_bp = Blueprint('verification', __name__, url_prefix='/api/v1/verification')

@verification_bp.route('/analyze-message', methods=['POST'])
def analyze_message():
    """
    Booking Verification and Scam Assistance.
    PRD Section 18: Analyzes SMS/WhatsApp/Email messages for fraud indicators.
    """
    data = request.get_json() or {}
    message_text = data.get('message_text', '').strip()

    if not message_text:
        return jsonify({"status": "error", "message": "Message text is required for analysis."}), 400

    text_lower = message_text.lower()
    red_flags = []
    risk_score = 10 # baseline

    # Check 1: Urgent threat of cancellation
    if any(k in text_lower for k in ["cancel", "urgent", "immediately", "blocked", "suspended"]) and any(k in text_lower for k in ["minute", "min", "hour", "fee", "now"]):
        risk_score += 35
        red_flags.append("Artificial urgency tactic: legitimate airlines do not threaten immediate cancellation over unverified SMS or messages.")

    # Check 2: UPI / QR code payment requests
    if any(k in text_lower for k in ["scan qr", "qr code", "upi", "paytm", "send money", "gpay", "phonepe", "verification fee", "transfer fee"]):
        risk_score += 40
        red_flags.append("Suspicious payment demand: airlines NEVER request fee transfers via personal UPI handles or QR codes.")

    # Check 3: OTP or password requests
    if any(k in text_lower for k in ["otp", "password", "cvv", "pin", "credential"]):
        risk_score += 45
        red_flags.append("Critical credential theft: Never share One-Time Passwords (OTP), UPI PIN, or CVV with anyone claiming to be airline staff.")

    # Check 4: Suspicious link detection
    urls = re.findall(r'(https?://[^\s]+)', message_text)
    legitimate_domains = ["goindigo.in", "airindia.com", "airvistara.com", "spicejet.com", "akasaair.com", "flywise.ai"]
    for u in urls:
        is_legit = any(ld in u for ld in legitimate_domains)
        if not is_legit:
            risk_score += 30
            red_flags.append(f"Suspicious unverified link detected: '{u}'. Official airline links always use recognized `.in` or `.com` brand domains.")

    # Determine verdict
    if risk_score >= 60:
        verdict = "HIGH RISK — LIKELY FRAUDULENT"
        advice = "DO NOT click any links, do not pay money, and never share OTPs. Verify your PNR directly on the official airline website."
    elif risk_score >= 30:
        verdict = "MODERATE RISK — EXERCISE CAUTION"
        advice = "Message contains suspicious wording. Check your flight status via official channels."
    else:
        verdict = "LOW RISK — STANDARD ADVISORY"
        advice = "No common phishing patterns detected. Still ensure you only pay through official SSL secured portals."

    verification_checklist = [
        "1. Check your 6-character PNR on the airline's official app or flywise.ai.",
        "2. Never scan a QR code received via WhatsApp/SMS to 'receive refund'. QR codes only deduct money.",
        "3. Airlines will never ask for your debit card PIN or NetBanking password.",
        "4. Contact the airline's official 24x7 customer care number found on their verified website."
    ]

    return jsonify({
        "status": "success",
        "verdict": verdict,
        "risk_score": min(100, risk_score),
        "red_flags": red_flags,
        "advice": advice,
        "verification_checklist": verification_checklist
    })

@verification_bp.route('/check-pnr', methods=['POST'])
def check_pnr():
    """Directly verifies whether a PNR exists in the FlyWise system and shows confirmed state."""
    data = request.get_json() or {}
    pnr = data.get('pnr', '').strip().upper()

    if not pnr:
        return jsonify({"status": "error", "message": "PNR is required."}), 400

    booking = query_one("""
        SELECT b.booking_reference, b.booking_status, b.total_amount, b.confirmed_at,
               f.flight_number, f.scheduled_departure, al.airline_name,
               orig.iata_code AS origin_code, dest.iata_code AS destination_code
        FROM bookings b
        JOIN booking_segments bs ON b.booking_id = bs.booking_id AND bs.segment_order = 1
        JOIN flights f ON bs.flight_id = f.flight_id
        JOIN airlines al ON f.airline_id = al.airline_id
        JOIN airports orig ON f.origin_airport_id = orig.airport_id
        JOIN airports dest ON f.destination_airport_id = dest.airport_id
        WHERE b.booking_reference = %s;
    """, (pnr,))

    if not booking:
        return jsonify({
            "status": "not_found",
            "pnr": pnr,
            "message": "This PNR was not found in the FlyWise database. If you booked through another agent, verify on the operating airline's official portal."
        }), 404

    return jsonify({
        "status": "verified",
        "pnr": pnr,
        "booking": booking,
        "message": "PNR is authenticated and verified in the database."
    })
