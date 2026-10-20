from datetime import datetime
from database import query_all, query_one

def assess_connection_risk(itinerary):
    """
    Assesses connection risk for an itinerary using rule-based heuristics.
    Categorizes into LOW, MODERATE, HIGH with explainable factors.
    """
    stops = itinerary.get('stops', 0)
    if stops == 0:
        return {
            "risk_level": "LOW",
            "risk_score": 10,
            "category": "Direct Flight - Zero Connection Risk",
            "factors": [
                "Direct flight without any layover or transfer required.",
                "Zero risk of missed connections."
            ],
            "recommendation": "Optimal choice for seamless point-to-point journey."
        }

    conn_info = itinerary.get('connection_info', {})
    layover_min = conn_info.get('layover_minutes', 60)
    layover_airport = conn_info.get('layover_airport', 'BLR')
    same_airline = conn_info.get('same_airline', True)

    risk_score = 30
    factors = []

    # 1. Layover duration analysis
    if layover_min < 45:
        risk_score += 50
        factors.append(f"Layover window of only {layover_min} minutes is dangerously tight (minimum recommended is 60 minutes).")
    elif layover_min < 75:
        risk_score += 25
        factors.append(f"Layover window of {layover_min} minutes is moderate. A minor delay on the first flight could cause boarding stress.")
    else:
        risk_score -= 10
        factors.append(f"Comfortable layover window of {layover_min} minutes allows buffer for baggage transfer and security.")

    # 2. Inter-terminal transfer risks
    if layover_airport in ['BOM', 'DEL']:
        risk_score += 15
        factors.append(f"Airport {layover_airport} has separate domestic/international terminals; inter-terminal transfers require extra transit time.")

    # 3. Interline / Separate tickets
    if not same_airline:
        risk_score += 20
        factors.append("Itinerary involves two different airlines. In case of missed connection, rebooking protections may not automatically apply.")

    # Categorize
    if risk_score >= 65:
        risk_level = "HIGH"
        category = "High Connection Risk"
        rec = "Consider choosing a direct flight or an itinerary with a layover of at least 90 minutes."
    elif risk_score >= 40:
        risk_level = "MODERATE"
        category = "Moderate Connection Risk"
        rec = "Manageable connection, but ensure prompt disembarkation at the layover airport."
    else:
        risk_level = "LOW"
        category = "Low Connection Risk"
        rec = "Safe connection buffer provided under normal operating conditions."

    return {
        "risk_level": risk_level,
        "risk_score": min(100, max(0, risk_score)),
        "category": category,
        "layover_minutes": layover_min,
        "layover_airport": layover_airport,
        "factors": factors,
        "recommendation": rec
    }

def find_recovery_options(flight_id):
    """
    Estimates practical alternative recovery options available in the schedule.
    Demonstrates disruption mitigation per PRD Section 12 & 13.
    """
    flight = query_one("""
        SELECT f.*, orig.iata_code AS orig_code, dest.iata_code AS dest_code
        FROM flights f
        JOIN airports orig ON f.origin_airport_id = orig.airport_id
        JOIN airports dest ON f.destination_airport_id = dest.airport_id
        WHERE f.flight_id = %s;
    """, (flight_id,))

    if not flight:
        return {"status": "error", "message": "Flight not found"}

    dep_time = flight['scheduled_departure']
    # Find later flights on the same day or next day on the same route
    alternatives = query_all("""
        SELECT f.flight_id, f.flight_number, f.scheduled_departure, f.scheduled_arrival,
               al.airline_name, al.iata_code AS airline_code,
               COALESCE(fa.base_fare, 4500) AS base_fare,
               COUNT(CASE WHEN s.seat_status = 'available' THEN 1 END) AS available_seats
        FROM flights f
        JOIN airlines al ON f.airline_id = al.airline_id
        LEFT JOIN fares fa ON f.flight_id = fa.flight_id
        LEFT JOIN seats s ON f.flight_id = s.flight_id
        WHERE f.origin_airport_id = %s
          AND f.destination_airport_id = %s
          AND f.flight_id != %s
          AND f.scheduled_departure >= %s
          AND f.scheduled_departure <= DATE_ADD(%s, INTERVAL 24 HOUR)
        GROUP BY f.flight_id, fa.fare_id
        ORDER BY f.scheduled_departure ASC
        LIMIT 5;
    """, (flight['origin_airport_id'], flight['destination_airport_id'], flight_id, dep_time, dep_time))

    count = len(alternatives)
    if count >= 3:
        assessment = "More recovery options identified"
        summary = f"{count} alternative flights departing within 24 hours on this route."
    elif count >= 1:
        assessment = "Some recovery options identified"
        summary = f"{count} alternative flights available later today."
    else:
        assessment = "Limited recovery options identified"
        summary = "No immediate same-route alternative within 24 hours. May require alternative airport routing."

    return {
        "assessment": assessment,
        "count": count,
        "summary": summary,
        "affected_flight": flight['flight_number'],
        "alternatives": alternatives
    }
