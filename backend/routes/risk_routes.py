from flask import Blueprint, request, jsonify
from services.risk_service import assess_connection_risk, find_recovery_options

risk_bp = Blueprint('risk', __name__, url_prefix='/api/v1/risk')

@risk_bp.route('/assess', methods=['POST'])
def assess():
    data = request.get_json() or {}
    itinerary = data.get('itinerary', {})
    res = assess_connection_risk(itinerary)
    return jsonify({"status": "success", "risk_assessment": res})

@risk_bp.route('/recovery-options', methods=['POST'])
def recovery():
    data = request.get_json() or {}
    flight_id = data.get('flight_id')
    if not flight_id:
        return jsonify({"status": "error", "message": "flight_id is required."}), 400
    res = find_recovery_options(flight_id)
    return jsonify({"status": "success", "recovery_options": res})
