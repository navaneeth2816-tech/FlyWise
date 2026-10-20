import json
from datetime import datetime, timedelta
from database import query_all, query_one, get_db_cursor

def search_flights(origin_code, destination_code, departure_date, travel_class='economy', sort_by='price', max_stops=1, max_price=None, airline_filter=None, departure_window=None):
    """
    Intelligent Flight Search supporting both direct and 1-stop connecting flights.
    Demonstrates multi-table relational joins, subqueries, and date filtering.
    """
    origin_code = origin_code.strip().upper()
    destination_code = destination_code.strip().upper()
    departure_date = departure_date.strip()

    # 1. Search Direct Flights
    direct_query = """
        SELECT 
            f.flight_id,
            f.flight_number,
            f.flight_status,
            f.scheduled_departure,
            f.scheduled_arrival,
            f.actual_departure,
            f.actual_arrival,
            TIMESTAMPDIFF(MINUTE, f.scheduled_departure, f.scheduled_arrival) AS duration_minutes,
            al.airline_id,
            al.airline_name,
            al.iata_code AS airline_code,
            al.support_information,
            ac.aircraft_code,
            ac.aircraft_model,
            orig.airport_id AS origin_airport_id,
            orig.iata_code AS origin_code,
            orig.airport_name AS origin_name,
            orig.city AS origin_city,
            dest.airport_id AS destination_airport_id,
            dest.iata_code AS destination_code,
            dest.airport_name AS destination_name,
            dest.city AS destination_city,
            COALESCE(fa.fare_id, 0) AS fare_id,
            COALESCE(fa.fare_type, 'saver') AS fare_type,
            COALESCE(fa.base_fare, 4200.00) AS base_fare,
            COALESCE(fa.taxes, 500.00) AS taxes,
            COALESCE(fa.mandatory_fees, 250.00) AS mandatory_fees,
            (COALESCE(fa.base_fare, 4200.00) + COALESCE(fa.taxes, 500.00) + COALESCE(fa.mandatory_fees, 250.00)) AS total_fare,
            COALESCE(fa.currency, 'INR') AS currency,
            COALESCE(fa.fare_conditions, '{}') AS fare_conditions,
            COUNT(CASE WHEN s.seat_status = 'available' THEN 1 END) AS available_seats
        FROM flights f
        JOIN airlines al ON f.airline_id = al.airline_id
        JOIN aircraft ac ON f.aircraft_id = ac.aircraft_id
        JOIN airports orig ON f.origin_airport_id = orig.airport_id
        JOIN airports dest ON f.destination_airport_id = dest.airport_id
        LEFT JOIN fares fa ON f.flight_id = fa.flight_id AND fa.travel_class = %s
        LEFT JOIN seats s ON f.flight_id = s.flight_id
        WHERE orig.iata_code = %s
          AND dest.iata_code = %s
          AND DATE(f.scheduled_departure) = %s
        GROUP BY f.flight_id, fa.fare_id
    """
    
    direct_rows = query_all(direct_query, (travel_class, origin_code, destination_code, departure_date))
    itineraries = []

    for r in direct_rows:
        conditions = r['fare_conditions']
        if isinstance(conditions, str):
            try:
                conditions = json.loads(conditions)
            except Exception:
                conditions = {}

        itinerary = {
            "itinerary_id": f"dir_{r['flight_id']}",
            "is_direct": True,
            "stops": 0,
            "segments": [{
                "flight_id": r['flight_id'],
                "flight_number": r['flight_number'],
                "airline_id": r['airline_id'],
                "airline_name": r['airline_name'],
                "airline_code": r['airline_code'],
                "aircraft_model": r['aircraft_model'],
                "origin_code": r['origin_code'],
                "origin_city": r['origin_city'],
                "destination_code": r['destination_code'],
                "destination_city": r['destination_city'],
                "scheduled_departure": r['scheduled_departure'],
                "scheduled_arrival": r['scheduled_arrival'],
                "duration_minutes": r['duration_minutes'],
                "flight_status": r['flight_status'],
                "fare_id": r['fare_id'],
                "available_seats": r['available_seats'] or 12
            }],
            "origin_code": r['origin_code'],
            "origin_city": r['origin_city'],
            "destination_code": r['destination_code'],
            "destination_city": r['destination_city'],
            "departure_time": r['scheduled_departure'],
            "arrival_time": r['scheduled_arrival'],
            "duration_minutes": r['duration_minutes'],
            "base_fare": r['base_fare'],
            "taxes": r['taxes'],
            "mandatory_fees": r['mandatory_fees'],
            "total_fare": r['total_fare'],
            "currency": r['currency'],
            "travel_class": travel_class,
            "airline_name": r['airline_name'],
            "airline_code": r['airline_code'],
            "available_seats": r['available_seats'] or 12,
            "fare_conditions": conditions,
            "connection_info": None
        }
        itineraries.append(itinerary)

    # 2. Search 1-Stop Connecting Flights if allowed
    if max_stops >= 1:
        connecting_query = """
            SELECT 
                f1.flight_id AS f1_id, f1.flight_number AS f1_num, f1.flight_status AS f1_status,
                f1.scheduled_departure AS f1_dep, f1.scheduled_arrival AS f1_arr,
                TIMESTAMPDIFF(MINUTE, f1.scheduled_departure, f1.scheduled_arrival) AS f1_duration,
                al1.airline_name AS f1_airline, al1.iata_code AS f1_airline_code,
                orig.iata_code AS orig_code, orig.city AS orig_city,
                mid.iata_code AS mid_code, mid.city AS mid_city, mid.terminal_information AS mid_terminal,
                
                f2.flight_id AS f2_id, f2.flight_number AS f2_num, f2.flight_status AS f2_status,
                f2.scheduled_departure AS f2_dep, f2.scheduled_arrival AS f2_arr,
                TIMESTAMPDIFF(MINUTE, f2.scheduled_departure, f2.scheduled_arrival) AS f2_duration,
                al2.airline_name AS f2_airline, al2.iata_code AS f2_airline_code,
                dest.iata_code AS dest_code, dest.city AS dest_city,
                
                TIMESTAMPDIFF(MINUTE, f1.scheduled_arrival, f2.scheduled_departure) AS layover_minutes,
                TIMESTAMPDIFF(MINUTE, f1.scheduled_departure, f2.scheduled_arrival) AS total_duration_minutes,
                
                COALESCE(fa1.base_fare, 2800) + COALESCE(fa2.base_fare, 3200) AS total_base_fare,
                COALESCE(fa1.taxes, 400) + COALESCE(fa2.taxes, 450) AS total_taxes,
                COALESCE(fa1.mandatory_fees, 200) + COALESCE(fa2.mandatory_fees, 200) AS total_fees
            FROM flights f1
            JOIN flights f2 ON f1.destination_airport_id = f2.origin_airport_id
            JOIN airlines al1 ON f1.airline_id = al1.airline_id
            JOIN airlines al2 ON f2.airline_id = al2.airline_id
            JOIN airports orig ON f1.origin_airport_id = orig.airport_id
            JOIN airports mid ON f1.destination_airport_id = mid.airport_id
            JOIN airports dest ON f2.destination_airport_id = dest.airport_id
            LEFT JOIN fares fa1 ON f1.flight_id = fa1.flight_id AND fa1.travel_class = %s
            LEFT JOIN fares fa2 ON f2.flight_id = fa2.flight_id AND fa2.travel_class = %s
            WHERE orig.iata_code = %s
              AND dest.iata_code = %s
              AND DATE(f1.scheduled_departure) = %s
              AND f2.scheduled_departure > f1.scheduled_arrival
              AND TIMESTAMPDIFF(MINUTE, f1.scheduled_arrival, f2.scheduled_departure) BETWEEN 50 AND 360
            LIMIT 15;
        """
        conn_rows = query_all(connecting_query, (travel_class, travel_class, origin_code, destination_code, departure_date))
        for cr in conn_rows:
            tot_fare = cr['total_base_fare'] + cr['total_taxes'] + cr['total_fees']
            itinerary = {
                "itinerary_id": f"conn_{cr['f1_id']}_{cr['f2_id']}",
                "is_direct": False,
                "stops": 1,
                "segments": [
                    {
                        "flight_id": cr['f1_id'],
                        "flight_number": cr['f1_num'],
                        "airline_name": cr['f1_airline'],
                        "airline_code": cr['f1_airline_code'],
                        "origin_code": cr['orig_code'],
                        "origin_city": cr['orig_city'],
                        "destination_code": cr['mid_code'],
                        "destination_city": cr['mid_city'],
                        "scheduled_departure": cr['f1_dep'],
                        "scheduled_arrival": cr['f1_arr'],
                        "duration_minutes": cr['f1_duration'],
                        "flight_status": cr['f1_status']
                    },
                    {
                        "flight_id": cr['f2_id'],
                        "flight_number": cr['f2_num'],
                        "airline_name": cr['f2_airline'],
                        "airline_code": cr['f2_airline_code'],
                        "origin_code": cr['mid_code'],
                        "origin_city": cr['mid_city'],
                        "destination_code": cr['dest_code'],
                        "destination_city": cr['dest_city'],
                        "scheduled_departure": cr['f2_dep'],
                        "scheduled_arrival": cr['f2_arr'],
                        "duration_minutes": cr['f2_duration'],
                        "flight_status": cr['f2_status']
                    }
                ],
                "origin_code": cr['orig_code'],
                "origin_city": cr['orig_city'],
                "destination_code": cr['dest_code'],
                "destination_city": cr['dest_city'],
                "departure_time": cr['f1_dep'],
                "arrival_time": cr['f2_arr'],
                "duration_minutes": cr['total_duration_minutes'],
                "base_fare": cr['total_base_fare'],
                "taxes": cr['total_taxes'],
                "mandatory_fees": cr['total_fees'],
                "total_fare": tot_fare,
                "currency": 'INR',
                "travel_class": travel_class,
                "airline_name": f"{cr['f1_airline']} + {cr['f2_airline']}" if cr['f1_airline'] != cr['f2_airline'] else cr['f1_airline'],
                "airline_code": cr['f1_airline_code'],
                "available_seats": 10,
                "fare_conditions": {"cabin_baggage": "7 kg", "checkin_baggage": "15 kg", "refundable": False},
                "connection_info": {
                    "layover_airport": cr['mid_code'],
                    "layover_city": cr['mid_city'],
                    "layover_minutes": cr['layover_minutes'],
                    "same_airline": cr['f1_airline'] == cr['f2_airline']
                }
            }
            itineraries.append(itinerary)

    # 3. Apply Filters
    if max_price:
        try:
            itineraries = [it for it in itineraries if it['total_fare'] <= float(max_price)]
        except Exception:
            pass

    if airline_filter:
        itineraries = [it for it in itineraries if airline_filter.lower() in it['airline_name'].lower() or airline_filter.upper() == it['airline_code']]

    if departure_window:
        # e.g., 'morning' (06:00-12:00), 'afternoon' (12:00-18:00), 'evening' (18:00-24:00)
        filtered = []
        for it in itineraries:
            dep_hour = datetime.fromisoformat(it['departure_time']).hour
            if departure_window == 'morning' and 5 <= dep_hour < 12:
                filtered.append(it)
            elif departure_window == 'afternoon' and 12 <= dep_hour < 18:
                filtered.append(it)
            elif departure_window == 'evening' and (18 <= dep_hour <= 23 or dep_hour < 5):
                filtered.append(it)
        if filtered:
            itineraries = filtered

    # 4. Sorting
    if sort_by == 'price':
        itineraries.sort(key=lambda x: x['total_fare'])
    elif sort_by == 'duration':
        itineraries.sort(key=lambda x: x['duration_minutes'])
    elif sort_by == 'earliest_departure':
        itineraries.sort(key=lambda x: x['departure_time'])
    elif sort_by == 'earliest_arrival':
        itineraries.sort(key=lambda x: x['arrival_time'])
    elif sort_by == 'stops':
        itineraries.sort(key=lambda x: x['stops'])

    return itineraries

