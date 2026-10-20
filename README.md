# FLYWISE AI — Intelligent Flight Booking & Journey Management System

> **B.Tech CSE Database Management System (DBMS) Project**  
> **Version:** 2.0  
> **Database:** MySQL 8.0 (26 Relational Tables, 4 Views, Stored Procedures, Triggers, Transactions)  
> **Backend:** Python Flask REST API  
> **Frontend:** HTML5, CSS3, JavaScript (Responsive Single-Page Application, Chart.js)  
> **Artificial Intelligence:** Google Gemini AI API (`gemini-3.5-flash`)  

---

## 1. Executive Summary & Product Vision

**FlyWise AI** is an intelligent flight-booking and travel-management platform designed to help travellers discover suitable flights, compare complete journey costs, assess connection risks, manage bookings, and receive personalised travel assistance.

Unlike conventional booking engines that focus merely on searching and booking, FlyWise AI answers five critical travel questions:
1. **Which flight is most suitable for my requirements?** (Personalised 5-factor ranking engine with natural-language explainability)
2. **What is the estimated total cost of my journey?** (Itemized total journey cost calculator including airfare, baggage, seat fees, and ground airport transit)
3. **What risks or difficulties could affect my itinerary?** (Rule-based connection-risk predictor evaluating terminal changes, airline reliability, and layover buffers)
4. **What should I do if my travel plans change?** (Emergency Travel Mode, disruption radar, and statutory DGCA passenger rights)
5. **How can I manage my entire journey from one place?** (Dynamic 10-stage Flight Journey Digital Twin, interactive checklists, and Gemini AI assistant)

---

## 2. Technology Stack

| Layer | Component | Technology Used |
|---|---|---|
| **Frontend** | User Interface | HTML5, CSS3 (Modern Aviation Theme), Vanilla JavaScript, Chart.js |
| **Backend** | REST APIs | Python Flask 3.1, Flask-CORS, PyJWT, Werkzeug Security |
| **Database** | Relational RDBMS | MySQL 8.0 (InnoDB, ACID Transactions, Row-level Locking, Triggers, Views) |
| **Database Connector** | DB Connectivity | PyMySQL, connection pooling, context-managed transactions |
| **AI Assistant** | Conversational Intelligence | Google Gemini AI (`gemini-3.5-flash`) with database grounding & fallback |
| **Testing** | Automated Quality Assurance | Python `unittest` suite testing database, ACID concurrency, and AI APIs |

---

## 3. Database Management System (DBMS) Syllabus Demonstration

As a comprehensive B.Tech CSE DBMS project, FlyWise AI demonstrates all required database concepts:

### 3.1 26 Relational Tables
1. `users` — User credentials, roles (`user`, `admin`), hashed passwords.
2. `airports` — Indian & international hubs (DEL, BOM, BLR, MAA, HYD, TIR, GOI, PNQ, JAI, DXB), coordinates, terminal layouts.
3. `airlines` — IndiGo, Air India, Vistara, SpiceJet, Akasa Air, support policies.
4. `aircraft` — Aircraft fleet models (A320neo, B787 Dreamliner, B737 MAX, A321neo).
5. `flights` — Scheduled flight instances across upcoming dates.
6. `fares` — Economy Saver, Flexi, and Business Club fares with detailed conditions.
7. `seats` — Physical aircraft seat map with `UNIQUE(flight_id, seat_number)` constraints.
8. `passengers` — Traveler profiles and government ID records.
9. `bookings` — Bookings with unique 8-character PNR references (`FW-XXXXXX`).
10. `booking_passengers` — Issued ticket numbers (`TK-6E-XXXXXXXXXX`).
11. `booking_segments` — Multi-segment flight routing for direct & connecting journeys.
12. `booking_seats` — Seat allocations with unique constraint `uq_bseat_booking_seat`.
13. `payments` — Simulated payment transactions and gateway references.
14. `cancellations` — Cancellation records and computed refund distributions.
15. `user_preferences` — User budget, airline, and departure window preferences.
16. `journeys` — Dynamic user journeys mapped to the Digital Twin.
17. `journey_events` — Real-time event log (verified ATC status, check-in, delays).
18. `flight_status_history` — Historical schedule modifications.
19. `user_travel_requirements` — Accessibility and wheelchair assistance preferences.
20. `group_trips` — Multi-traveler group itineraries.
21. `group_members` — Individual budgets and seating preferences.
22. `ai_conversations` — Conversational assistant sessions.
23. `ai_messages` — Grounded AI chat logs.
24. `ai_usage_logs` — Token counts, latency, and model metrics.
25. `notifications` — In-app flight disruption alerts and travel reminders.
26. `data_source_logs` — System operational telemetry.

### 3.2 Relational Views
* `v_flight_search` — Multi-table join of flights, airlines, aircraft, airports, and available seat counts.
* `v_booking_summaries` — Joins bookings, users, passengers, payments, and journey states.
* `v_airline_performance` — Aggregations (`COUNT`, `AVG`, `SUM`, `GROUP BY`) calculating flight count, delay percentage, and revenue per carrier.
* `v_route_analytics` — Analytics evaluating minimum, average, and maximum base fares per route.

### 3.3 Transactions & Concurrency Control
* **ACID Transactions**: Handled via `START TRANSACTION`, `COMMIT`, and `ROLLBACK` context managers.
* **Concurrency Protection**: During seat reservation, row-level locking (`SELECT ... FOR UPDATE`) guarantees two simultaneous users cannot book the same seat.

