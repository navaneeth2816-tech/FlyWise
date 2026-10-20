from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, request, jsonify
from services.flight_service import search_flights, get_flight_seats, get_flight_status
from services.recommendation_service import score_and_rank_itineraries
from routes.auth_routes import get_current_user
from database import query_one, query_all

flight_bp = Blueprint('flights', __name__, url_prefix='/api/v1/flights')

@flight_bp.route('/search', methods=['GET'])
def search():
    origin = request.args.get('origin', '').strip().upper()
    destination = request.args.get('destination', '').strip().upper()
    departure_date = request.args.get('date', '').strip()
    return_date = request.args.get('return_date', '').strip()
    trip_type = request.args.get('trip_type', 'oneway').strip().lower()
    travel_class = request.args.get('class', 'economy').strip().lower()
    sort_by = request.args.get('sort_by', 'recommendation').strip()
    passengers = int(request.args.get('passengers', 1) or 1)
    max_stops = int(request.args.get('stops', 1))
    max_price = request.args.get('max_price')
    airline_filter = request.args.get('airline')
    departure_window = request.args.get('window')

    if not origin or not destination or not departure_date:
        return jsonify({
            "status": "error",
            "message": "Origin, destination, and departure date are required query parameters."
        }), 400

    if origin == destination:
        return jsonify({
            "status": "error",
            "message": "Departure and destination cannot be the same airport. Please select different cities."
        }), 400

    if trip_type == 'roundtrip' and return_date and return_date < departure_date:
        return jsonify({
            "status": "error",
            "message": "Return date cannot be earlier than departure date."
        }), 400

    def run_outbound():
        return search_flights(
            origin_code=origin,
            destination_code=destination,
            departure_date=departure_date,
            travel_class=travel_class,
            sort_by=sort_by if sort_by != 'recommendation' else 'price',
            max_stops=max_stops,
            max_price=max_price,
            airline_filter=airline_filter,
            departure_window=departure_window
        )

    def run_inbound():
        if trip_type == 'roundtrip' and return_date:
            return search_flights(
                origin_code=destination,
                destination_code=origin,
                departure_date=return_date,
                travel_class=travel_class,
                sort_by=sort_by if sort_by != 'recommendation' else 'price',
                max_stops=max_stops,
                max_price=max_price,
                airline_filter=airline_filter,
                departure_window=departure_window
            )
        return []

    # Run outbound and inbound searches concurrently if roundtrip
    if trip_type == 'roundtrip' and return_date:
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_out = pool.submit(run_outbound)
            f_in = pool.submit(run_inbound)
            itineraries = f_out.result()
            ret_raw = f_in.result()
    else:
        itineraries = run_outbound()
        ret_raw = []

    # Apply Personalized Recommendation Scoring
    user = get_current_user()
    user_prefs = {}
    if user:
        prefs = query_all("SELECT preference_type, preference_value FROM user_preferences WHERE user_id = %s;", (user['user_id'],))
        user_prefs = {p['preference_type']: p['preference_value'] for p in prefs}

    scored = score_and_rank_itineraries(itineraries, user_prefs)
    return_itineraries = score_and_rank_itineraries(ret_raw, user_prefs) if ret_raw else []

    # Re-sort if user explicitly selected a sorting option
    if sort_by == 'price':
        scored.sort(key=lambda x: x['total_fare'])
    elif sort_by == 'duration':
        scored.sort(key=lambda x: x['duration_minutes'])
    elif sort_by == 'total_cost':
        scored.sort(key=lambda x: x['estimated_journey_cost'])
    elif sort_by == 'earliest_departure':
        scored.sort(key=lambda x: x['departure_time'])
    elif sort_by == 'recommendation':
        scored.sort(key=lambda x: x['recommendation_score'], reverse=True)

    return jsonify({
        "status": "success",
        "search_parameters": {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date if trip_type == 'roundtrip' else None,
            "trip_type": trip_type,
            "passengers": passengers,
            "travel_class": travel_class,
            "sort_by": sort_by
        },
        "count": len(scored),
        "itineraries": scored,
        "return_count": len(return_itineraries),
        "return_itineraries": return_itineraries
    })

@flight_bp.route('/<int:flight_id>', methods=['GET'])
def get_flight(flight_id):
    flight = query_one("""
        SELECT f.*, al.airline_name, al.iata_code AS airline_code, al.support_information,
               ac.aircraft_model, ac.aircraft_code,
               orig.iata_code AS origin_code, orig.city AS origin_city, orig.airport_name AS origin_name,
               dest.iata_code AS destination_code, dest.city AS destination_city, dest.airport_name AS destination_name
        FROM flights f
        JOIN airlines al ON f.airline_id = al.airline_id
        JOIN aircraft ac ON f.aircraft_id = ac.aircraft_id
        JOIN airports orig ON f.origin_airport_id = orig.airport_id
        JOIN airports dest ON f.destination_airport_id = dest.airport_id
        WHERE f.flight_id = %s;
    """, (flight_id,))

    if not flight:
        return jsonify({"status": "error", "message": "Flight not found"}), 404

    fares = query_all("SELECT * FROM fares WHERE flight_id = %s;", (flight_id,))
    flight['fares'] = fares
    return jsonify({"status": "success", "flight": flight})

@flight_bp.route('/<int:flight_id>/seats', methods=['GET'])
def get_seats(flight_id):
    seats = get_flight_seats(flight_id)
    return jsonify({"status": "success", "flight_id": flight_id, "seats": seats})

@flight_bp.route('/<int:flight_id>/status', methods=['GET'])
def get_status(flight_id):
    st = get_flight_status(flight_id)
    if not st:
        return jsonify({"status": "error", "message": "Flight not found"}), 404
    return jsonify({"status": "success", "flight_status": st})
