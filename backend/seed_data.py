import os
import sys
import json
import random
from datetime import datetime, timedelta
import pymysql
from werkzeug.security import generate_password_hash

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import Config

def get_connection():
    kwargs = {
        'host': Config.DB_HOST,
        'port': Config.DB_PORT,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
        'database': Config.DB_NAME,
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': False,
        'connect_timeout': 10
    }
    if Config.DB_SSL:
        kwargs['ssl'] = {'ssl_mode': 'REQUIRED'}
    return pymysql.connect(**kwargs)

def seed():
    print("Starting comprehensive database seeding for FlyWise AI...")
    conn = get_connection()
    cur = conn.cursor()

    try:
        # 1. Clean existing seed data
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
        tables = [
            'data_source_logs', 'notifications', 'ai_usage_logs', 'ai_messages', 'ai_conversations',
            'group_members', 'group_trips', 'user_travel_requirements', 'flight_status_history',
            'journey_events', 'journeys', 'user_preferences', 'cancellations', 'payments',
            'booking_seats', 'booking_segments', 'booking_passengers', 'bookings', 'passengers',
            'seats', 'fares', 'flights', 'aircraft', 'airlines', 'airports', 'users'
        ]
        for t in tables:
            cur.execute(f"TRUNCATE TABLE {t};")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
        print("[OK] Cleared existing tables.")

        # 2. Seed Users
        hashed_pwd = generate_password_hash("Password@123")
        admin_pwd = generate_password_hash("Admin@123")

        users_data = [
            ("Navaneeth Naidu", "navaneeth@flywise.ai", hashed_pwd, "+91 9876543210", "en", "user", "active"),
            ("FlyWise System Admin", "admin@flywise.ai", admin_pwd, "+91 9876500000", "en", "admin", "active"),
            ("Priya Sharma", "priya@gmail.com", hashed_pwd, "+91 9845123456", "en", "user", "active"),
            ("Rahul Verma", "rahul@gmail.com", hashed_pwd, "+91 9711223344", "en", "user", "active")
        ]
        cur.executemany("""
            INSERT INTO users (full_name, email, password_hash, phone, preferred_language, role, account_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, users_data)
        print("[OK] Seeded Users.")

        # 3. Seed Airports
        airports_data = [
            ("DEL", "VIDP", "Indira Gandhi International Airport", "Delhi", "India", "Asia/Kolkata", 28.556160, 77.100281, json.dumps({
                "terminals": ["T1 (Domestic Low-cost)", "T2 (Domestic)", "T3 (International & Domestic Full-service)"],
                "inter_terminal_transit": "Complimentary shuttle bus between T1 and T2/T3 every 20 mins. Walking between T2 and T3 takes 5-7 mins.",
                "metro": "Delhi Metro Airport Express Line connects T3 and T2 directly to New Delhi Railway Station in 20 mins (₹60).",
                "ground_transport": {"taxi_min": 450, "taxi_max": 750, "bus": 60, "metro": 60},
                "wheelchair_support": True,
                "meet_and_assist": True,
                "parking_hourly": 150
            })),
            ("BOM", "VABB", "Chhatrapati Shivaji Maharaj International Airport", "Mumbai", "India", "Asia/Kolkata", 19.089560, 72.865616, json.dumps({
                "terminals": ["T1 (Domestic Santacruz)", "T2 (International & Domestic Sahar)"],
                "inter_terminal_transit": "Shuttle bus available every 15 mins (travel time 25-35 mins due to city traffic). Separate tickets caution advised.",
                "ground_transport": {"taxi_min": 400, "taxi_max": 650, "bus": 80, "metro": 50},
                "wheelchair_support": True,
                "meet_and_assist": True,
                "parking_hourly": 180
            })),
            ("BLR", "VOBL", "Kempegowda International Airport", "Bengaluru", "India", "Asia/Kolkata", 13.198635, 77.706593, json.dumps({
                "terminals": ["T1 (Domestic & Selected International)", "T2 (Garden Terminal - Domestic & International)"],
                "inter_terminal_transit": "Complimentary electric buggy service and 5-min walkway between T1 and T2.",
                "ground_transport": {"taxi_min": 900, "taxi_max": 1300, "bus": 250, "metro": 0},
                "vayu_vajra_bus": "BMTC Vayu Vajra luxury Volvo buses operate 24/7 across Bengaluru city (₹250-320).",
                "wheelchair_support": True,
                "meet_and_assist": True,
                "parking_hourly": 120
            })),
            ("MAA", "VOMM", "Chennai International Airport", "Chennai", "India", "Asia/Kolkata", 12.994112, 80.170868, json.dumps({
                "terminals": ["T1 (Kamaraj Domestic)", "T4 (Domestic)", "T2 (Anna International)"],
                "inter_terminal_transit": "Connected via moving walkways and travellators (8 mins walk).",
                "metro": "Chennai Metro Blue line station directly at airport terminal.",
                "ground_transport": {"taxi_min": 350, "taxi_max": 550, "metro": 50},
                "wheelchair_support": True,
                "meet_and_assist": True,
                "parking_hourly": 100
            })),
            ("HYD", "VOHS", "Rajiv Gandhi International Airport", "Hyderabad", "India", "Asia/Kolkata", 17.240261, 78.429382, json.dumps({
                "terminals": ["Integrated Terminal (Domestic & International)"],
                "inter_terminal_transit": "Single integrated terminal, no inter-terminal shuttle required.",
                "ground_transport": {"taxi_min": 650, "taxi_max": 950, "bus": 200},
                "pushpak_bus": "TSRTC Pushpak AC buses to Secunderabad, Hitec City, Charminar (₹150-250).",
                "wheelchair_support": True,
                "meet_and_assist": True,
                "parking_hourly": 120
            })),
            ("TIR", "VOTP", "Tirupati Airport", "Tirupati", "India", "Asia/Kolkata", 13.632483, 79.543343, json.dumps({
                "terminals": ["Garuda Terminal (Integrated Domestic)"],
                "inter_terminal_transit": "Single terminal building with modern passenger amenities.",
                "ground_transport": {"taxi_min": 350, "taxi_max": 500, "temple_bus": 100},
                "shuttle": "APSRTC temple pilgrim buses direct to Tirumala hills and Tirupati Central Railway Station.",
                "nearby_alternatives": [{"airport": "MAA", "distance_km": 135, "train_hrs": 3, "road_hrs": 3.5, "est_cab_inr": 2800},
                                        {"airport": "BLR", "distance_km": 240, "road_hrs": 4.5, "est_cab_inr": 4500}],
                "wheelchair_support": True,
                "meet_and_assist": True,
                "parking_hourly": 60
            })),
            ("GOI", "VOGO", "Dabolim International Airport", "Goa", "India", "Asia/Kolkata", 15.380833, 73.831389, json.dumps({
                "terminals": ["Integrated Terminal"],
                "ground_transport": {"taxi_min": 800, "taxi_max": 1400},
                "wheelchair_support": True,
                "parking_hourly": 100
            })),
            ("PNQ", "VAPO", "Pune International Airport", "Pune", "India", "Asia/Kolkata", 18.582222, 73.919722, json.dumps({
                "terminals": ["New Integrated Terminal"],
                "ground_transport": {"taxi_min": 350, "taxi_max": 550},
                "wheelchair_support": True,
                "nearby_alternatives": [{"airport": "BOM", "distance_km": 150, "road_hrs": 3.0, "est_cab_inr": 2500, "train_hrs": 3.5}],
                "parking_hourly": 90
            })),
            ("JAI", "VIJP", "Jaipur International Airport", "Jaipur", "India", "Asia/Kolkata", 26.824222, 75.812222, json.dumps({
                "terminals": ["Terminal 2"],
                "ground_transport": {"taxi_min": 300, "taxi_max": 500},
                "wheelchair_support": True,
                "nearby_alternatives": [{"airport": "DEL", "distance_km": 260, "expressway_hrs": 3.5, "vande_bharat_hrs": 3.2}],
                "parking_hourly": 80
            })),
            ("DXB", "OMDB", "Dubai International Airport", "Dubai", "United Arab Emirates", "Asia/Dubai", 25.253174, 55.365673, json.dumps({
                "terminals": ["T1", "T2", "T3"],
                "ground_transport": {"taxi_min": 1200, "metro": 200},
                "wheelchair_support": True,
                "parking_hourly": 350
            }))
        ]
        cur.executemany("""
            INSERT INTO airports (iata_code, icao_code, airport_name, city, country, timezone, latitude, longitude, terminal_information)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, airports_data)
        print("[OK] Seeded 10 Airports.")

        # 4. Seed Airlines
        airlines_data = [
            ("IndiGo", "6E", "IGO", "https://www.goindigo.in", json.dumps({
                "hotline": "+91 9910383838",
                "baggage_rules": {
                    "cabin": "7 kg (1 piece up to 115cm)",
                    "checkin_economy": "15 kg (1 piece)",
                    "excess_per_kg_inr": 550
                },
                "on_time_rating": 4.5,
                "cancellation_fee_standard": 3000
            })),
            ("Air India", "AI", "AIC", "https://www.airindia.com", json.dumps({
                "hotline": "+91 18602331407",
                "baggage_rules": {
                    "cabin": "7 kg cabin bag + 1 personal laptop/purse item (up to 3kg)",
                    "checkin_economy": "15 kg to 20 kg depending on fare family",
                    "checkin_business": "30 kg",
                    "excess_per_kg_inr": 500
                },
                "on_time_rating": 3.9,
                "cancellation_fee_standard": 2800
            })),
            ("Vistara", "UK", "VTI", "https://www.airvistara.com", json.dumps({
                "hotline": "+91 9289228888",
                "baggage_rules": {
                    "cabin": "7 kg Economy / 10 kg Premium Economy / 12 kg Business",
                    "checkin_economy": "15 kg (Economy Lite) / 20 kg (Standard) / 25 kg (Flexi)",
                    "checkin_business": "35 kg",
                    "excess_per_kg_inr": 500
                },
                "on_time_rating": 4.6,
                "cancellation_fee_standard": 3500
            })),
            ("SpiceJet", "SG", "SEJ", "https://www.spicejet.com", json.dumps({
                "hotline": "+91 1244983410",
                "baggage_rules": {
                    "cabin": "7 kg (1 piece)",
                    "checkin_economy": "15 kg (1 piece)",
                    "excess_per_kg_inr": 550
                },
                "on_time_rating": 3.7,
                "cancellation_fee_standard": 3100
            })),
            ("Akasa Air", "QP", "AKJ", "https://www.akasaair.com", json.dumps({
                "hotline": "+91 9606112131",
                "baggage_rules": {
                    "cabin": "7 kg (1 piece)",
                    "checkin_economy": "15 kg (1 piece)",
                    "excess_per_kg_inr": 500
                },
                "on_time_rating": 4.4,
                "cancellation_fee_standard": 2900
            }))
        ]
        cur.executemany("""
            INSERT INTO airlines (airline_name, iata_code, icao_code, website, support_information)
            VALUES (%s, %s, %s, %s, %s)
        """, airlines_data)
        print("[OK] Seeded 5 Airlines.")

        # 5. Seed Aircraft
        aircraft_data = [
            ("VT-ING", "Airbus A320neo", "Airbus", 186, 0, 186, "active"),
            ("VT-AIQ", "Airbus A320neo", "Airbus", 180, 12, 168, "active"),
            ("VT-ANB", "Boeing 787-8 Dreamliner", "Boeing", 256, 18, 238, "active"),
            ("VT-VIS", "Airbus A321neo", "Airbus", 192, 12, 180, "active"),
            ("VT-SPJ", "Boeing 737-800", "Boeing", 189, 0, 189, "active"),
            ("VT-AKA", "Boeing 737 MAX 8", "Boeing", 189, 0, 189, "active")
        ]
        cur.executemany("""
            INSERT INTO aircraft (aircraft_code, aircraft_model, manufacturer, total_capacity, business_capacity, economy_capacity, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, aircraft_data)
        print("[OK] Seeded 6 Aircraft models.")

        # Fetch airport and airline IDs
        cur.execute("SELECT airport_id, iata_code FROM airports;")
        airport_map = {row['iata_code']: row['airport_id'] for row in cur.fetchall()}

        cur.execute("SELECT airline_id, iata_code FROM airlines;")
        airline_map = {row['iata_code']: row['airline_id'] for row in cur.fetchall()}

        cur.execute("SELECT aircraft_id, aircraft_code FROM aircraft;")
        aircraft_map = {row['aircraft_code']: row['aircraft_id'] for row in cur.fetchall()}

        # 6. Seed Scheduled Flights across next 25 days
        # Base templates for major Indian routes
        flight_templates = [
            # Tirupati (TIR) to Delhi (DEL) - directly for user scenario!
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-618", "orig": "TIR", "dest": "DEL", "dep_time": "08:15", "arr_time": "11:00", "base_fare": 5800, "status": "on-time"},
            {"airline": "SG", "aircraft": "VT-SPJ", "fnum": "SG-302", "orig": "TIR", "dest": "DEL", "dep_time": "14:30", "arr_time": "17:25", "base_fare": 4999, "status": "scheduled"},
            {"airline": "AI", "aircraft": "VT-AIQ", "fnum": "AI-542", "orig": "TIR", "dest": "HYD", "dep_time": "09:30", "arr_time": "10:35", "base_fare": 2400, "status": "scheduled"},
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-7201", "orig": "TIR", "dest": "BLR", "dep_time": "07:15", "arr_time": "08:10", "base_fare": 2200, "status": "on-time"},
            {"airline": "AI", "aircraft": "VT-AIQ", "fnum": "AI-840", "orig": "HYD", "dest": "DEL", "dep_time": "12:15", "arr_time": "14:35", "base_fare": 3800, "status": "scheduled"},
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-2055", "orig": "BLR", "dest": "DEL", "dep_time": "09:45", "arr_time": "12:35", "base_fare": 4100, "status": "scheduled"},
            # DEL <-> BOM (Golden Trunk Route)
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-201", "orig": "DEL", "dest": "BOM", "dep_time": "06:00", "arr_time": "08:15", "base_fare": 4200, "status": "on-time"},
            {"airline": "AI", "aircraft": "VT-ANB", "fnum": "AI-805", "orig": "DEL", "dest": "BOM", "dep_time": "08:00", "arr_time": "10:15", "base_fare": 5100, "status": "scheduled"},
            {"airline": "UK", "aircraft": "VT-VIS", "fnum": "UK-993", "orig": "DEL", "dest": "BOM", "dep_time": "10:30", "arr_time": "12:45", "base_fare": 5600, "status": "scheduled"},
            {"airline": "QP", "aircraft": "VT-AKA", "fnum": "QP-1102", "orig": "DEL", "dest": "BOM", "dep_time": "16:15", "arr_time": "18:35", "base_fare": 3950, "status": "scheduled"},
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-206", "orig": "BOM", "dest": "DEL", "dep_time": "09:15", "arr_time": "11:30", "base_fare": 4350, "status": "on-time"},
            {"airline": "AI", "aircraft": "VT-ANB", "fnum": "AI-806", "orig": "BOM", "dest": "DEL", "dep_time": "11:30", "arr_time": "13:45", "base_fare": 5200, "status": "scheduled"},
            {"airline": "UK", "aircraft": "VT-VIS", "fnum": "UK-994", "orig": "BOM", "dest": "DEL", "dep_time": "14:00", "arr_time": "16:20", "base_fare": 5700, "status": "scheduled"},
            # DEL <-> BLR
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-2131", "orig": "DEL", "dest": "BLR", "dep_time": "07:00", "arr_time": "09:45", "base_fare": 4800, "status": "scheduled"},
            {"airline": "AI", "aircraft": "VT-AIQ", "fnum": "AI-506", "orig": "DEL", "dest": "BLR", "dep_time": "13:00", "arr_time": "15:50", "base_fare": 5400, "status": "scheduled"},
            {"airline": "UK", "aircraft": "VT-VIS", "fnum": "UK-817", "orig": "DEL", "dest": "BLR", "dep_time": "18:20", "arr_time": "21:10", "base_fare": 6100, "status": "scheduled"},
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-2132", "orig": "BLR", "dest": "DEL", "dep_time": "10:30", "arr_time": "13:15", "base_fare": 4900, "status": "scheduled"},
            # BLR <-> GOI (Holiday route for group travel)
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-344", "orig": "BLR", "dest": "GOI", "dep_time": "09:20", "arr_time": "10:35", "base_fare": 2900, "status": "scheduled"},
            {"airline": "QP", "aircraft": "VT-AKA", "fnum": "QP-1351", "orig": "BLR", "dest": "GOI", "dep_time": "15:45", "arr_time": "17:00", "base_fare": 2650, "status": "scheduled"},
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-345", "orig": "GOI", "dest": "BLR", "dep_time": "11:15", "arr_time": "12:30", "base_fare": 2950, "status": "scheduled"},
            # DEL <-> MAA
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-2401", "orig": "DEL", "dest": "MAA", "dep_time": "06:45", "arr_time": "09:30", "base_fare": 4600, "status": "scheduled"},
            {"airline": "AI", "aircraft": "VT-AIQ", "fnum": "AI-440", "orig": "DEL", "dest": "MAA", "dep_time": "16:00", "arr_time": "18:45", "base_fare": 5100, "status": "scheduled"},
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-2402", "orig": "MAA", "dest": "DEL", "dep_time": "10:15", "arr_time": "13:00", "base_fare": 4650, "status": "scheduled"},
            # HYD <-> DEL
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-512", "orig": "HYD", "dest": "DEL", "dep_time": "07:30", "arr_time": "09:50", "base_fare": 4200, "status": "scheduled"},
            {"airline": "6E", "aircraft": "VT-ING", "fnum": "6E-513", "orig": "DEL", "dest": "HYD", "dep_time": "19:00", "arr_time": "21:15", "base_fare": 4300, "status": "scheduled"},
            # International: DEL -> DXB
            {"airline": "AI", "aircraft": "VT-ANB", "fnum": "AI-995", "orig": "DEL", "dest": "DXB", "dep_time": "20:00", "arr_time": "22:45", "base_fare": 13500, "status": "scheduled"}
        ]

        # Generate schedule for today (2026-10-20) and next 20 days
        base_date = datetime(2026, 10, 20)
        flights_to_insert = []
        fares_to_insert = []

        flight_id_counter = 1

        for day_offset in range(0, 21):
            curr_day = base_date + timedelta(days=day_offset)
            date_str = curr_day.strftime("%Y-%m-%d")

            for tmpl in flight_templates:
                dep_dt = datetime.strptime(f"{date_str} {tmpl['dep_time']}", "%Y-%m-%d %H:%M")
                arr_dt = datetime.strptime(f"{date_str} {tmpl['arr_time']}", "%Y-%m-%d %H:%M")
                if arr_dt <= dep_dt:
                    arr_dt += timedelta(days=1)

                status = tmpl['status']
                if day_offset == 0:
                    # Today's flights can have diverse active statuses
                    if tmpl['fnum'] == '6E-618':
                        status = 'on-time'
                    elif tmpl['fnum'] == '6E-201':
                        status = 'departed'
                    elif tmpl['fnum'] == 'AI-840':
                        status = 'delayed' # For disruption simulation

                flights_to_insert.append((
                    flight_id_counter,
                    airline_map[tmpl['airline']],
                    aircraft_map[tmpl['aircraft']],
                    tmpl['fnum'],
                    airport_map[tmpl['orig']],
                    airport_map[tmpl['dest']],
                    dep_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    arr_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    (dep_dt + timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S") if status == 'delayed' else None,
                    (arr_dt + timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S") if status == 'delayed' else None,
                    status,
                    "flywise_scheduler"
                ))

                # Fares: Economy Standard & Flexi
                base = tmpl['base_fare']
                taxes = round(base * 0.12, 2)
                fees = 250.00
                fares_to_insert.append((
                    flight_id_counter,
                    'economy',
                    'saver',
                    base,
                    taxes,
                    fees,
                    'INR',
                    json.dumps({
                        "cabin_baggage": "7 kg",
                        "checkin_baggage": "15 kg",
                        "refundable": False,
                        "change_fee": 3000,
                        "meal_included": False
                    }),
                    curr_day.strftime("%Y-%m-%d 00:00:00"),
                    (curr_day + timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
                ))

                fares_to_insert.append((
                    flight_id_counter,
                    'economy',
                    'flexi',
                    round(base * 1.25, 2),
                    round(taxes * 1.25, 2),
                    fees,
                    'INR',
                    json.dumps({
                        "cabin_baggage": "7 kg",
                        "checkin_baggage": "20 kg",
                        "refundable": True,
                        "cancellation_fee": 500,
                        "change_fee": 0,
                        "meal_included": True,
                        "free_seat_selection": True
                    }),
                    curr_day.strftime("%Y-%m-%d 00:00:00"),
                    (curr_day + timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
                ))

                # If aircraft has business class
                if tmpl['aircraft'] in ['VT-AIQ', 'VT-ANB', 'VT-VIS']:
                    fares_to_insert.append((
                        flight_id_counter,
                        'business',
                        'business_flex',
                        round(base * 2.8, 2),
                        round(taxes * 2.5, 2),
                        450.00,
                        'INR',
                        json.dumps({
                            "cabin_baggage": "12 kg",
                            "checkin_baggage": "35 kg",
                            "priority_checkin": True,
                            "priority_boarding": True,
                            "lounge_access": True,
                            "gourmet_meals": True,
                            "refundable": True
                        }),
                        curr_day.strftime("%Y-%m-%d 00:00:00"),
                        (curr_day + timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
                    ))

                flight_id_counter += 1

        cur.executemany("""
            INSERT INTO flights (
                flight_id, airline_id, aircraft_id, flight_number,
                origin_airport_id, destination_airport_id, scheduled_departure,
                scheduled_arrival, actual_departure, actual_arrival, flight_status, data_source
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, flights_to_insert)
        print(f"[OK] Seeded {len(flights_to_insert)} scheduled flight instances.")

        cur.executemany("""
            INSERT INTO fares (
                flight_id, travel_class, fare_type, base_fare, taxes,
                mandatory_fees, currency, fare_conditions, valid_from, valid_until
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, fares_to_insert)
        print(f"[OK] Seeded {len(fares_to_insert)} fare records.")

        # 7. Seed Seats for the first 50 flights (to keep seed execution fast & crisp)
        seats_to_insert = []
        for fid in range(1, min(55, flight_id_counter)):
            # 24 seats per flight: Rows 1-4 (A, B, C, D, E, F)
            # Row 1: Business / Extra legroom, Row 2-4: Economy
            for r in range(1, 5):
                t_class = 'business' if r == 1 else 'economy'
                for col in ['A', 'B', 'C', 'D', 'E', 'F']:
                    seat_num = f"{r}{col}"
                    # Make most available, a few booked
                    s_status = 'available'
                    if (fid, seat_num) in [(1, '2A'), (1, '2B'), (7, '3C')]:
                        s_status = 'booked'
                    seats_to_insert.append((fid, seat_num, t_class, s_status))

        cur.executemany("""
            INSERT INTO seats (flight_id, seat_number, travel_class, seat_status)
            VALUES (%s, %s, %s, %s)
        """, seats_to_insert)
        print(f"[OK] Seeded {len(seats_to_insert)} seat records for initial flight instances.")

        # 8. Seed Passengers
        passengers_data = [
            (1, "Navaneeth Naidu", "2003-08-15", json.dumps({"email": "navaneeth@flywise.ai", "phone": "+91 9876543210"})),
            (1, "Kavya Naidu", "2005-11-20", json.dumps({"email": "kavya@gmail.com", "phone": "+91 9876543211"})),
            (3, "Priya Sharma", "2001-04-10", json.dumps({"email": "priya@gmail.com", "phone": "+91 9845123456"}))
        ]
        cur.executemany("""
            INSERT INTO passengers (user_id, full_name, date_of_birth, contact_information)
            VALUES (%s, %s, %s, %s)
        """, passengers_data)
        print("[OK] Seeded Passengers.")

        # 9. Seed Active Sample Booking (DEL to BOM)
        # Booking 1: Upcoming Journey for Navaneeth
        cur.execute("""
            INSERT INTO bookings (booking_id, booking_reference, user_id, booking_status, booking_currency, total_amount, created_at, confirmed_at)
            VALUES (1, 'FW-DEL25B', 1, 'confirmed', 'INR', 10450.00, '2026-10-18 14:30:00', '2026-10-18 14:32:00')
        """)
        # Booking Passengers
        cur.execute("""
            INSERT INTO booking_passengers (booking_id, passenger_id, ticket_number, passenger_status)
            VALUES 
            (1, 1, 'TK-6E-9021481', 'confirmed'),
            (1, 2, 'TK-6E-9021482', 'confirmed')
        """)
        # Booking Segment (Flight 7: DEL -> BOM on 2026-10-20 or 2026-10-25)
        # Find a DEL to BOM flight around 2026-10-25
        cur.execute("""
            SELECT flight_id FROM flights 
            WHERE flight_number = '6E-201' AND DATE(scheduled_departure) = '2026-10-25' LIMIT 1;
        """)
        f_row = cur.fetchone()
        f_del_bom = f_row['flight_id'] if f_row else 7

        cur.execute("""
            INSERT INTO booking_segments (booking_id, flight_id, segment_order, fare_id, segment_status)
            VALUES (1, %s, 1, 1, 'confirmed')
        """, (f_del_bom,))

        # Seat assignments
        cur.execute("SELECT seat_id FROM seats WHERE flight_id = %s AND seat_number = '2A';", (f_del_bom,))
        s1 = cur.fetchone()
        cur.execute("SELECT seat_id FROM seats WHERE flight_id = %s AND seat_number = '2B';", (f_del_bom,))
        s2 = cur.fetchone()
        if s1 and s2:
            cur.execute("""
                INSERT INTO booking_seats (booking_id, passenger_id, seat_id, assignment_status)
                VALUES 
                (1, 1, %s, 'assigned'),
                (1, 2, %s, 'assigned')
            """, (s1['seat_id'], s2['seat_id']))

        # Payment
        cur.execute("""
            INSERT INTO payments (booking_id, provider_reference, amount, currency, payment_status)
            VALUES (1, 'PAY-RAZOR-98721A0', 10450.00, 'INR', 'success')
        """)

        # Journey & Digital Twin Events
        cur.execute("""
            INSERT INTO journeys (journey_id, user_id, booking_id, journey_status, planned_departure, planned_arrival)
            VALUES (1, 1, 1, 'pre_departure', '2026-10-25 06:00:00', '2026-10-25 08:15:00')
        """)

        journey_events = [
            (1, "booking_confirmed", "2026-10-18 14:32:00", "system", "Booking confirmed with PNR FW-DEL25B. E-tickets issued.", "verified"),
            (1, "pre_departure_checklist", "2026-10-19 10:00:00", "companion", "Web check-in opens 48 hours prior to departure. Prepare government photo ID.", "verified"),
            (1, "terminal_info_update", "2026-10-20 09:00:00", "airport_service", "Flight 6E-201 scheduled from Indira Gandhi International Terminal 1D/T1.", "verified")
        ]
        cur.executemany("""
            INSERT INTO journey_events (journey_id, event_type, event_timestamp, event_source, event_description, verification_status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, journey_events)

        # Booking 2: Disrupted Flight (to demonstrate Emergency Mode and Disruption Recovery!)
        cur.execute("""
            INSERT INTO bookings (booking_id, booking_reference, user_id, booking_status, booking_currency, total_amount, created_at, confirmed_at)
            VALUES (2, 'FW-DISR01', 1, 'confirmed', 'INR', 6800.00, '2026-10-19 11:20:00', '2026-10-19 11:22:00')
        """)
        cur.execute("""
            INSERT INTO booking_passengers (booking_id, passenger_id, ticket_number, passenger_status)
            VALUES (2, 1, 'TK-AI-7782101', 'confirmed')
        """)
        # Flight with delayed status
        cur.execute("SELECT flight_id FROM flights WHERE flight_status = 'delayed' LIMIT 1;")
        f_delayed = cur.fetchone()
        f_del_id = f_delayed['flight_id'] if f_delayed else 5

        cur.execute("""
            INSERT INTO booking_segments (booking_id, flight_id, segment_order, segment_status)
            VALUES (2, %s, 1, 'confirmed')
        """, (f_del_id,))

        cur.execute("""
            INSERT INTO payments (booking_id, provider_reference, amount, currency, payment_status)
            VALUES (2, 'PAY-UPI-DISRUPT99', 6800.00, 'INR', 'success')
        """)

        cur.execute("""
            INSERT INTO journeys (journey_id, user_id, booking_id, journey_status, planned_departure, planned_arrival)
            VALUES (2, 1, 2, 'disrupted', '2026-10-20 12:15:00', '2026-10-20 14:35:00')
        """)

        cur.execute("""
            INSERT INTO journey_events (journey_id, event_type, event_timestamp, event_source, event_description, verification_status)
            VALUES 
            (2, 'schedule_change', '2026-10-20 10:15:00', 'atc_simulator', 'Flight delayed by 45 minutes due to air traffic congestion. Onward connection at risk.', 'verified'),
            (2, 'disruption_alert', '2026-10-20 10:20:00', 'flywise_recovery', 'Emergency Travel Mode activated. Alternative non-stop itineraries discovered.', 'verified')
        """)

        # 10. Seed User Preferences & Travel Requirements
        cur.execute("""
            INSERT INTO user_preferences (user_id, preference_type, preference_value)
            VALUES 
            (1, 'max_budget', '7500'),
            (1, 'preferred_airline', 'IndiGo,Vistara'),
            (1, 'departure_time_window', 'morning'),
            (1, 'max_stops', '1')
        """)

        cur.execute("""
            INSERT INTO user_travel_requirements (user_id, requirement_type, requirement_details)
            VALUES 
            (1, 'accessibility', JSON_OBJECT('wheelchair_needed', true, 'assistance_type', 'ramp_and_cabin', 'special_meal', 'diabetic'))
        """)

        # 11. Seed Group Trip ("Goa College Reunion 2026")
        cur.execute("""
            INSERT INTO group_trips (group_trip_id, organiser_user_id, group_name, origin_airport_id, destination_airport_id, departure_date)
            VALUES (1, 1, 'Goa College Reunion 2026', %s, %s, '2026-10-28')
        """, (airport_map['BLR'], airport_map['GOI']))

        cur.execute("""
            INSERT INTO group_members (group_trip_id, user_id, member_name, budget, travel_preferences, invitation_status)
            VALUES 
            (1, 1, 'Navaneeth Naidu', 4000.00, JSON_OBJECT('departure', 'morning', 'seat', 'window'), 'accepted'),
            (1, 3, 'Priya Sharma', 3500.00, JSON_OBJECT('departure', 'morning', 'seat', 'aisle'), 'accepted'),
            (1, 4, 'Rahul Verma', 4500.00, JSON_OBJECT('departure', 'any', 'seat', 'middle'), 'accepted')
        """)

        # 12. Seed Notifications
        cur.execute("""
            INSERT INTO notifications (user_id, notification_type, title, message, delivery_status)
            VALUES 
            (1, 'disruption', 'Flight AI-840 Delayed by 45m', 'Your flight is delayed. Click to open Emergency Travel Mode and view alternative options.', 'unread'),
            (1, 'reminder', 'Upcoming Trip: Delhi to Mumbai', 'Your flight FW-DEL25B is coming up on Oct 25. Web check-in opens tomorrow.', 'read')
        """)

        conn.commit()
        print("\n[SUCCESS] FlyWise AI database seeded successfully with rich, realistic data!")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Seeding failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    seed()