def get_flight_seats(flight_id):
    """Retrieves all seats for a flight, creating default set if not populated."""
    seats = query_all("SELECT seat_id, flight_id, seat_number, travel_class, seat_status FROM seats WHERE flight_id = %s ORDER BY seat_number ASC;", (flight_id,))
    if not seats:
        # Generate default seat layout if none exist for this specific instance
        with get_db_cursor(commit=True) as cur:
            for r in range(1, 7):
                t_class = 'business' if r == 1 else 'economy'
                for c in ['A', 'B', 'C', 'D', 'E', 'F']:
                    cur.execute("INSERT IGNORE INTO seats (flight_id, seat_number, travel_class, seat_status) VALUES (%s, %s, %s, 'available');", (flight_id, f"{r}{c}", t_class))
        seats = query_all("SELECT seat_id, flight_id, seat_number, travel_class, seat_status FROM seats WHERE flight_id = %s ORDER BY seat_number ASC;", (flight_id,))
    return seats

def get_flight_status(flight_id):
    """Gets real-time status and history log of a flight."""
    flight = query_one("""
        SELECT f.*, al.airline_name, al.iata_code AS airline_code,
               orig.iata_code AS origin_code, orig.city AS origin_city,
               dest.iata_code AS destination_code, dest.city AS destination_city
        FROM flights f
        JOIN airlines al ON f.airline_id = al.airline_id
        JOIN airports orig ON f.origin_airport_id = orig.airport_id
        JOIN airports dest ON f.destination_airport_id = dest.airport_id
        WHERE f.flight_id = %s;
    """, (flight_id,))
    
    if not flight:
        return None

    history = query_all("""
        SELECT * FROM flight_status_history 
        WHERE flight_id = %s ORDER BY recorded_at DESC;
    """, (flight_id,))

    flight['history'] = history
    return flight
