-- FLYWISE AI: Comprehensive Relational Database Schema
-- B.Tech CSE Database Management System Project
-- Database: flywise_db

SET FOREIGN_KEY_CHECKS = 0;

DROP VIEW IF EXISTS v_route_analytics;
DROP VIEW IF EXISTS v_airline_performance;
DROP VIEW IF EXISTS v_booking_summaries;
DROP VIEW IF EXISTS v_flight_search;

DROP TABLE IF EXISTS data_source_logs;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS ai_usage_logs;
DROP TABLE IF EXISTS ai_messages;
DROP TABLE IF EXISTS ai_conversations;
DROP TABLE IF EXISTS group_members;
DROP TABLE IF EXISTS group_trips;
DROP TABLE IF EXISTS user_travel_requirements;
DROP TABLE IF EXISTS flight_status_history;
DROP TABLE IF EXISTS journey_events;
DROP TABLE IF EXISTS journeys;
DROP TABLE IF EXISTS user_preferences;
DROP TABLE IF EXISTS cancellations;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS booking_seats;
DROP TABLE IF EXISTS booking_segments;
DROP TABLE IF EXISTS booking_passengers;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS passengers;
DROP TABLE IF EXISTS seats;
DROP TABLE IF EXISTS fares;
DROP TABLE IF EXISTS flights;
DROP TABLE IF EXISTS aircraft;
DROP TABLE IF EXISTS airlines;
DROP TABLE IF EXISTS airports;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- 1. USERS
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    preferred_language VARCHAR(50) DEFAULT 'en',
    role ENUM('user', 'admin') DEFAULT 'user',
    account_status ENUM('active', 'suspended', 'deactivated') DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_email (email),
    INDEX idx_user_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. AIRPORTS
