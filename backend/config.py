import os
import urllib.parse
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file (check backend directory and project root)
_env_backend = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_backend):
    load_dotenv(_env_backend)
_env_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(_env_root):
    load_dotenv(_env_root)
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "flywise_super_secret_jwt_key_2026")

    # Database Settings (defaults to laptop local MySQL: localhost:3306)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "Lamo@2008")
    DB_NAME = os.getenv("DB_NAME", "flywise_db")
    DB_SSL = os.getenv("DB_SSL", "").lower() in ("true", "1", "required")

    # Cloud Database URL parser (Render / Railway / TiDB / PlanetScale / Aiven / AWS RDS)
    # When deployed to cloud (e.g. Render), DATABASE_URL environment variable is provided
    _db_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL") or os.getenv("JAWSDB_URL")
    if _db_url and ("mysql" in _db_url.lower() or "mariadb" in _db_url.lower()):
        try:
            _clean_url = _db_url
            if _clean_url.startswith("mysql+pymysql://"):
                _clean_url = "mysql://" + _clean_url[len("mysql+pymysql://"):]
            elif _clean_url.startswith("mysql+mysqlconnector://"):
                _clean_url = "mysql://" + _clean_url[len("mysql+mysqlconnector://"):]
            _parsed = urllib.parse.urlparse(_clean_url)
            if _parsed.hostname:
                DB_HOST = _parsed.hostname
            if _parsed.port:
                DB_PORT = int(_parsed.port)
            if _parsed.username:
                DB_USER = urllib.parse.unquote(_parsed.username)
            if _parsed.password:
                DB_PASSWORD = urllib.parse.unquote(_parsed.password)
            if _parsed.path and len(_parsed.path) > 1:
                DB_NAME = _parsed.path.lstrip('/').split('?')[0]
            # Auto-enable SSL for cloud databases or if requested in query parameters
            if "ssl" in _db_url.lower() or any(k in (_parsed.hostname or '').lower() for k in ("aivencloud", "tidb", "planetscale", "aws", "rds", "railway", "cleardb")):
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
