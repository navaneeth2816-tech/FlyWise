import json
from flask import Blueprint, request, jsonify
from database import query_all, query_one

baggage_bp = Blueprint('baggage', __name__, url_prefix='/api/v1/baggage')

@baggage_bp.route('/policies', methods=['GET'])
def get_all_policies():
    airlines = query_all("SELECT airline_id, airline_name, iata_code, support_information FROM airlines;")
    results = []
    for a in airlines:
        info = a['support_information']
        if isinstance(info, str):
            try:
                info = json.loads(info)
            except Exception:
                info = {}
        results.append({
            "airline_id": a['airline_id'],
            "airline_name": a['airline_name'],
            "airline_code": a['iata_code'],
            "rules": info.get('baggage_rules', {})
        })
    return jsonify({"status": "success", "policies": results})

@baggage_bp.route('/interpret', methods=['POST'])
def interpret():
    data = request.get_json() or {}
    airline_code = data.get('airline_code', '6E').strip().upper()
    travel_class = data.get('travel_class', 'economy').strip().lower()
    expected_weight_kg = float(data.get('expected_weight_kg', 18))

    airline = query_one("SELECT airline_name, iata_code, support_information FROM airlines WHERE iata_code = %s;", (airline_code,))
    if not airline:
        return jsonify({"status": "error", "message": "Airline not found"}), 404

    info = airline['support_information']
    if isinstance(info, str):
        try:
            info = json.loads(info)
        except Exception:
            info = {}

    rules = info.get('baggage_rules', {})
    free_checkin_kg = 30 if travel_class == 'business' else 15
    cabin_limit = "10 kg" if travel_class == 'business' else "7 kg (1 piece up to 115cm dimensions)"
    excess_rate = rules.get('excess_per_kg_inr', 500)

    excess_kg = max(0.0, expected_weight_kg - free_checkin_kg)
    excess_fee = excess_kg * excess_rate

    restrictions = [
        "Power banks, loose lithium batteries, and e-cigarettes must be carried ONLY in cabin baggage, NEVER in checked baggage.",
        "Liquids, aerosols, and gels in cabin baggage are restricted to containers of 100ml each, packed in a transparent resealable bag.",
        "Sharp objects, scissors, blades, and lighters are strictly prohibited in cabin baggage."
    ]

    return jsonify({
        "status": "success",
        "airline": airline['airline_name'],
        "airline_code": airline['iata_code'],
        "travel_class": travel_class,
        "cabin_allowance": cabin_limit,
        "free_checkin_allowance_kg": free_checkin_kg,
        "expected_weight_kg": expected_weight_kg,
        "excess_weight_kg": excess_kg,
        "excess_charge_inr": excess_fee,
        "excess_rate_per_kg": excess_rate,
        "critical_restrictions": restrictions,
        "recommendation": f"Pre-book extra baggage online at least 6 hours before departure to save up to 40% compared to airport gate excess rates." if excess_kg > 0 else "Your baggage is within the standard free allowance."
    })
