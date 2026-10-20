import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, request, jsonify
from database import query_all, query_one
from services.flight_service import search_flights

simulation_bp = Blueprint('simulation', __name__, url_prefix='/api/v1/simulation')

@simulation_bp.route('/alternatives', methods=['POST'])
def simulate_dates():
    """
    What-If Simulator: compares alternative dates (-3 to +3 days) concurrently.
    PRD Section 14.
    """
    data = request.get_json() or {}
    origin = data.get('origin', 'TIR').strip().upper()
    destination = data.get('destination', 'DEL').strip().upper()
    base_date_str = data.get('departure_date', '2026-10-23').strip()
    travel_class = (data.get('travel_class') or data.get('class') or 'economy').strip().lower()

    try:
        base_dt = datetime.strptime(base_date_str, "%Y-%m-%d")
    except Exception:
        base_dt = datetime(2026, 10, 23)
        base_date_str = "2026-10-23"

    day_shifts = [-3, -2, -1, 0, 1, 2, 3]

    def evaluate_shift(shift):
        check_dt = base_dt + timedelta(days=shift)
        date_str = check_dt.strftime("%Y-%m-%d")
        flights = []
        try:
            flights = search_flights(origin, destination, date_str, travel_class=travel_class, max_stops=1) or []
        except Exception as fe:
            print(f"Simulation search_flights error for {date_str}: {fe}")
            flights = []

        if flights:
            cheapest = min(flights, key=lambda x: x['total_fare'])
            fastest = min(flights, key=lambda x: x['duration_minutes'])
            return {
                "date": date_str,
                "day_name": check_dt.strftime("%a, %b %d"),
                "shift_days": shift,
                "flight_count": len(flights),
                "is_live_schedule": True,
                "price_type": "live_schedule",
                "lowest_fare": float(cheapest['total_fare']),
                "cheapest_flight": {
                    "airline": cheapest['airline_name'],
                    "flight_number": cheapest['segments'][0]['flight_number'],
                    "departure": cheapest['departure_time'],
                    "stops": cheapest['stops'],
                    "duration_minutes": cheapest['duration_minutes']
                },
                "fastest_duration_minutes": fastest['duration_minutes']
            }
        else:
            base_class_factor = 2.2 if travel_class == 'business' else 1.0
            est_fare = float(round((5200 + (abs(shift) * 250)) * base_class_factor))
            return {
                "date": date_str,
                "day_name": check_dt.strftime("%a, %b %d"),
                "shift_days": shift,
                "flight_count": 0,
                "is_live_schedule": False,
                "price_type": "estimated_trend",
                "lowest_fare": est_fare,
                "cheapest_flight": None,
                "fastest_duration_minutes": 165
            }

    with ThreadPoolExecutor(max_workers=7) as executor:
        timeline = list(executor.map(evaluate_shift, day_shifts))

    # Compare baseline (shift 0) with other dates in timeline
    baseline_entry = next((t for t in timeline if t['shift_days'] == 0), None)
    baseline_fare = baseline_entry['lowest_fare'] if baseline_entry else 5800.0

    # Calculate exact fare difference for each date
    for t in timeline:
        t['fare_difference'] = float(t['lowest_fare'] - baseline_fare)

    best_option = min(timeline, key=lambda x: x['lowest_fare'])
    savings = float(baseline_fare - best_option['lowest_fare'])

    insights = []
    if savings > 0 and best_option['shift_days'] != 0:
        dir_label = f"{abs(best_option['shift_days'])} days earlier" if best_option['shift_days'] < 0 else f"{best_option['shift_days']} days later"
        insights.append(f"Travelling on {best_option['day_name']} ({dir_label}) can save ~₹{savings:,.0f} compared to {base_date_str}.")
    elif any(t['flight_count'] > 0 for t in timeline):
        live_options = [t for t in timeline if t['flight_count'] > 0]
        insights.append(f"Found active scheduled flights on {len(live_options)} alternate dates around your selection.")
    else:
        insights.append("Historical price trends indicate weekday departures (Tue-Thu) typically offer lower fares on this route.")

    return jsonify({
        "status": "success",
        "origin": origin,
        "destination": destination,
        "base_date": base_date_str,
        "travel_class": travel_class,
        "baseline_fare": baseline_fare,
        "max_savings_inr": max(0.0, savings),
        "best_date": best_option['date'],
        "timeline": timeline,
        "alternatives": timeline,
        "insights": insights
    })

