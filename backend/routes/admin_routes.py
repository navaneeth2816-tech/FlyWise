from flask import Blueprint, request, jsonify
from routes.auth_routes import admin_required
from database import query_all, query_one, execute_commit

admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1/admin')

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard_stats(user):
    """Administrative overview metrics."""
    counts = query_one("""
        SELECT 
            (SELECT COUNT(*) FROM users) AS total_users,
            (SELECT COUNT(*) FROM flights) AS total_flights,
            (SELECT COUNT(*) FROM bookings) AS total_bookings,
            (SELECT COALESCE(SUM(total_amount), 0) FROM bookings WHERE booking_status = 'confirmed') AS total_revenue,
            (SELECT COUNT(*) FROM aircraft WHERE status = 'active') AS active_aircraft,
            (SELECT COUNT(*) FROM airports) AS total_airports,
            (SELECT COUNT(*) FROM ai_usage_logs) AS total_ai_requests;
    """)
    recent_bookings = query_all("SELECT * FROM v_booking_summaries ORDER BY booking_date DESC LIMIT 5;")
    airline_perf = query_all("SELECT * FROM v_airline_performance;")

    return jsonify({
        "status": "success",
        "counts": counts,
        "recent_bookings": recent_bookings,
        "airline_performance": airline_perf
    })

@admin_bp.route('/flights', methods=['POST'])
@admin_required
def create_flight(user):
    data = request.get_json() or {}
    airline_id = data.get('airline_id')
    aircraft_id = data.get('aircraft_id')
    flight_number = data.get('flight_number', '').strip().upper()
    origin_airport_id = data.get('origin_airport_id')
    destination_airport_id = data.get('destination_airport_id')
    scheduled_departure = data.get('scheduled_departure')
    scheduled_arrival = data.get('scheduled_arrival')
    base_fare = float(data.get('base_fare', 4500.0))

    if not (airline_id and aircraft_id and flight_number and origin_airport_id and destination_airport_id and scheduled_departure and scheduled_arrival):
        return jsonify({"status": "error", "message": "All flight schedule fields are required."}), 400

    flight_id = execute_commit("""
        INSERT INTO flights (airline_id, aircraft_id, flight_number, origin_airport_id, destination_airport_id, scheduled_departure, scheduled_arrival, flight_status, data_source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'scheduled', 'admin_console');
    """, (airline_id, aircraft_id, flight_number, origin_airport_id, destination_airport_id, scheduled_departure, scheduled_arrival))

    # Create default fare
    taxes = round(base_fare * 0.12, 2)
    fees = 250.0
    execute_commit("""
        INSERT INTO fares (flight_id, travel_class, fare_type, base_fare, taxes, mandatory_fees, currency, valid_from, valid_until)
        VALUES (%s, 'economy', 'standard', %s, %s, %s, 'INR', NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY));
    """, (flight_id, base_fare, taxes, fees))

    return jsonify({"status": "success", "flight_id": flight_id, "message": "Flight created successfully."}), 201

@admin_bp.route('/flights/<int:flight_id>', methods=['PATCH'])
@admin_required
def update_flight_status(user, flight_id):
    """
    Updates flight status or times.
    Triggers MySQL trigger trg_after_flight_status_update which logs to flight_status_history!
    """
    data = request.get_json() or {}
    new_status = data.get('flight_status')
    actual_dep = data.get('actual_departure')
    actual_arr = data.get('actual_arrival')

    fields = []
    params = []

    if new_status:
        fields.append("flight_status = %s")
        params.append(new_status)
    if actual_dep:
        fields.append("actual_departure = %s")
        params.append(actual_dep)
    if actual_arr:
        fields.append("actual_arrival = %s")
        params.append(actual_arr)

    if not fields:
        return jsonify({"status": "error", "message": "No update fields provided."}), 400

    params.append(flight_id)
    execute_commit(f"UPDATE flights SET {', '.join(fields)} WHERE flight_id = %s;", tuple(params))

    return jsonify({"status": "success", "message": f"Flight {flight_id} updated. Trigger executed."})

@admin_bp.route('/bookings', methods=['GET'])
@admin_required
def get_all_bookings(user):
    bookings = query_all("SELECT * FROM v_booking_summaries ORDER BY booking_date DESC LIMIT 50;")
    return jsonify({"status": "success", "bookings": bookings})

@admin_bp.route('/ai-usage', methods=['GET'])
@admin_required
def get_ai_usage(user):
    logs = query_all("SELECT * FROM ai_usage_logs ORDER BY created_at DESC LIMIT 50;")
    summary = query_one("""
        SELECT 
            COUNT(*) AS total_calls,
            ROUND(AVG(latency_ms), 1) AS avg_latency_ms,
            COUNT(CASE WHEN request_status = 'success' THEN 1 END) AS successful_calls,
            COUNT(CASE WHEN request_status != 'success' THEN 1 END) AS failed_calls
        FROM ai_usage_logs;
    """)
    return jsonify({"status": "success", "summary": summary, "logs": logs})

@admin_bp.route('/analytics', methods=['GET'])
@admin_required
def get_analytics(user):
    """Formatted datasets ready for Chart.js rendering."""
    # 1. Bookings by airline
    airline_shares = query_all("""
        SELECT al.airline_name, COUNT(b.booking_id) AS booking_count
        FROM airlines al
        JOIN flights f ON al.airline_id = f.airline_id
        JOIN booking_segments bs ON f.flight_id = bs.flight_id
        JOIN bookings b ON bs.booking_id = b.booking_id
        GROUP BY al.airline_id;
    """)

    # 2. Status distribution
    status_dist = query_all("""
        SELECT flight_status, COUNT(*) AS count
        FROM flights
        GROUP BY flight_status;
    """)

    # 3. Revenue by Route
    route_rev = query_all("SELECT * FROM v_route_analytics LIMIT 6;")

    # 4. AI Latency trend
    ai_trend = query_all("""
        SELECT DATE_FORMAT(created_at, '%H:%i') AS time_label, latency_ms
        FROM ai_usage_logs
        ORDER BY created_at DESC LIMIT 15;
    """)

    return jsonify({
        "status": "success",
        "charts": {
            "airline_bookings": {
                "labels": [a['airline_name'] for a in airline_shares] or ["IndiGo", "Air India", "Vistara"],
                "data": [a['booking_count'] for a in airline_shares] or [4, 2, 1]
            },
            "status_distribution": {
                "labels": [s['flight_status'] for s in status_dist],
                "data": [s['count'] for s in status_dist]
            },
            "route_analytics": route_rev,
            "ai_latency_trend": {
                "labels": [t['time_label'] for t in reversed(ai_trend)],
                "data": [t['latency_ms'] for t in reversed(ai_trend)]
            }
        }
    })
