import random
import string
import json
from datetime import datetime, timedelta
from database import transaction, query_all, query_one, clean_row

def generate_booking_reference():
    """Generates a clean 8-character unique booking reference like FW-7K9A2M."""
    chars = string.ascii_uppercase + string.digits
    rand_part = ''.join(random.choices(chars, k=6))
    return f"FW-{rand_part}"

def generate_ticket_number(airline_code="6E"):
    """Generates unique 13-digit e-ticket number."""
    digits = ''.join(random.choices(string.digits, k=10))
    return f"TK-{airline_code}-{digits}"

def create_booking(user_id, itinerary_id, flight_ids, passengers_list, seat_assignments, total_amount, payment_mode="card", add_ons=None):
    """
    ACID Transactional Booking Creation with Concurrency Control & Backend Fare Recalculation.
    Validates passengers, flights, and seats, recalculates fares directly from database records,
    executes simulated payment workflow, and persists the booking to MySQL.
    """
    if not passengers_list:
        raise ValueError("At least one passenger is required to complete the booking.")

    # 1. Validate Passenger Details
    for idx, p in enumerate(passengers_list):
        fname = (p.get('full_name') or '').strip()
        if not fname or len(fname) < 2:
            raise ValueError(f"Passenger #{idx + 1}: Please enter a valid full name (minimum 2 characters).")
        email = (p.get('email') or '').strip()
        if not email or '@' not in email or '.' not in email:
            raise ValueError(f"Passenger #{idx + 1}: Please enter a valid email address.")

    if not flight_ids:
        raise ValueError("At least one flight segment is required for booking.")

    with transaction() as cur:
        # 2. Concurrency Check: Lock requested seats with FOR UPDATE
        seat_ids = [s.get('seat_id') for s in seat_assignments if s.get('seat_id')]
        locked_seats = []
        if seat_ids:
            format_strings = ','.join(['%s'] * len(seat_ids))
            cur.execute(f"""
                SELECT seat_id, flight_id, seat_number, travel_class, seat_status 
                FROM seats 
                WHERE seat_id IN ({format_strings}) 
                FOR UPDATE;
            """, tuple(seat_ids))
            locked_seats = cur.fetchall()
            
            for s in locked_seats:
                if s['seat_status'] in ['booked', 'reserved']:
                    raise ValueError(f"Seat {s['seat_number']} is no longer available. Please select another seat.")

        # 3. Backend Fare Recalculation from MySQL fares table
        calculated_base = 0.0
        calculated_taxes = 0.0
        flight_segments_data = []
        for fid in flight_ids:
            cur.execute("""
                SELECT f.flight_id, f.flight_number, f.flight_status, f.scheduled_departure, f.scheduled_arrival,
                       fa.fare_id, fa.base_fare, fa.taxes, fa.mandatory_fees, fa.travel_class
                FROM flights f
                LEFT JOIN fares fa ON f.flight_id = fa.flight_id
                WHERE f.flight_id = %s LIMIT 1;
            """, (fid,))
            fl = cur.fetchone()
            if not fl:
                raise ValueError(f"Flight ID {fid} was not found in the flight schedule.")

            bf = float(fl.get('base_fare') or 4000.0)
            tx = float(fl.get('taxes') or 500.0)
            mf = float(fl.get('mandatory_fees') or 200.0)
            calculated_base += bf
            calculated_taxes += (tx + mf)
            flight_segments_data.append(fl)

        # Calculate seat fee based on locked seats
        calculated_seat_fee = 0.0
        for s in locked_seats:
            s_num = s.get('seat_number', '')
            if s_num.startswith('1'):
                calculated_seat_fee += 600.0
            elif s_num.endswith('B') or s_num.endswith('E'):
                calculated_seat_fee += 0.0
            else:
                calculated_seat_fee += 250.0

        # Calculate add-on charges
        calculated_addons_fee = 0.0
        selected_addons_list = []
        if isinstance(add_ons, dict):
            if add_ons.get('meal'):
                calculated_addons_fee += 350.0
                selected_addons_list.append("Hot Gourmet Meal (+₹350)")
            if add_ons.get('insurance'):
                calculated_addons_fee += 199.0
                selected_addons_list.append("Comprehensive Travel Insurance (+₹199)")
            if add_ons.get('priority'):
                calculated_addons_fee += 300.0
                selected_addons_list.append("Priority Baggage & Boarding (+₹300)")
        elif isinstance(add_ons, list):
            selected_addons_list = add_ons
            for ad in selected_addons_list:
                if '350' in str(ad) or 'Meal' in str(ad):
                    calculated_addons_fee += 350.0
                elif '199' in str(ad) or 'Insurance' in str(ad):
                    calculated_addons_fee += 199.0
                elif '300' in str(ad) or 'Priority' in str(ad):
                    calculated_addons_fee += 300.0

        passenger_count = len(passengers_list)
        subtotal_flights = (calculated_base + calculated_taxes) * passenger_count
        backend_total = subtotal_flights + calculated_seat_fee + calculated_addons_fee

        # Use backend calculated total (or client total if within reasonable rounding)
        client_total = float(total_amount) if total_amount else backend_total
        final_charged_amount = backend_total if abs(backend_total - client_total) > 5.0 else client_total

        # 4. Generate unique PNR
        pnr = generate_booking_reference()
        cur.execute("SELECT booking_id FROM bookings WHERE booking_reference = %s;", (pnr,))
        if cur.fetchone():
            pnr = generate_booking_reference()

        # 5. Insert Booking Record
        cur.execute("""
            INSERT INTO bookings (booking_reference, user_id, booking_status, booking_currency, total_amount, confirmed_at)
            VALUES (%s, %s, 'confirmed', 'INR', %s, NOW());
        """, (pnr, user_id, float(final_charged_amount)))
        booking_id = cur.lastrowid
        if not booking_id:
            raise RuntimeError("Database error: Failed to generate booking record.")

        # 6. Insert Passengers & Booking_Passengers
        created_passengers = []
        for p in passengers_list:
            full_name = p.get('full_name', 'Passenger').strip()
            dob = p.get('date_of_birth', None)
            contact_info = json.dumps({
                "email": p.get('email', '').strip(),
                "phone": p.get('phone', '').strip(),
                "gender": p.get('gender', 'M'),
                "addons": selected_addons_list,
                "passenger_type": p.get('passenger_type', 'Adult')
            })
            cur.execute("""
                INSERT INTO passengers (user_id, full_name, date_of_birth, contact_information)
                VALUES (%s, %s, %s, %s);
            """, (user_id, full_name, dob, contact_info))
            passenger_id = cur.lastrowid

            tkt_num = generate_ticket_number()
            cur.execute("""
                INSERT INTO booking_passengers (booking_id, passenger_id, ticket_number, passenger_status)
                VALUES (%s, %s, %s, 'confirmed');
            """, (booking_id, passenger_id, tkt_num))

            created_passengers.append({
                "passenger_id": passenger_id,
                "full_name": full_name,
                "ticket_number": tkt_num
            })

        # 7. Insert Booking Segments
        order = 1
        first_dep = None
        last_arr = None

        for fl in flight_segments_data:
            fid = fl['flight_id']
            if order == 1:
                first_dep = fl['scheduled_departure']
            last_arr = fl['scheduled_arrival']

            cur.execute("""
                INSERT INTO booking_segments (booking_id, flight_id, segment_order, fare_id, segment_status)
                VALUES (%s, %s, %s, %s, 'confirmed');
            """, (booking_id, fid, order, fl['fare_id']))
            order += 1

        # 8. Reserve & Assign Seats
        for i, sa in enumerate(seat_assignments):
            s_id = sa.get('seat_id')
            if s_id:
                assigned_pid = created_passengers[min(i, len(created_passengers)-1)]['passenger_id']
                cur.execute("""
                    INSERT INTO booking_seats (booking_id, passenger_id, seat_id, assignment_status)
                    VALUES (%s, %s, %s, 'assigned');
                """, (booking_id, assigned_pid, s_id))

                cur.execute("""
                    UPDATE seats SET seat_status = 'booked' WHERE seat_id = %s;
                """, (s_id,))

        # 9. Simulated Payment Workflow
        clean_mode = payment_mode.upper().replace(' ', '_')
        pay_ref = f"SIM-PAY-{clean_mode}-{pnr.replace('FW-', '')}"
        cur.execute("""
            INSERT INTO payments (booking_id, provider_reference, amount, currency, payment_status)
            VALUES (%s, %s, %s, 'INR', 'success');
        """, (booking_id, pay_ref, float(final_charged_amount)))

        # 10. Create Journey & Digital Twin
        cur.execute("""
            INSERT INTO journeys (user_id, booking_id, journey_status, planned_departure, planned_arrival)
            VALUES (%s, %s, 'confirmed', %s, %s);
        """, (user_id, booking_id, first_dep or datetime.now(), last_arr or datetime.now()))
        journey_id = cur.lastrowid

        # 11. Initial Journey Events
        cur.execute("""
            INSERT INTO journey_events (journey_id, event_type, event_description, verification_status)
            VALUES 
            (%s, 'booking_confirmed', CONCAT('Booking confirmed with PNR ', %s, '. Simulated payment verified in MySQL.'), 'verified'),
            (%s, 'pre_departure', 'Journey registered in FlyWise Digital Twin. Web check-in opens 48h prior.', 'verified');
        """, (journey_id, pnr, journey_id))

        # 12. In-App Notification
        cur.execute("""
            INSERT INTO notifications (user_id, notification_type, title, message)
            VALUES (%s, 'booking_confirmed', CONCAT('Flight Confirmed: PNR ', %s), CONCAT('Your journey has been confirmed. Total amount paid: ₹', %s, ' (Simulated Transaction)'));
        """, (user_id, pnr, f"{final_charged_amount:,.2f}"))

        return {
            "booking_id": booking_id,
            "booking_reference": pnr,
            "journey_id": journey_id,
            "status": "confirmed",
            "total_amount": final_charged_amount,
            "passengers": created_passengers,
            "payment_reference": pay_ref,
            "is_simulated_payment": True
        }

