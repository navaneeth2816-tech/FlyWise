import sys
import os

# Insert backend directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import create_app
from config import Config

app = create_app()

if __name__ == '__main__':
    port = Config.FLASK_PORT
    print("\n" + "=" * 65)
    print("  FLYWISE AI: AI-Powered Flight Booking & Travel System")
    print(f"  Web Application: http://localhost:{port}")
    print(f"  Database Connected: MySQL (flywise_db) on localhost:{Config.DB_PORT}")
    print(f"  AI Intelligence: Google Gemini ({Config.GEMINI_MODEL})")
    print("=" * 65 + "\n")
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
