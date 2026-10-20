import json
from flask import Blueprint, request, jsonify
from database import query_all, query_one

airport_bp = Blueprint('airports', __name__, url_prefix='/api/v1/airports')

@airport_bp.route('', methods=['GET'])
def list_airports():
    airports = query_all("SELECT airport_id, iata_code, icao_code, airport_name, city, country, terminal_information FROM airports ORDER BY city ASC;")
    return jsonify({"status": "success", "airports": airports})

@airport_bp.route('/<string:code>/information', methods=['GET'])
def get_airport_info(code):
    airport = query_one("SELECT * FROM airports WHERE iata_code = %s;", (code.upper(),))
    if not airport:
        return jsonify({"status": "error", "message": "Airport not found"}), 404
    
    term_info = airport['terminal_information']
    if isinstance(term_info, str):
        try:
            term_info = json.loads(term_info)
        except Exception:
            term_info = {}

    airport['terminal_information'] = term_info
    return jsonify({"status": "success", "airport": airport})

@airport_bp.route('/<string:code>/accessibility', methods=['GET'])
def get_accessibility_info(code):
    """Accessible Journey Planner: PRD Section 22."""
    airport = query_one("SELECT iata_code, airport_name, city, terminal_information FROM airports WHERE iata_code = %s;", (code.upper(),))
    if not airport:
        return jsonify({"status": "error", "message": "Airport not found"}), 404

    term_info = airport['terminal_information']
    if isinstance(term_info, str):
        try:
            term_info = json.loads(term_info)
        except Exception:
            term_info = {}

    accessibility_features = {
        "airport_code": airport['iata_code'],
        "airport_name": airport['airport_name'],
        "city": airport['city'],
        "wheelchair_available": term_info.get('wheelchair_support', True),
        "meet_and_assist": term_info.get('meet_and_assist', True),
        "accessible_washrooms": "Dedicated, braille-signed, wide-door accessible restrooms at every boarding concourse.",
        "ramps_and_elevators": "Braille-equipped lifts and zero-step tactile boarding ramps to all departure gates.",
        "special_assistance_counter": "Located immediately upon entry at Gate 1 / Departure concourse.",
        "airline_notification_window": "Request wheelchair or blind/deaf assistance at least 48 hours prior to flight departure."
    }

    return jsonify({"status": "success", "accessibility": accessibility_features})
