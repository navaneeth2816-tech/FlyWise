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
        tables = []
        db_err = None
        try:
            res = query_all("SHOW TABLES;")
            tables = [list(r.values())[0] for r in res] if res else []
        except Exception as e:
            db_ok = False
            db_err = str(e)
        return jsonify({
            "status": "healthy" if db_ok and len(tables) > 0 else "degraded",
            "service": "FlyWise AI Backend",
            "database_connected": db_ok,
            "table_count": len(tables),
            "tables": tables,
            "db_host": Config.DB_HOST,
            "db_name": Config.DB_NAME,
            "error": db_err,
            "version": "2.0.0"
        })

    # System Database Initialization & Diagnostic Endpoint
    @app.route('/api/v1/system/init-db', methods=['GET', 'POST'])
    def system_init_db():
        try:
            import init_db
            init_db.init_database()
            import seed_data
            seed_data.seed()
            tables = query_all("SHOW TABLES;")
            table_list = [list(r.values())[0] for r in tables] if tables else []
            return jsonify({
                "status": "success",
                "message": "Database initialized and seeded successfully.",
                "table_count": len(table_list),
                "tables": table_list
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"Initialization failed: {str(e)}",
                "trace": traceback.format_exc()
            }), 500

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
        import traceback
        err_detail = str(getattr(e, 'original_exception', e))
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": "Internal server error occurred.",
            "detail": err_detail
        }), 500

    # Auto-initialize database tables if missing on startup
    try:
        tables = query_all("SHOW TABLES;")
        table_names = [list(r.values())[0].lower() for r in tables] if tables else []
        if 'users' not in table_names or 'flights' not in table_names or 'airports' not in table_names:
            print("Notice: Missing core database tables on startup. Initializing schema and seed data...")
            import init_db
            init_db.init_database()
            import seed_data
            seed_data.seed()
            print("Database initialized and seeded successfully on startup.")
        else:
            print(f"Database connected: {len(table_names)} tables verified.")
    except Exception as e:
        print(f"Startup database check notice: {e}")

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
