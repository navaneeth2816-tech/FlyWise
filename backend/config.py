import os
import urllib.parse
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
    DB_SSL = os.getenv("DB_SSL", "").lower() in ("true", "1", "required")

    # Cloud Database URL parser (Render / Railway / TiDB / PlanetScale / Aiven)
    _db_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL") or os.getenv("JAWSDB_URL")
    if _db_url and ("mysql" in _db_url or "mariadb" in _db_url):
        try:
            _parsed = urllib.parse.urlparse(_db_url)
            if _parsed.hostname:
                DB_HOST = _parsed.hostname
            if _parsed.port:
                DB_PORT = int(_parsed.port)
            if _parsed.username:
                DB_USER = urllib.parse.unquote(_parsed.username)
            if _parsed.password:
                DB_PASSWORD = urllib.parse.unquote(_parsed.password)
            if _parsed.path and len(_parsed.path) > 1:
                DB_NAME = _parsed.path.lstrip('/')
            # Auto-enable SSL for cloud databases or if requested in query parameters
            if "ssl" in _db_url.lower() or any(k in (_parsed.hostname or '').lower() for k in ("aivencloud", "tidb", "planetscale", "aws", "rds", "railway")):
                DB_SSL = True
        except Exception as _e:
            print(f"Notice: Failed to parse DATABASE_URL: {_e}")
    
    # Gemini AI
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-robotics-er-2-preview")
    
    # Server
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"
    
    # JWT
    JWT_EXPIRATION_HOURS = 24
