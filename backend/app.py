import os
import sys
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from config import Config

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import query_one, query_all, execute_commit
from routes.auth_routes import auth_bp, get_current_user
from routes.flight_routes import flight_bp
from routes.booking_routes import booking_bp
from routes.recommendation_routes import recommendation_bp
from routes.journey_cost_routes import journey_cost_bp
from routes.risk_routes import risk_bp
from routes.simulation_routes import simulation_bp
from routes.assistant_routes import assistant_bp
from routes.journey_routes import journey_bp
from routes.airport_routes import airport_bp
from routes.baggage_routes import baggage_bp
from routes.verification_routes import verification_bp
from routes.group_routes import group_bp
from routes.admin_routes import admin_bp

def create_app():
    frontend_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    app = Flask(__name__, static_folder=frontend_folder, static_url_path="")
    app.config.from_object(Config)

    # Enable Cross-Origin Resource Sharing
    CORS(app, supports_credentials=True)

    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(flight_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(recommendation_bp)
    app.register_blueprint(journey_cost_bp)
    app.register_blueprint(risk_bp)
    app.register_blueprint(simulation_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(journey_bp)
    app.register_blueprint(airport_bp)
    app.register_blueprint(baggage_bp)
    app.register_blueprint(verification_bp)
    app.register_blueprint(group_bp)
    app.register_blueprint(admin_bp)

    # Health Check Endpoint
    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        db_ok = True
        try:
            query_one("SELECT 1;")
        except Exception as e:
            db_ok = False
        return jsonify({
            "status": "healthy" if db_ok else "unhealthy",
            "service": "FlyWise AI Backend",
            "database_connected": db_ok,
            "version": "2.0.0"
        })

    # In-App Notifications Endpoints
    @app.route('/api/v1/notifications', methods=['GET'])
    def get_notifications():
        user = get_current_user()
        if not user:
            return jsonify({"status": "success", "notifications": []})
        notifs = query_all("""
            SELECT * FROM notifications 
            WHERE user_id = %s 
            ORDER BY created_at DESC LIMIT 10;
        """, (user['user_id'],))
        return jsonify({"status": "success", "notifications": notifs})

    @app.route('/api/v1/notifications/<int:notif_id>/read', methods=['POST'])
    def mark_notif_read(notif_id):
        execute_commit("UPDATE notifications SET delivery_status = 'read', read_at = NOW() WHERE notification_id = %s;", (notif_id,))
        return jsonify({"status": "success", "message": "Notification marked as read."})

    # Serve Frontend Single-Page App
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    # Error Handlers
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({"status": "error", "message": "API endpoint not found"}), 404
        return send_from_directory(app.static_folder, 'index.html')

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"status": "error", "message": "Internal server error occurred."}), 500

    return app

app = create_app()

if __name__ == '__main__':
    port = Config.FLASK_PORT
    print(f"\n========================================================")
    print(f" FLYWISE AI: Flight Booking & Journey Management System")
    print(f" Server running at http://localhost:{port}")
    print(f" Connected to MySQL database '{Config.DB_NAME}'")
    print(f" Gemini AI Model: {Config.GEMINI_MODEL}")
    print(f"========================================================\n")
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