def get_booking_details(booking_id_or_ref, user_id=None):
    """Retrieves full booking details including passengers, segments, seats, payment."""
    if isinstance(booking_id_or_ref, int) or str(booking_id_or_ref).isdigit():
        clause = "b.booking_id = %s"
        param = int(booking_id_or_ref)
    else:
        clause = "b.booking_reference = %s"
        param = str(booking_id_or_ref).strip().upper()

    user_clause = " AND b.user_id = %s" if user_id else ""
    params = (param, user_id) if user_id else (param,)

    booking = query_one(f"""
        SELECT b.*, u.full_name AS booked_by_name, u.email AS booked_by_email,
               p.provider_reference, p.payment_status,
               j.journey_id, j.journey_status
        FROM bookings b
        JOIN users u ON b.user_id = u.user_id
        LEFT JOIN payments p ON b.booking_id = p.booking_id
        LEFT JOIN journeys j ON b.booking_id = j.booking_id
        WHERE {clause} {user_clause};
    """, params)

    if not booking:
        return None

    # Fetch Passengers
    passengers = query_all("""
        SELECT bp.ticket_number, bp.passenger_status, p.passenger_id, p.full_name, p.date_of_birth, p.contact_information,
               s.seat_number, s.travel_class AS seat_class
        FROM booking_passengers bp
        JOIN passengers p ON bp.passenger_id = p.passenger_id
        LEFT JOIN booking_seats bs ON bp.booking_id = bs.booking_id AND bp.passenger_id = bs.passenger_id
        LEFT JOIN seats s ON bs.seat_id = s.seat_id
        WHERE bp.booking_id = %s;
    """, (booking['booking_id'],))

    # Fetch Segments with fare details
    segments = query_all("""
        SELECT bs.segment_order, bs.segment_status,
               f.flight_id, f.flight_number, f.scheduled_departure, f.scheduled_arrival, f.flight_status,
               TIMESTAMPDIFF(MINUTE, f.scheduled_departure, f.scheduled_arrival) AS duration_minutes,
               al.airline_name, al.iata_code AS airline_code,
               orig.iata_code AS origin_code, orig.city AS origin_city, orig.airport_name AS origin_name,
               dest.iata_code AS destination_code, dest.city AS destination_city, dest.airport_name AS destination_name,
               fa.base_fare, fa.taxes, fa.mandatory_fees, COALESCE(fa.travel_class, 'economy') AS travel_class
        FROM booking_segments bs
        JOIN flights f ON bs.flight_id = f.flight_id
        JOIN airlines al ON f.airline_id = al.airline_id
        JOIN airports orig ON f.origin_airport_id = orig.airport_id
        JOIN airports dest ON f.destination_airport_id = dest.airport_id
        LEFT JOIN fares fa ON bs.fare_id = fa.fare_id
        WHERE bs.booking_id = %s
        ORDER BY bs.segment_order ASC;
    """, (booking['booking_id'],))

    # Parse Passenger Details
    for p in passengers:
        raw_contact = p.get('contact_information')
        if isinstance(raw_contact, str):
            try:
                c_dict = json.loads(raw_contact)
            except Exception:
                c_dict = {}
        elif isinstance(raw_contact, dict):
            c_dict = raw_contact
        else:
            c_dict = {}

        p['email'] = c_dict.get('email', '')
        p['phone'] = c_dict.get('phone', '')
        p['gender'] = c_dict.get('gender', 'M')
        p['addons'] = c_dict.get('addons', [])
        p['passenger_type'] = c_dict.get('passenger_type', 'Adult')

    # Itemized Fare Summary Breakdown
    p_count = max(1, len(passengers))
    base_fare_sum = 0.0
    taxes_fees_sum = 0.0
    for seg in segments:
        base_fare_sum += float(seg.get('base_fare') or 0.0)
        taxes_fees_sum += float(seg.get('taxes') or 0.0) + float(seg.get('mandatory_fees') or 0.0)

    total_amt = float(booking.get('total_amount') or 0.0)
    if base_fare_sum == 0.0 and total_amt > 0:
        base_fare_sum = round(total_amt * 0.78, 2)
        taxes_fees_sum = round(total_amt * 0.22, 2)
    else:
        base_fare_sum = base_fare_sum * p_count
        taxes_fees_sum = taxes_fees_sum * p_count

    seat_fee_sum = 0.0
    for p in passengers:
        s_num = p.get('seat_number') or ''
        if s_num.startswith('1'):
            seat_fee_sum += 600.0
        elif s_num.endswith('B') or s_num.endswith('E'):
            seat_fee_sum += 0.0
        elif s_num:
            seat_fee_sum += 250.0

    addons_fee_sum = 0.0
    for p in passengers:
        for ad in p.get('addons', []):
            ad_str = str(ad)
            if '350' in ad_str or 'Meal' in ad_str:
                addons_fee_sum += 350.0
            elif '199' in ad_str or 'Insurance' in ad_str:
                addons_fee_sum += 199.0
            elif '300' in ad_str or 'Priority' in ad_str:
                addons_fee_sum += 300.0

    booking['passengers'] = passengers
    booking['segments'] = segments
    booking['fare_breakdown'] = {
        "base_fare": base_fare_sum,
        "taxes_and_fees": taxes_fees_sum,
        "seat_fee": seat_fee_sum,
        "addons_fee": addons_fee_sum,
        "total_amount": total_amt,
        "is_simulated_payment": True,
        "payment_status": booking.get('payment_status', 'success'),
        "payment_reference": booking.get('provider_reference') or f"SIM-PAY-CARD-{booking.get('booking_reference')}",
        "payment_label": "Simulated / Test Payment - Successful"
    }
    return booking

