import os
import time
import json
import re
import requests
from datetime import datetime, timedelta
from config import Config
from database import query_all, query_one, execute_commit
from services.flight_service import search_flights
from services.recommendation_service import score_and_rank_itineraries

SYSTEM_INSTRUCTION = """You are FlyWise AI, a friendly, highly intelligent, and versatile AI assistant.
You can answer ANY question — whether general knowledge (science, history, technology, geography, everyday questions, math) or specific to travel, aviation, and journey management.

When answering travel or flight questions:
1. Ground your answers accurately in the provided flight schedules and database information. Never fabricate flight numbers or fares.
2. Explain why specific flights are recommended based on budget, duration, and connection safety.
3. For connection risks, warn empathetically if a layover is tight (< 60 minutes) or requires terminal transfers.
4. Maintain a polite, clear, and structured Markdown response (using bold text, bullet points, and concise summaries).

When answering general questions:
- Provide direct, helpful, accurate, and conversational responses without unnecessary travel jargon, but remain welcoming as FlyWise AI.
"""

def extract_search_entities(user_message):
    """
    Extracts origin, destination, dates, budget from user message with heuristics
    to provide instant accurate backend flight data grounding.
    """
    msg = user_message.lower()
    
    # Common Indian & International Airport Aliases
    airport_aliases = {
        "tirupati": "TIR", "renigunta": "TIR", "tir": "TIR",
        "delhi": "DEL", "new delhi": "DEL", "indira gandhi": "DEL", "del": "DEL",
        "mumbai": "BOM", "bombay": "BOM", "bom": "BOM",
        "bangalore": "BLR", "bengaluru": "BLR", "blr": "BLR",
        "chennai": "MAA", "madras": "MAA", "maa": "MAA",
        "hyderabad": "HYD", "hyd": "HYD",
        "goa": "GOI", "dabolim": "GOI", "goi": "GOI",
        "pune": "PNQ", "pnq": "PNQ",
        "jaipur": "JAI", "jai": "JAI",
        "dubai": "DXB", "dxb": "DXB"
    }
    
    origin = None
    destination = None
    
    # 1. Check for "from X to Y" or "X to Y" patterns
    from_to_match = re.search(r'(?:from\s+)?([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)(?:\s+flights|\s+flight|\s+next|\s+on|\s+this|\s+tomorrow|\s+under|\s+with|\s+in|$|\.|\,)', msg)
    if from_to_match:
        cand_orig = from_to_match.group(1).strip()
        cand_dest = from_to_match.group(2).strip()
        for k, code in airport_aliases.items():
            if re.search(r'\b' + re.escape(k) + r'\b', cand_orig) and not origin:
                origin = code
            if re.search(r'\b' + re.escape(k) + r'\b', cand_dest) and not destination:
                destination = code

    # 2. Positional keyword scanning based on order of appearance in message
    if not origin or not destination:
        occurrences = []
        for word, code in airport_aliases.items():
            for m in re.finditer(r'\b' + re.escape(word) + r'\b', msg):
                occurrences.append((m.start(), code))
        occurrences.sort(key=lambda x: x[0])
        seen = []
        for _, code in occurrences:
            if code not in seen:
                seen.append(code)
        if len(seen) >= 2:
            if not origin:
                origin = seen[0]
            if not destination:
                destination = seen[1]

    # Budget extraction (e.g. ₹7,000, 7000, under 6000, budget 8000)
    budget = None
    budget_match = re.search(r'(?:₹|rs\.?|inr|budget\s*(?:of|is|:)?|under|within)\s*([0-9]+(?:,[0-9]+)?)', msg)
    if budget_match:
        try:
            budget = float(budget_match.group(1).replace(',', ''))
        except Exception:
            budget = None

    # Date extraction
    dep_date = (datetime(2026, 10, 20) + timedelta(days=3)).strftime("%Y-%m-%d")
    if "today" in msg:
        dep_date = "2026-10-20"
    elif "tomorrow" in msg:
        dep_date = "2026-10-21"
    elif "next friday" in msg or "friday" in msg:
        dep_date = "2026-10-23"
    elif "next monday" in msg or "monday" in msg:
        dep_date = "2026-10-26"
    elif "weekend" in msg or "saturday" in msg:
        dep_date = "2026-10-24"

    return {
        "origin": origin,
        "destination": destination,
        "departure_date": dep_date,
        "budget": budget
    }