### 3.4 Triggers & Stored Procedures
* `trg_after_flight_status_update`: Trigger fired upon any flight status change to automatically record an audit entry in `flight_status_history`.
* `sp_search_direct_flights`: Parameterized stored procedure for flight route and date retrieval.
* `sp_get_booking_summary`: Stored procedure retrieving comprehensive booking records by PNR.

---

## 4. Key Modules & Features

1. **Intelligent Flight Search**:
   * Direct and 1-stop connecting flights with realistic layovers.
   * Real-time filtering by airline, price slider, departure window (morning, afternoon, evening), and stops.
   * Side-by-side flight comparison tray for up to 3 flights.
2. **Personalised Recommendation Engine**:
   * Multi-factor scoring model: 30% Total Cost + 20% Duration + 20% Connection Safety + 15% Convenience + 15% User Preferences.
   * Natural-language explainability tags on every flight card.
3. **Total Journey Cost Calculator**:
   * Itemized breakdown: Base Fare + Taxes + Baggage Allowance + Seat Selection + Ground Transit (Cab / Metro) + Add-ons.
4. **Connection-Risk Predictor**:
   * Categorizes layover risk as LOW, MODERATE, or HIGH considering terminal changes, airport distances, and airline reliability.
5. **Interactive Seat Selection & Booking**:
   * Visual airplane fuselage map with Business class, Economy window/aisle, and free middle seats.
   * Instant e-Ticket generation with unique PNR and printable format.
6. **Flight Journey Digital Twin**:
   * 10-stage dynamic lifecycle tracker: Confirmed → Pre-departure → Check-in → Boarding → Departed → In-transit → Arrived → Completed.
7. **Emergency Travel Mode**:
   * Disruption radar triggered on flight delays to discover alternative flights, provide statutory DGCA rights, and link priority assistance.
8. **Gemini AI Travel Assistant**:
   * Conversational assistant with direct MySQL schedule grounding, suggested prompt shortcuts, and automatic fallback.
9. **Smart Travel Tools**:
   * **What-If Date Simulator**: Evaluates ±1 to 3 days date shifts for price savings.
   * **Smart Alternative-Airport Finder**: Compares nearby airports (Tirupati vs Chennai, Pune vs Mumbai) with cab costs and net savings.
   * **Smart Baggage Policy Assistant**: Calculates checked/cabin limits and excess fees for Indian carriers.
   * **Booking Verification & Scam Assistant**: Detects fraudulent SMS, fake links, and unauthorized UPI payment demands.
   * **Group Travel Optimiser**: Consolidates multiple budgets to discover common affordable flights.
10. **Administrative Management Console**:
    * Operational KPI tiles, Chart.js visualizations, database trigger testing, and Gemini API telemetry.

---

## 5. Quick Start & Execution

### 5.1 Prerequisites
* Python 3.10+ (Verified on Python 3.15)
* MySQL Server (Running on localhost:3306)

### 5.2 Environment Setup
The backend configuration is stored in `.env`:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=Lamo@2008
DB_NAME=flywise_db
SECRET_KEY=flywise_super_secret_jwt_key_2026
GEMINI_API_KEY=AQ.Ab8RN6I_ouDZtFVH3me8cm20uiWHkglI1FSwA8K3a-KlVHf1JA
FLASK_PORT=5000
```

### 5.3 Database Initialization & Seeding
To initialize the 26 tables, views, triggers, and seed 540+ flight records:
```powershell
python backend/init_db.py
python backend/seed_data.py
```

### 5.4 Run Automated Tests
Execute the comprehensive test suite verifying database views, ACID booking concurrency, and AI grounding:
```powershell
python backend/tests/test_suite.py
```

### 5.5 Start the Application
Launch the FlyWise AI server:
```powershell
python run.py
```
Open your browser and navigate to:
```
http://localhost:5000
```

---

## 6. Demo User & Admin Credentials

| Role | Email | Password | Capabilities |
|---|---|---|---|
| **Traveller (User)** | `navaneeth@flywise.ai` | `Password@123` | Search, book flights, view Digital Twin, customize preferences |
| **Administrator** | `admin@flywise.ai` | `Admin@123` | Access Admin Console, Chart.js metrics, test triggers, inspect telemetry |

---

## 7. REST API Documentation (Sample Endpoints)

* `GET /api/v1/health` — Health check verifying MySQL database connection.
* `POST /api/v1/auth/login` — Authenticate and issue JWT token.
* `GET /api/v1/flights/search` — Search flights with parameters (`origin`, `destination`, `date`, `class`, `sort_by`).
* `GET /api/v1/flights/<id>/seats` — Aircraft seat map and availability.
* `POST /api/v1/bookings` — ACID transactional booking creation with `FOR UPDATE` seat locking.
* `POST /api/v1/bookings/<id>/cancel` — Cancel reservation and calculate refund.
* `POST /api/v1/recommendations/compare` — Compare multiple itineraries side-by-side.
* `POST /api/v1/journey-cost/calculate` — Itemized total journey cost estimation.
* `POST /api/v1/assistant/chat` — Gemini AI conversational assistant.
* `POST /api/v1/simulation/alternatives` — What-If date shift simulation.
* `POST /api/v1/verification/analyze-message` — Fraud & phishing analysis.
* `GET /api/v1/admin/analytics` — Formatted analytics for Chart.js rendering.
