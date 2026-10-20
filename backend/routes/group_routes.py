import json
from flask import Blueprint, request, jsonify
from routes.auth_routes import login_required
from database import query_all, query_one, execute_commit
from services.flight_service import search_flights
from services.recommendation_service import score_and_rank_itineraries

group_bp = Blueprint('groups', __name__, url_prefix='/api/v1/groups')

@group_bp.route('', methods=['POST'])
@login_required
def create_group(user):
    data = request.get_json() or {}
    group_name = data.get('group_name', '').strip()
    origin_code = data.get('origin', 'BLR').strip().upper()
    destination_code = data.get('destination', 'GOI').strip().upper()
    dep_date = data.get('departure_date', '2026-10-28')

    if not group_name:
        return jsonify({"status": "error", "message": "Group name is required."}), 400

    orig = query_one("SELECT airport_id FROM airports WHERE iata_code = %s;", (origin_code,))
    dest = query_one("SELECT airport_id FROM airports WHERE iata_code = %s;", (destination_code,))
    if not orig or not dest:
        return jsonify({"status": "error", "message": "Invalid origin or destination airport."}), 400

    group_id = execute_commit("""
        INSERT INTO group_trips (organiser_user_id, group_name, origin_airport_id, destination_airport_id, departure_date)
        VALUES (%s, %s, %s, %s, %s);
    """, (user['user_id'], group_name, orig['airport_id'], dest['airport_id'], dep_date))

    # Add organizer as first member
    execute_commit("""
        INSERT INTO group_members (group_trip_id, user_id, member_name, budget, travel_preferences, invitation_status)
        VALUES (%s, %s, %s, %s, %s, 'accepted');
    """, (group_id, user['user_id'], user['full_name'], 5000.0, json.dumps({"departure": "morning", "seat": "window"})))

    return jsonify({"status": "success", "group_trip_id": group_id, "message": "Group trip created."}), 201

@group_bp.route('', methods=['GET'])
@login_required
def get_user_groups(user):
    trips = query_all("""
        SELECT gt.*, u.full_name AS organiser_name,
               orig.iata_code AS origin_code, orig.city AS origin_city,
               dest.iata_code AS destination_code, dest.city AS destination_city,
               COUNT(gm.group_member_id) AS member_count
        FROM group_trips gt
        JOIN users u ON gt.organiser_user_id = u.user_id
        JOIN airports orig ON gt.origin_airport_id = orig.airport_id
        JOIN airports dest ON gt.destination_airport_id = dest.airport_id
        LEFT JOIN group_members gm ON gt.group_trip_id = gm.group_trip_id
        WHERE gt.organiser_user_id = %s OR gm.user_id = %s
        GROUP BY gt.group_trip_id;
    """, (user['user_id'], user['user_id']))
    return jsonify({"status": "success", "groups": trips})

@group_bp.route('/<int:group_id>', methods=['GET'])
@login_required
def get_group_details(user, group_id):
    trip = query_one("""
        SELECT gt.*, u.full_name AS organiser_name,
               orig.iata_code AS origin_code, orig.city AS origin_city,
               dest.iata_code AS destination_code, dest.city AS destination_city
        FROM group_trips gt
        JOIN users u ON gt.organiser_user_id = u.user_id
        JOIN airports orig ON gt.origin_airport_id = orig.airport_id
        JOIN airports dest ON gt.destination_airport_id = dest.airport_id
        WHERE gt.group_trip_id = %s;
    """, (group_id,))

    if not trip:
        return jsonify({"status": "error", "message": "Group trip not found."}), 404

    members = query_all("SELECT * FROM group_members WHERE group_trip_id = %s;", (group_id,))
    trip['members'] = members
    return jsonify({"status": "success", "group": trip})

@group_bp.route('/<int:group_id>/members', methods=['POST'])
@login_required
def add_member(user, group_id):
    data = request.get_json() or {}
    name = data.get('member_name', '').strip()
    budget = float(data.get('budget', 5000.0))
    pref = data.get('travel_preferences', {"departure": "morning", "seat": "window"})

    if not name:
        return jsonify({"status": "error", "message": "Member name is required."}), 400

    execute_commit("""
        INSERT INTO group_members (group_trip_id, member_name, budget, travel_preferences, invitation_status)
        VALUES (%s, %s, %s, %s, 'accepted');
    """, (group_id, name, budget, json.dumps(pref)))

    return jsonify({"status": "success", "message": f"{name} added to the group trip."})

@group_bp.route('/<int:group_id>/optimise', methods=['POST'])
@login_required
def optimise_group(user, group_id):
    """
    Optimizes group itinerary matching common budget and schedule constraints.
    PRD Section 19.
    """
    trip = query_one("""
        SELECT gt.*, orig.iata_code AS origin_code, dest.iata_code AS destination_code
        FROM group_trips gt
        JOIN airports orig ON gt.origin_airport_id = orig.airport_id
        JOIN airports dest ON gt.destination_airport_id = dest.airport_id
        WHERE gt.group_trip_id = %s;
    """, (group_id,))

    if not trip:
        return jsonify({"status": "error", "message": "Group trip not found."}), 404

    members = query_all("SELECT * FROM group_members WHERE group_trip_id = %s;", (group_id,))
    if not members:
        return jsonify({"status": "error", "message": "No members in group."}), 400

    budgets = [m['budget'] for m in members]
    min_budget = min(budgets)
    avg_budget = sum(budgets) / len(budgets)

    # Search available flights
    flights = search_flights(
        origin_code=trip['origin_code'],
        destination_code=trip['destination_code'],
        departure_date=trip['departure_date'].strftime("%Y-%m-%d") if hasattr(trip['departure_date'], 'strftime') else str(trip['departure_date']),
        max_stops=1
    )

    if not flights:
        return jsonify({
            "status": "success",
            "message": "No flights found on selected date.",
            "member_count": len(members),
            "suitable_flights": []
        })

    # Filter flights that fit within the minimum member budget (or close to it)
    suitable = []
    for f in flights:
        total_fare = f['total_fare']
        is_affordable_for_all = total_fare <= min_budget
        group_total = total_fare * len(members)

        suitable.append({
            "itinerary_id": f['itinerary_id'],
            "airline": f['airline_name'],
            "flight_number": f['segments'][0]['flight_number'],
            "departure_time": f['departure_time'],
            "arrival_time": f['arrival_time'],
            "duration": f"{f['duration_minutes'] // 60}h {f['duration_minutes'] % 60}m",
            "stops": f['stops'],
            "individual_fare_inr": total_fare,
            "group_total_inr": group_total,
            "affordable_for_all": is_affordable_for_all,
            "budget_status": "Fits all member budgets" if is_affordable_for_all else f"Exceeds lowest budget (₹{min_budget:,.0f}) by ₹{total_fare - min_budget:,.0f}"
        })

    suitable.sort(key=lambda x: (not x['affordable_for_all'], x['individual_fare_inr']))

    return jsonify({
        "status": "success",
        "group_name": trip['group_name'],
        "member_count": len(members),
        "min_member_budget_inr": min_budget,
        "avg_member_budget_inr": round(avg_budget, 2),
        "suitable_flights": suitable[:5]
    })
