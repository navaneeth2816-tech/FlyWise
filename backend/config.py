import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "flywise_super_secret_jwt_key_2026")
    
    # Database Settings
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "Lamo@2008")
    DB_NAME = os.getenv("DB_NAME", "flywise_db")
    
    # Gemini AI
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    
    # Server
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"
    
    # JWT
    JWT_EXPIRATION_HOURS = 24