def cancel_booking(booking_id, user_id, reason="Customer requested"):
    """
    Transactional cancellation of a booking:
    1. Verifies ownership.
    2. Calculates refund.
    3. Releases assigned seats back to 'available'.
    4. Updates booking status to 'cancelled'.
    5. Records cancellation row.
    """
    with transaction() as cur:
        # Verify ownership
        cur.execute("SELECT * FROM bookings WHERE booking_id = %s AND user_id = %s FOR UPDATE;", (booking_id, user_id))
        booking = cur.fetchone()
        if not booking:
            raise ValueError("Booking not found or unauthorized.")

        if booking['booking_status'] == 'cancelled':
            raise ValueError("Booking is already cancelled.")

        # Calculate refund: Flat ₹1500 cancellation fee per ticket, remainder refunded
        cur.execute("SELECT COUNT(*) AS cnt FROM booking_passengers WHERE booking_id = %s;", (booking_id,))
        p_count = cur.fetchone()['cnt'] or 1
        cancellation_fee = 1500.0 * p_count
        refund_amount = max(0.0, float(booking['total_amount']) - cancellation_fee)

        # Release seats
        cur.execute("""
            SELECT seat_id FROM booking_seats WHERE booking_id = %s;
        """, (booking_id,))
        seat_rows = cur.fetchall()
        for sr in seat_rows:
            cur.execute("UPDATE seats SET seat_status = 'available' WHERE seat_id = %s;", (sr['seat_id'],))

        cur.execute("UPDATE booking_seats SET assignment_status = 'released' WHERE booking_id = %s;", (booking_id,))
        cur.execute("UPDATE bookings SET booking_status = 'cancelled' WHERE booking_id = %s;", (booking_id,))
        cur.execute("UPDATE booking_passengers SET passenger_status = 'cancelled' WHERE booking_id = %s;", (booking_id,))
        cur.execute("UPDATE booking_segments SET segment_status = 'cancelled' WHERE booking_id = %s;", (booking_id,))
        cur.execute("UPDATE journeys SET journey_status = 'cancelled' WHERE booking_id = %s;", (booking_id,))

        # Insert cancellation record
        cur.execute("""
            INSERT INTO cancellations (booking_id, requested_by, cancellation_status, cancellation_reason, calculated_refund_amount, confirmed_refund_amount, completed_at)
            VALUES (%s, %s, 'processed', %s, %s, %s, NOW());
        """, (booking_id, user_id, reason, refund_amount, refund_amount))
        cancel_id = cur.lastrowid

        # Journey Event
        cur.execute("SELECT journey_id FROM journeys WHERE booking_id = %s;", (booking_id,))
        j_row = cur.fetchone()
        if j_row:
            cur.execute("""
                INSERT INTO journey_events (journey_id, event_type, event_description, verification_status)
                VALUES (%s, 'booking_cancelled', CONCAT('Booking cancelled. Estimated refund of ₹', %s, ' initiated.'), 'verified');
            """, (j_row['journey_id'], f"{refund_amount:,.2f}"))

        # Notification
        cur.execute("""
            INSERT INTO notifications (user_id, notification_type, title, message)
            VALUES (%s, 'cancellation', CONCAT('Booking Cancelled: ', %s), CONCAT('Your booking has been cancelled. Refund of ₹', %s, ' has been credited to original payment source.'));
        """, (user_id, booking['booking_reference'], f"{refund_amount:,.2f}"))

        return {
            "cancellation_id": cancel_id,
            "booking_reference": booking['booking_reference'],
            "refund_amount": refund_amount,
            "cancellation_fee": cancellation_fee,
            "status": "processed"
        }