CREATE TABLE airports (
    airport_id INT AUTO_INCREMENT PRIMARY KEY,
    iata_code VARCHAR(3) NOT NULL UNIQUE,
    icao_code VARCHAR(4) NOT NULL UNIQUE,
    airport_name VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL DEFAULT 'India',
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Kolkata',
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    terminal_information JSON,
    INDEX idx_airport_iata (iata_code),
    INDEX idx_airport_city (city)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. AIRLINES
CREATE TABLE airlines (
    airline_id INT AUTO_INCREMENT PRIMARY KEY,
    airline_name VARCHAR(100) NOT NULL,
    iata_code VARCHAR(3) NOT NULL UNIQUE,
    icao_code VARCHAR(4) NOT NULL UNIQUE,
    website VARCHAR(255),
    support_information JSON,
    INDEX idx_airline_iata (iata_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. AIRCRAFT
CREATE TABLE aircraft (
    aircraft_id INT AUTO_INCREMENT PRIMARY KEY,
    aircraft_code VARCHAR(20) NOT NULL UNIQUE,
    aircraft_model VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(100) NOT NULL,
    total_capacity INT NOT NULL,
    business_capacity INT NOT NULL DEFAULT 0,
    economy_capacity INT NOT NULL,
    status ENUM('active', 'maintenance', 'retired') DEFAULT 'active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. FLIGHTS
CREATE TABLE flights (
    flight_id INT AUTO_INCREMENT PRIMARY KEY,
    airline_id INT NOT NULL,
    aircraft_id INT NOT NULL,
    flight_number VARCHAR(20) NOT NULL,
    origin_airport_id INT NOT NULL,
    destination_airport_id INT NOT NULL,
    scheduled_departure DATETIME NOT NULL,
    scheduled_arrival DATETIME NOT NULL,
    actual_departure DATETIME NULL,
    actual_arrival DATETIME NULL,
    flight_status ENUM('scheduled', 'on-time', 'delayed', 'boarding', 'departed', 'in-air', 'arrived', 'cancelled') DEFAULT 'scheduled',
    data_source VARCHAR(50) DEFAULT 'system_schedule',
    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_flight_airline FOREIGN KEY (airline_id) REFERENCES airlines(airline_id) ON DELETE CASCADE,
    CONSTRAINT fk_flight_aircraft FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE RESTRICT,
    CONSTRAINT fk_flight_origin FOREIGN KEY (origin_airport_id) REFERENCES airports(airport_id) ON DELETE RESTRICT,
    CONSTRAINT fk_flight_destination FOREIGN KEY (destination_airport_id) REFERENCES airports(airport_id) ON DELETE RESTRICT,
    INDEX idx_flight_route (origin_airport_id, destination_airport_id, scheduled_departure),
    INDEX idx_flight_departure (scheduled_departure),
    INDEX idx_flight_number (flight_number),
    INDEX idx_flight_status (flight_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. FARES
CREATE TABLE fares (
    fare_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_id INT NOT NULL,
    travel_class ENUM('economy', 'business', 'first') DEFAULT 'economy',
    fare_type VARCHAR(50) DEFAULT 'standard',
    base_fare DECIMAL(10, 2) NOT NULL,
    taxes DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    mandatory_fees DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'INR',
    fare_conditions JSON,
    valid_from DATETIME NOT NULL,
    valid_until DATETIME NOT NULL,
    data_source VARCHAR(50) DEFAULT 'internal',
    CONSTRAINT fk_fare_flight FOREIGN KEY (flight_id) REFERENCES flights(flight_id) ON DELETE CASCADE,
    INDEX idx_fare_flight_class (flight_id, travel_class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. SEATS
CREATE TABLE seats (
    seat_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_id INT NOT NULL,
    seat_number VARCHAR(5) NOT NULL,
    travel_class ENUM('economy', 'business', 'first') DEFAULT 'economy',
    seat_status ENUM('available', 'reserved', 'booked', 'blocked') DEFAULT 'available',
    CONSTRAINT fk_seat_flight FOREIGN KEY (flight_id) REFERENCES flights(flight_id) ON DELETE CASCADE,
    UNIQUE KEY uq_flight_seat (flight_id, seat_number),
    INDEX idx_seat_status (flight_id, seat_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. PASSENGERS
CREATE TABLE passengers (
    passenger_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    full_name VARCHAR(150) NOT NULL,
    date_of_birth DATE NULL,
    contact_information JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_passenger_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_passenger_name (full_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. BOOKINGS
CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_reference VARCHAR(12) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    booking_status ENUM('confirmed', 'pending', 'cancelled', 'completed') DEFAULT 'confirmed',
    booking_currency VARCHAR(3) DEFAULT 'INR',
    total_amount DECIMAL(10, 2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    confirmed_at DATETIME NULL,
    CONSTRAINT fk_booking_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_booking_ref (booking_reference),
    INDEX idx_booking_user_status (user_id, booking_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. BOOKING_PASSENGERS
CREATE TABLE booking_passengers (
    booking_passenger_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    passenger_id INT NOT NULL,
    ticket_number VARCHAR(25) NOT NULL UNIQUE,
    passenger_status ENUM('confirmed', 'checked-in', 'boarded', 'cancelled') DEFAULT 'confirmed',
    CONSTRAINT fk_bp_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    CONSTRAINT fk_bp_passenger FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. BOOKING_SEGMENTS
CREATE TABLE booking_segments (
    segment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    flight_id INT NOT NULL,
    segment_order INT NOT NULL DEFAULT 1,
    fare_id INT NULL,
    segment_status ENUM('confirmed', 'cancelled', 'completed') DEFAULT 'confirmed',
    CONSTRAINT fk_bs_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    CONSTRAINT fk_bs_flight FOREIGN KEY (flight_id) REFERENCES flights(flight_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bs_fare FOREIGN KEY (fare_id) REFERENCES fares(fare_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. BOOKING_SEATS
CREATE TABLE booking_seats (
    booking_seat_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    passenger_id INT NOT NULL,
    seat_id INT NOT NULL,
    assignment_status ENUM('assigned', 'released') DEFAULT 'assigned',
    CONSTRAINT fk_bseat_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    CONSTRAINT fk_bseat_passenger FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bseat_seat FOREIGN KEY (seat_id) REFERENCES seats(seat_id) ON DELETE RESTRICT,
    UNIQUE KEY uq_bseat_booking_seat (booking_id, seat_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. PAYMENTS
CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    provider_reference VARCHAR(100) NOT NULL UNIQUE,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    payment_status ENUM('success', 'failed', 'refunded', 'pending') DEFAULT 'success',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    INDEX idx_payment_ref (provider_reference)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 14. CANCELLATIONS
CREATE TABLE cancellations (
    cancellation_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    requested_by INT NOT NULL,
    cancellation_status ENUM('pending', 'approved', 'processed', 'rejected') DEFAULT 'processed',
    cancellation_reason TEXT,
    calculated_refund_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    confirmed_refund_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    CONSTRAINT fk_cancel_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    CONSTRAINT fk_cancel_user FOREIGN KEY (requested_by) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 15. USER_PREFERENCES
CREATE TABLE user_preferences (
    preference_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    preference_type VARCHAR(50) NOT NULL,
    preference_value TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_pref_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_pref_user_type (user_id, preference_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 16. JOURNEYS
CREATE TABLE journeys (
    journey_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    booking_id INT NOT NULL,
    journey_status ENUM('confirmed', 'pre_departure', 'check_in', 'boarding', 'departed', 'connection_in_progress', 'arrived', 'completed', 'disrupted', 'cancelled') DEFAULT 'confirmed',
    planned_departure DATETIME NOT NULL,
    planned_arrival DATETIME NOT NULL,
    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_journey_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_journey_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    INDEX idx_journey_user (user_id, journey_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 17. JOURNEY_EVENTS
CREATE TABLE journey_events (
    journey_event_id INT AUTO_INCREMENT PRIMARY KEY,
    journey_id INT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_source VARCHAR(50) DEFAULT 'system',
    event_description TEXT NOT NULL,
    verification_status ENUM('verified', 'estimated', 'user_reported') DEFAULT 'verified',
    CONSTRAINT fk_je_journey FOREIGN KEY (journey_id) REFERENCES journeys(journey_id) ON DELETE CASCADE,
    INDEX idx_je_timestamp (journey_id, event_timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 18. FLIGHT_STATUS_HISTORY
CREATE TABLE flight_status_history (
    status_history_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_id INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    scheduled_time DATETIME NOT NULL,
    reported_time DATETIME NOT NULL,
    source VARCHAR(50) DEFAULT 'flight_radar_service',
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fsh_flight FOREIGN KEY (flight_id) REFERENCES flights(flight_id) ON DELETE CASCADE,
    INDEX idx_fsh_flight (flight_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 19. USER_TRAVEL_REQUIREMENTS
CREATE TABLE user_travel_requirements (
    requirement_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    requirement_type VARCHAR(50) NOT NULL,
    requirement_details JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_utr_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 20. GROUP_TRIPS
CREATE TABLE group_trips (
    group_trip_id INT AUTO_INCREMENT PRIMARY KEY,
    organiser_user_id INT NOT NULL,
    group_name VARCHAR(150) NOT NULL,
    origin_airport_id INT NOT NULL,
    destination_airport_id INT NOT NULL,
    departure_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_gt_organiser FOREIGN KEY (organiser_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_gt_origin FOREIGN KEY (origin_airport_id) REFERENCES airports(airport_id) ON DELETE RESTRICT,
    CONSTRAINT fk_gt_destination FOREIGN KEY (destination_airport_id) REFERENCES airports(airport_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 21. GROUP_MEMBERS
CREATE TABLE group_members (
    group_member_id INT AUTO_INCREMENT PRIMARY KEY,
    group_trip_id INT NOT NULL,
    user_id INT NULL,
    member_name VARCHAR(150) NOT NULL,
    budget DECIMAL(10, 2) NOT NULL DEFAULT 10000.00,
    travel_preferences JSON,
    invitation_status ENUM('pending', 'accepted', 'declined') DEFAULT 'pending',
    CONSTRAINT fk_gm_group FOREIGN KEY (group_trip_id) REFERENCES group_trips(group_trip_id) ON DELETE CASCADE,
    CONSTRAINT fk_gm_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 22. AI_CONVERSATIONS
CREATE TABLE ai_conversations (
    conversation_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    title VARCHAR(255) DEFAULT 'New Journey Planning',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_aic_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 23. AI_MESSAGES
CREATE TABLE ai_messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    sender_type ENUM('user', 'assistant', 'system') NOT NULL,
    message_content TEXT NOT NULL,
    metadata JSON NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_aim_conv FOREIGN KEY (conversation_id) REFERENCES ai_conversations(conversation_id) ON DELETE CASCADE,
    INDEX idx_aim_conv (conversation_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 24. AI_USAGE_LOGS
CREATE TABLE ai_usage_logs (
    usage_log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    model_identifier VARCHAR(100) NOT NULL,
    request_type VARCHAR(50) NOT NULL,
    input_token_count INT DEFAULT 0,
    output_token_count INT DEFAULT 0,
    latency_ms INT DEFAULT 0,
    request_status VARCHAR(20) DEFAULT 'success',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_aiu_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_aiu_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 25. NOTIFICATIONS
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    delivery_status ENUM('unread', 'read', 'archived') DEFAULT 'unread',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME NULL,
    CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_notif_user_status (user_id, delivery_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 26. DATA_SOURCE_LOGS
CREATE TABLE data_source_logs (
    source_log_id INT AUTO_INCREMENT PRIMARY KEY,
    provider_name VARCHAR(100) NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    request_status VARCHAR(20) NOT NULL,
    latency_ms INT DEFAULT 0,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =======================================================
-- DBMS VIEWS (Demonstrating Joins, Calculations, Aggregations)
-- =======================================================

-- View 1: Search View linking flights, airlines, aircraft, airports, base fares and available seats
CREATE VIEW v_flight_search AS
SELECT 
    f.flight_id,
    f.flight_number,
    f.flight_status,
    f.scheduled_departure,
    f.scheduled_arrival,
    TIMESTAMPDIFF(MINUTE, f.scheduled_departure, f.scheduled_arrival) AS duration_minutes,
    al.airline_id,
    al.airline_name,
    al.iata_code AS airline_code,
    ac.aircraft_model,
    orig.airport_id AS origin_airport_id,
    orig.iata_code AS origin_code,
    orig.airport_name AS origin_name,
    orig.city AS origin_city,
    dest.airport_id AS destination_airport_id,
    dest.iata_code AS destination_code,
    dest.airport_name AS destination_name,
    dest.city AS destination_city,
    COALESCE(fa.base_fare, 3500.00) AS base_fare,
    COALESCE(fa.taxes, 750.00) AS taxes,
    COALESCE(fa.mandatory_fees, 250.00) AS mandatory_fees,
    (COALESCE(fa.base_fare, 3500.00) + COALESCE(fa.taxes, 750.00) + COALESCE(fa.mandatory_fees, 250.00)) AS total_fare,
    COALESCE(fa.travel_class, 'economy') AS travel_class,
    COUNT(CASE WHEN s.seat_status = 'available' THEN 1 END) AS available_seats,
    COUNT(s.seat_id) AS total_seats
FROM flights f
JOIN airlines al ON f.airline_id = al.airline_id
JOIN aircraft ac ON f.aircraft_id = ac.aircraft_id
JOIN airports orig ON f.origin_airport_id = orig.airport_id
JOIN airports dest ON f.destination_airport_id = dest.airport_id
LEFT JOIN fares fa ON f.flight_id = fa.flight_id AND fa.travel_class = 'economy'
LEFT JOIN seats s ON f.flight_id = s.flight_id
GROUP BY 
    f.flight_id, fa.fare_id;

-- View 2: Detailed Booking Summaries with User, Payment, Segments
CREATE VIEW v_booking_summaries AS
SELECT 
    b.booking_id,
    b.booking_reference,
    b.booking_status,
    b.total_amount,
    b.booking_currency,
    b.created_at AS booking_date,
    u.user_id,
    u.full_name AS booked_by,
    u.email AS user_email,
    p.provider_reference AS payment_reference,
    p.payment_status,
    COUNT(DISTINCT bp.passenger_id) AS passenger_count,
    COUNT(DISTINCT bs.flight_id) AS segment_count,
    j.journey_id,
    j.journey_status
FROM bookings b
JOIN users u ON b.user_id = u.user_id
LEFT JOIN payments p ON b.booking_id = p.booking_id
LEFT JOIN booking_passengers bp ON b.booking_id = bp.booking_id
LEFT JOIN booking_segments bs ON b.booking_id = bs.booking_id
LEFT JOIN journeys j ON b.booking_id = j.booking_id
GROUP BY b.booking_id, p.payment_id, j.journey_id;

-- View 3: Airline Performance Analytics (Demonstrating Aggregation, GROUP BY)
CREATE VIEW v_airline_performance AS
SELECT 
    al.airline_id,
    al.airline_name,
    al.iata_code,
    COUNT(f.flight_id) AS total_flights,
    ROUND(AVG(TIMESTAMPDIFF(MINUTE, f.scheduled_departure, f.scheduled_arrival)), 1) AS avg_flight_duration,
    COUNT(CASE WHEN f.flight_status = 'delayed' THEN 1 END) AS delayed_flights,
    ROUND((COUNT(CASE WHEN f.flight_status = 'delayed' THEN 1 END) * 100.0 / NULLIF(COUNT(f.flight_id), 0)), 2) AS delay_percentage,
    COALESCE(SUM(b.total_amount), 0.00) AS total_revenue_generated
FROM airlines al
LEFT JOIN flights f ON al.airline_id = f.airline_id
LEFT JOIN booking_segments bs ON f.flight_id = bs.flight_id
LEFT JOIN bookings b ON bs.booking_id = b.booking_id AND b.booking_status = 'confirmed'
GROUP BY al.airline_id;

-- View 4: Popular Route Analytics
CREATE VIEW v_route_analytics AS
SELECT 
    orig.iata_code AS origin,
    orig.city AS origin_city,
    dest.iata_code AS destination,
    dest.city AS destination_city,
    COUNT(f.flight_id) AS daily_flights,
    MIN(fa.base_fare) AS lowest_base_fare,
    ROUND(AVG(fa.base_fare), 2) AS avg_base_fare,
    MAX(fa.base_fare) AS highest_base_fare,
    ROUND(AVG(TIMESTAMPDIFF(MINUTE, f.scheduled_departure, f.scheduled_arrival)), 0) AS avg_duration_minutes
FROM flights f
JOIN airports orig ON f.origin_airport_id = orig.airport_id
JOIN airports dest ON f.destination_airport_id = dest.airport_id
LEFT JOIN fares fa ON f.flight_id = fa.flight_id
GROUP BY orig.airport_id, dest.airport_id;

-- =======================================================
-- STORED PROCEDURES (DBMS syllabus requirement)
-- =======================================================

DROP PROCEDURE IF EXISTS sp_search_direct_flights;
DELIMITER //
CREATE PROCEDURE sp_search_direct_flights(
    IN p_origin VARCHAR(3),
    IN p_destination VARCHAR(3),
    IN p_departure_date DATE
)
BEGIN
    SELECT 
        v.*
    FROM v_flight_search v
    WHERE v.origin_code = p_origin
      AND v.destination_code = p_destination
      AND DATE(v.scheduled_departure) = p_departure_date
    ORDER BY v.total_fare ASC;
END //
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_get_booking_summary;
DELIMITER //
CREATE PROCEDURE sp_get_booking_summary(
    IN p_booking_ref VARCHAR(12)
)
BEGIN
    SELECT * FROM v_booking_summaries
    WHERE booking_reference = p_booking_ref;
END //
DELIMITER ;

-- =======================================================
-- TRIGGERS (DBMS syllabus requirement)
-- =======================================================

DROP TRIGGER IF EXISTS trg_after_flight_status_update;
DELIMITER //
CREATE TRIGGER trg_after_flight_status_update
AFTER UPDATE ON flights
FOR EACH ROW
BEGIN
    IF OLD.flight_status <> NEW.flight_status THEN
        INSERT INTO flight_status_history (
            flight_id,
            status,
            scheduled_time,
            reported_time,
            source,
            recorded_at
        ) VALUES (
            NEW.flight_id,
            NEW.flight_status,
            NEW.scheduled_departure,
            NOW(),
            'system_trigger',
            NOW()
        );
    END IF;
END //
DELIMITER ;
