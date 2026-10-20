from flask import Blueprint, request, jsonify
from services.cost_service import calculate_journey_cost, compare_journey_costs

journey_cost_bp = Blueprint('journey_cost', __name__, url_prefix='/api/v1/journey-cost')

@journey_cost_bp.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json() or {}
    flight_id = data.get('flight_id')
    base_fare = data.get('base_fare')
    origin_code = data.get('origin_code', 'DEL')
    destination_code = data.get('destination_code', 'BOM')
    baggage_kg = int(data.get('baggage_kg', 15))
    seat_type = data.get('seat_type', 'standard_window')
    ground_transport = data.get('ground_transport', 'cab')
    add_ons = data.get('add_ons', [])

    breakdown = calculate_journey_cost(
        flight_id=flight_id,
        base_fare=base_fare,
        origin_code=origin_code,
        destination_code=destination_code,
        baggage_kg=baggage_kg,
        seat_type=seat_type,
        ground_transport=ground_transport,
        add_ons=add_ons
    )
    return jsonify({"status": "success", "cost_breakdown": breakdown})

@journey_cost_bp.route('/compare', methods=['POST'])
def compare():
    data = request.get_json() or {}
    itineraries = data.get('itineraries', [])
    ground_transport = data.get('ground_transport', 'cab')
    results = compare_journey_costs(itineraries, ground_transport=ground_transport)
    return jsonify({"status": "success", "comparison": results})
