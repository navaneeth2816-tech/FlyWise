from services.risk_service import assess_connection_risk
from services.cost_service import calculate_journey_cost
from datetime import datetime

def score_and_rank_itineraries(itineraries, user_preferences=None):
    """
    Personalized Flight Recommendation Engine according to PRD Section 9.
    Implements multi-factor weighted scoring model with explainable reasons.
    """
    if not itineraries:
        return []

    prefs = user_preferences or {}
    max_budget = float(prefs.get('max_budget', 12000.0))
    preferred_airline = prefs.get('preferred_airline', '')
    preferred_departure_window = prefs.get('departure_time_window', 'morning') # morning, afternoon, evening

    # Extract bounds for normalization
    costs = [it['total_fare'] for it in itineraries]
    durations = [it['duration_minutes'] for it in itineraries]
    min_cost = min(costs) if costs else 1.0
    max_cost = max(costs) if costs else 1.0
    min_dur = min(durations) if durations else 1.0
    max_dur = max(durations) if durations else 1.0

    scored_itineraries = []

    for it in itineraries:
        # 1. Total Journey Cost Score (Weight: 30%)
        # Lower cost -> higher score (normalized 0-100)
        if max_cost == min_cost:
            cost_score = 90.0
        else:
            cost_score = 100.0 - ((it['total_fare'] - min_cost) / (max_cost - min_cost) * 70.0)
        # Extra penalty if exceeds user budget
        if it['total_fare'] > max_budget:
            cost_score = max(10.0, cost_score - 30.0)

        # 2. Journey Duration Score (Weight: 20%)
        # Shorter duration -> higher score
        if max_dur == min_dur:
            duration_score = 90.0
        else:
            duration_score = 100.0 - ((it['duration_minutes'] - min_dur) / (max_dur - min_dur) * 60.0)

        # 3. Connection Safety Score (Weight: 20%)
        risk_res = assess_connection_risk(it)
        it['connection_risk'] = risk_res
        # Risk score 0-100 where 0 is safest; safety score is 100 - risk_score
        safety_score = 100.0 - risk_res['risk_score']

        # 4. Schedule Convenience (Weight: 15%)
        dep_dt = datetime.fromisoformat(it['departure_time'])
        dep_hour = dep_dt.hour
        convenience_score = 70.0
        if preferred_departure_window == 'morning' and 6 <= dep_hour <= 11:
            convenience_score = 100.0
        elif preferred_departure_window == 'afternoon' and 12 <= dep_hour <= 17:
            convenience_score = 100.0
        elif preferred_departure_window == 'evening' and 18 <= dep_hour <= 22:
            convenience_score = 100.0
        elif dep_hour < 5 or dep_hour >= 23:
            convenience_score = 40.0 # Red-eye penalty

        # 5. Preference Match (Weight: 15%)
        pref_score = 60.0
        if preferred_airline and preferred_airline.lower() in it['airline_name'].lower():
            pref_score += 35.0
        if it['is_direct']:
            pref_score += 10.0
        pref_score = min(100.0, pref_score)

        # Aggregate weighted score
        final_score = (
            (cost_score * 0.30) +
            (duration_score * 0.20) +
            (safety_score * 0.20) +
            (convenience_score * 0.15) +
            (pref_score * 0.15)
        )
        final_score = round(final_score, 1)

        # Explainability generation
        explanations = []
        if it['total_fare'] <= min_cost * 1.05:
            explanations.append(f"Lowest fare option available on this date (₹{it['total_fare']:,.0f})")
        elif it['total_fare'] <= max_budget:
            explanations.append(f"Comfortably within your stated budget limit (₹{it['total_fare']:,.0f} vs limit ₹{max_budget:,.0f})")

        if it['is_direct']:
            explanations.append(f"Direct non-stop flight saving layover hassle ({it['duration_minutes'] // 60}h {it['duration_minutes'] % 60}m)")
        elif it['connection_risk']['risk_level'] == 'LOW':
            explanations.append("Comfortable layover window with ample connection buffer")

        if convenience_score >= 90:
            explanations.append(f"Ideal departure schedule at {dep_dt.strftime('%I:%M %p')}")

        if preferred_airline and preferred_airline.lower() in it['airline_name'].lower():
            explanations.append(f"Operated by your preferred carrier ({it['airline_name']})")

        if not explanations:
            explanations.append("Solid standard itinerary offering dependable timing and value.")

        it['recommendation_score'] = final_score
        it['score_breakdown'] = {
            "cost_score": round(cost_score, 1),
            "duration_score": round(duration_score, 1),
            "safety_score": round(safety_score, 1),
            "convenience_score": round(convenience_score, 1),
            "preference_score": round(pref_score, 1)
        }
        it['explanations'] = explanations

        # Total journey cost estimate attachment
        journey_cost_details = calculate_journey_cost(
            base_fare=it['base_fare'],
            origin_code=it['origin_code'],
            destination_code=it['destination_code']
        )
        it['estimated_journey_cost'] = journey_cost_details['estimated_total_journey_cost']
        it['cost_breakdown'] = journey_cost_details

        scored_itineraries.append(it)

    # Sort descending by recommendation score
    scored_itineraries.sort(key=lambda x: x['recommendation_score'], reverse=True)
    return scored_itineraries

def compare_itineraries(itinerary_list):
    """Generates comparative analysis between 2 or 3 itineraries."""
    if not itinerary_list:
        return {}
    
    ranked = score_and_rank_itineraries(itinerary_list)
    winner = ranked[0]
    
    comparison = {
        "best_overall": winner['itinerary_id'],
        "reason": winner['explanations'][0] if winner['explanations'] else "Top balanced score across all attributes",
        "items": ranked
    }
    return comparison
