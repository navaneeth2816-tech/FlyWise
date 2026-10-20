from database import query_one

def calculate_journey_cost(flight_id=None, base_fare=None, origin_code="DEL", destination_code="BOM", 
                           baggage_kg=15, seat_type="standard_window", ground_transport="cab", add_ons=None):
    """
    Total Journey Cost Calculator engine based on PRD Section 10.
    Produces an itemized transparent breakdown preventing double counting.
    """
    fare_amount = 0.0
    taxes_amount = 0.0
    fees_amount = 0.0

    if flight_id:
        fare_info = query_one("""
            SELECT fa.base_fare, fa.taxes, fa.mandatory_fees, orig.iata_code AS orig_code, dest.iata_code AS dest_code
            FROM flights f
            JOIN airports orig ON f.origin_airport_id = orig.airport_id
            JOIN airports dest ON f.destination_airport_id = dest.airport_id
            LEFT JOIN fares fa ON f.flight_id = fa.flight_id
            WHERE f.flight_id = %s LIMIT 1;
        """, (flight_id,))
        if fare_info:
            fare_amount = fare_info['base_fare'] or 4200.0
            taxes_amount = fare_info['taxes'] or 550.0
            fees_amount = fare_info['mandatory_fees'] or 250.0
            origin_code = fare_info['orig_code']
            destination_code = fare_info['dest_code']
    elif base_fare:
        fare_amount = float(base_fare)
        taxes_amount = round(fare_amount * 0.12, 2)
        fees_amount = 250.0

    ticket_total = fare_amount + taxes_amount + fees_amount

    # Baggage calculation (15kg is free on domestic economy)
    baggage_cost = 0.0
    if baggage_kg > 15:
        excess_kg = baggage_kg - 15
        baggage_cost = excess_kg * 500.0 # ~₹500 per excess kg

    # Seat charges
    seat_pricing = {
        "middle": 0.0,
        "standard_window": 250.0,
        "standard_aisle": 250.0,
        "extra_legroom": 600.0,
        "business": 0.0 # included in fare
    }
    seat_cost = seat_pricing.get(seat_type, 200.0)

    # Ground transport estimates based on airport
    ground_rates = {
        "metro": {"DEL": 60, "MAA": 50, "BOM": 50, "default": 60},
        "bus": {"BLR": 250, "HYD": 200, "DEL": 60, "default": 100},
        "cab": {"DEL": 600, "BOM": 550, "BLR": 1100, "MAA": 450, "HYD": 800, "TIR": 400, "default": 600}
    }

    origin_transit = ground_rates.get(ground_transport, {}).get(origin_code, ground_rates.get(ground_transport, {}).get("default", 500))
    dest_transit = ground_rates.get(ground_transport, {}).get(destination_code, ground_rates.get(ground_transport, {}).get("default", 500))
    total_ground_transport = origin_transit + dest_transit

    # Add-ons
    addon_cost = 0.0
    addon_items = []
    if add_ons:
        if isinstance(add_ons, list):
            for a in add_ons:
                if a == "meal":
                    addon_cost += 350.0
                    addon_items.append({"name": "Hot Gourmet Meal", "cost": 350.0})
                elif a == "insurance":
                    addon_cost += 199.0
                    addon_items.append({"name": "Travel Protection Insurance", "cost": 199.0})
                elif a == "priority_boarding":
                    addon_cost += 300.0
                    addon_items.append({"name": "Priority Boarding & Baggage", "cost": 300.0})

    estimated_total_journey_cost = ticket_total + baggage_cost + seat_cost + total_ground_transport + addon_cost

    return {
        "ticket_fare": {
            "base_fare": fare_amount,
            "taxes": taxes_amount,
            "mandatory_fees": fees_amount,
            "subtotal": ticket_total
        },
        "baggage_charges": {
            "included_kg": 15,
            "requested_kg": baggage_kg,
            "charge": baggage_cost
        },
        "seat_charges": {
            "seat_type": seat_type,
            "charge": seat_cost
        },
        "ground_transport": {
            "mode": ground_transport,
            "origin_transit_inr": origin_transit,
            "destination_transit_inr": dest_transit,
            "subtotal": total_ground_transport
        },
        "add_ons": {
            "items": addon_items,
            "subtotal": addon_cost
        },
        "estimated_total_journey_cost": estimated_total_journey_cost,
        "currency": "INR"
    }

def compare_journey_costs(itineraries, ground_transport="cab"):
    """Compares multiple flight options by their complete total journey cost."""
    results = []
    for it in itineraries:
        cost = calculate_journey_cost(
            base_fare=it.get('base_fare', 4000),
            origin_code=it.get('origin_code', 'DEL'),
            destination_code=it.get('destination_code', 'BOM'),
            ground_transport=ground_transport
        )
        results.append({
            "itinerary_id": it.get('itinerary_id'),
            "airline_name": it.get('airline_name'),
            "flight_number": it.get('flight_number', 'N/A'),
            "base_fare": it.get('base_fare'),
            "ticket_total": it.get('total_fare'),
            "total_journey_cost": cost['estimated_total_journey_cost'],
            "breakdown": cost
        })
    results.sort(key=lambda x: x['total_journey_cost'])
    return results