@simulation_bp.route('/airports', methods=['POST'])
def simulate_airports():
    """
    Smart Alternative-Airport Finder with concurrent nearby airport searches.
    PRD Section 15: Compares nearby airport options with ground transport costs and travel times.
    """
    data = request.get_json() or {}
    origin = data.get('origin', 'TIR').strip().upper()
    destination = data.get('destination', 'DEL').strip().upper()
    dep_date = data.get('departure_date', '2026-10-23').strip()

    # Get airport details
    orig_airport = query_one("SELECT * FROM airports WHERE iata_code = %s;", (origin,))
    if not orig_airport:
        return jsonify({"status": "error", "message": "Origin airport not found"}), 404

    term_info = orig_airport['terminal_information']
    if isinstance(term_info, str):
        term_info = json.loads(term_info)
    nearby = term_info.get('nearby_alternatives', [])

    # Search primary and alternative flights concurrently
    def fetch_primary():
        return search_flights(origin, destination, dep_date, max_stops=1)

    def fetch_alt(alt):
        alt_code = alt['airport']
        flights = search_flights(alt_code, destination, dep_date, max_stops=1)
        cheapest = min(flights, key=lambda x: x['total_fare']) if flights else None
        return alt, cheapest

    with ThreadPoolExecutor(max_workers=max(1, len(nearby) + 1)) as executor:
        primary_future = executor.submit(fetch_primary)
        alt_futures = [executor.submit(fetch_alt, alt) for alt in nearby]
        
        primary_flights = primary_future.result()
        alt_results = [f.result() for f in alt_futures]

    primary_cheapest = min(primary_flights, key=lambda x: x['total_fare']) if primary_flights else None
    alternatives_analysis = []

    for alt, alt_cheapest in alt_results:
        if alt_cheapest:
            alt_code = alt['airport']
            flight_fare = alt_cheapest['total_fare']
            cab_cost = alt.get('est_cab_inr', 2500)
            road_hrs = alt.get('road_hrs', 3.5)
            
            alt_total_cost = flight_fare + cab_cost
            primary_total_cost = (primary_cheapest['total_fare'] + 500) if primary_cheapest else 99999
            net_difference = primary_total_cost - alt_total_cost

            recommendation = ""
            if net_difference > 1000:
                recommendation = f"Favorable: Saves ₹{net_difference:,.0f} overall even after including ₹{cab_cost} ground cab transit."
            elif net_difference > 0:
                recommendation = f"Marginal savings of ₹{net_difference:,.0f}, but adds {road_hrs}h road travel. Recommended only if flight times are more convenient."
            else:
                recommendation = f"Not recommended: Flying directly from {origin} is cheaper and saves {road_hrs}h ground travel."

            alternatives_analysis.append({
                "alternative_airport_code": alt_code,
                "distance_km": alt.get('distance_km'),
                "road_travel_hours": road_hrs,
                "ground_cab_cost_inr": cab_cost,
                "flight_fare_inr": flight_fare,
                "total_journey_cost_inr": alt_total_cost,
                "net_savings_vs_primary": net_difference,
                "cheapest_flight": alt_cheapest,
                "recommendation": recommendation
            })

    return jsonify({
        "status": "success",
        "primary_origin": origin,
        "destination": destination,
        "departure_date": dep_date,
        "primary_cheapest_fare": primary_cheapest['total_fare'] if primary_cheapest else None,
        "nearby_airports_evaluated": len(alternatives_analysis),
        "alternatives": alternatives_analysis
    })