def process_assistant_chat(user_message, user_id=None, conversation_id=None):
    """
    Orchestrates conversational AI interaction:
    1. Extracts travel entities & queries FlyWise DB when applicable.
    2. Builds grounded context and multi-turn chat history.
    3. Calls Gemini API with fallback models.
    4. Logs AI usage & messages to MySQL safely.
    5. Returns response with grounded flight cards if flights were requested.
    """
    start_time = time.time()
    
    # Ensure conversation exists
    if not conversation_id:
        try:
            conversation_id = execute_commit("""
                INSERT INTO ai_conversations (user_id, title)
                VALUES (%s, %s);
            """, (user_id, user_message[:50]))
        except Exception as dbe:
            print(f"Notice: Conversation insert skipped: {dbe}")
            conversation_id = int(time.time())
    
    # Fetch recent conversation history (last 6 messages) for multi-turn context
    recent_history = []
    try:
        recent_history = query_all("""
            SELECT sender_type, message_content 
            FROM ai_messages 
            WHERE conversation_id = %s 
            ORDER BY created_at ASC 
            LIMIT 6;
        """, (conversation_id,)) or []
    except Exception as dbe:
        print(f"Notice: Message history query skipped: {dbe}")

    # Record current user message in DB
    try:
        execute_commit("""
            INSERT INTO ai_messages (conversation_id, sender_type, message_content)
            VALUES (%s, 'user', %s);
        """, (conversation_id, user_message))
    except Exception as dbe:
        print(f"Notice: User message insert skipped: {dbe}")

    # Entity extraction & DB Grounding for travel queries
    entities = extract_search_entities(user_message)
    grounded_data = {}
    grounded_itineraries = []

    if entities['origin'] and entities['destination']:
        try:
            raw_results = search_flights(
                origin_code=entities['origin'],
                destination_code=entities['destination'],
                departure_date=entities['departure_date'],
                max_stops=1
            ) or []
            if raw_results:
                ranked = score_and_rank_itineraries(raw_results, {"max_budget": entities['budget'] or 12000})
                grounded_itineraries = ranked[:4]
                grounded_data['matching_flights'] = [
                    {
                        "flight_number": it['segments'][0]['flight_number'],
                        "airline": it['airline_name'],
                        "departure": it['departure_time'],
                        "arrival": it['arrival_time'],
                        "duration": f"{it['duration_minutes'] // 60}h {it['duration_minutes'] % 60}m",
                        "stops": it['stops'],
                        "ticket_fare_inr": it['total_fare'],
                        "estimated_total_journey_cost_inr": it['estimated_journey_cost'],
                        "recommendation_score": it['recommendation_score'],
                        "connection_risk": it['connection_risk']['risk_level'],
                        "key_reasons": it['explanations']
                    }
                    for it in grounded_itineraries
                ]
        except Exception as fe:
            print(f"Notice: search_flights error during chat grounding: {fe}")

    # Baggage query check
    if "baggage" in user_message.lower():
        try:
            airlines = query_all("SELECT airline_name, iata_code, support_information FROM airlines;") or []
            grounded_data['baggage_policies'] = [
                {"airline": a['airline_name'], "code": a['iata_code'], "info": json.loads(a['support_information']) if isinstance(a['support_information'], str) else a['support_information']}
                for a in airlines
            ]
        except Exception as be:
            print(f"Notice: baggage query skipped: {be}")

    # Airport query check
    if any(k in user_message.lower() for k in ["airport", "terminal", "metro", "transit", "wheelchair", "delhi", "mumbai", "bangalore"]):
        try:
            airports = query_all("SELECT iata_code, airport_name, city, terminal_information FROM airports LIMIT 6;") or []
            grounded_data['airports'] = [
                {"code": a['iata_code'], "name": a['airport_name'], "city": a['city'], "details": json.loads(a['terminal_information']) if isinstance(a['terminal_information'], str) else a['terminal_information']}
                for a in airports
            ]
        except Exception as ae:
            print(f"Notice: airport query skipped: {ae}")

    # Build prompt
    prompt_parts = [
        f"User question: {user_message}\n",
        f"Today's date: 2026-10-20.\n"
    ]
    if grounded_data:
        prompt_parts.append(f"Grounded Application Data from Flight Database:\n{json.dumps(grounded_data, indent=2)}\n")
        prompt_parts.append("Answer accurately using the grounded flights above. Mention the airline, schedule, fare in INR, and connection details.\n")
    else:
        prompt_parts.append("Answer this question helpfully, politely, and thoroughly. If it is a general question (science, history, technology, math, facts), answer it directly. If it is travel-related, offer relevant advice.\n")

    current_prompt = "".join(prompt_parts)

    # Format multi-turn contents
    contents_payload = []
    for h in recent_history:
        role = 'user' if h.get('sender_type') == 'user' else 'model'
        contents_payload.append({
            "role": role,
            "parts": [{"text": h.get('message_content', '')}]
        })
    contents_payload.append({
        "role": "user",
        "parts": [{"text": current_prompt}]
    })

    assistant_reply = ""
    status = "success"
    latency_ms = 0

    # Models to attempt (deduplicated priority list)
    models_to_try = []
    for m in [Config.GEMINI_MODEL, "gemini-3-flash-preview", "gemini-3.1-flash-lite", "gemma-4-26b-a4b-it", "gemini-3.5-flash", "gemini-3.5-flash-lite"]:
        if m and m not in models_to_try:
            models_to_try.append(m)

    model_used = None
    if Config.GEMINI_API_KEY:
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={Config.GEMINI_API_KEY}"
                payload = {
                    "systemInstruction": {
                        "parts": [{"text": SYSTEM_INSTRUCTION}]
                    },
                    "contents": contents_payload,
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 1000
                    }
                }
                resp = requests.post(url, json=payload, timeout=8)
                latency_ms = int((time.time() - start_time) * 1000)

                if resp.status_code == 200:
                    resp_json = resp.json()
                    candidates = resp_json.get("candidates", [])
                    if candidates:
                        assistant_reply = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if assistant_reply:
                            model_used = model_name
                            status = "success"
                            break
                else:
                    print(f"Gemini API ({model_name}) status {resp.status_code}: {resp.text[:120]}")
                    status = f"http_{resp.status_code}"
            except Exception as e:
                print(f"Gemini API ({model_name}) error: {e}")
                status = "error"
                latency_ms = int((time.time() - start_time) * 1000)
    else:
        print("Notice: GEMINI_API_KEY not configured; using intelligent grounded fallback.")

    # Intelligent Grounded Fallback if API was unavailable or rate-limited
    if not assistant_reply:
        if grounded_itineraries:
            top = grounded_itineraries[0]
            assistant_reply = f"""I found **{len(grounded_itineraries)} scheduled flights** for your trip from **{entities['origin']} to {entities['destination']}** on **{entities['departure_date']}**:

### Top Recommendation: **{top['airline_name']} ({top['segments'][0]['flight_number']})**
- **Score:** {top['recommendation_score']}/100
- **Airfare:** ₹{top['total_fare']:,.0f} (Estimated Total Journey Cost: ₹{top['estimated_journey_cost']:,.0f})
- **Duration:** {top['duration_minutes'] // 60}h {top['duration_minutes'] % 60}m ({'Direct Non-stop' if top['is_direct'] else '1-Stop'})
- **Connection Safety:** {top['connection_risk']['risk_level']} Risk ({top['connection_risk']['category']})
- **Why it fits you:** {', '.join(top['explanations'])}

Review the flight cards below to book your seat or compare complete cost breakdowns."""
        elif entities.get('origin') and entities.get('destination'):
            assistant_reply = f"I searched the flight database for **{entities['origin']} to {entities['destination']}**, but no scheduled flights were found for {entities['departure_date']}. Try shifting your departure date using our What-If Date Simulator or checking nearby airport hubs like Chennai (MAA) or Bengaluru (BLR)."
        else:
            assistant_reply = "I am ready to help you! You can ask me any general knowledge questions or travel queries — for example: *'Find flights from Tirupati to Delhi under ₹7,000'*, *'What are the baggage rules for Air India?'*, or *'What is the connection risk at Mumbai Airport?'*"

    # Store assistant reply in DB
    try:
        execute_commit("""
            INSERT INTO ai_messages (conversation_id, sender_type, message_content, metadata)
            VALUES (%s, 'assistant', %s, %s);
        """, (conversation_id, assistant_reply, json.dumps({"flight_count": len(grounded_itineraries), "status": status})))
        execute_commit("""
            INSERT INTO ai_usage_logs (user_id, model_identifier, request_type, latency_ms, request_status)
            VALUES (%s, %s, 'assistant_chat', %s, %s);
        """, (user_id, model_used or Config.GEMINI_MODEL, latency_ms, status))
    except Exception as dbe:
        print(f"Notice: Assistant message insert skipped: {dbe}")

    return {
        "conversation_id": conversation_id,
        "reply": assistant_reply,
        "itineraries": grounded_itineraries,
        "entities": entities,
        "latency_ms": latency_ms
    }
