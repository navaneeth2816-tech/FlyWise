import jwt
import functools
import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from database import query_one, query_all, execute_commit

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

def generate_token(user_id, email, role):
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')

def get_current_user():
    user_fields = "user_id, full_name, email, phone, role, preferred_language, account_status, created_at"
    # 1. Check Flask session
    if 'user_id' in session:
        try:
            return query_one(f"SELECT {user_fields} FROM users WHERE user_id = %s;", (session['user_id'],))
        except Exception as e:
            print(f"Warning: Failed to fetch current user from session: {e}")
            return None
    
    # 2. Check Authorization Header Bearer token
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            decoded = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            return query_one(f"SELECT {user_fields} FROM users WHERE user_id = %s;", (decoded['user_id'],))
        except Exception as e:
            print(f"Warning: Failed to fetch current user from token: {e}")
            return None
    return None

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"status": "error", "message": "Authentication required. Please log in."}), 401
        return f(user, *args, **kwargs)
    return decorated_function

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.get('role') != 'admin':
            return jsonify({"status": "error", "message": "Administrator privileges required."}), 403
        return f(user, *args, **kwargs)
    return decorated_function

def validate_password_strength(password):
    """
    Validates password requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit (0-9)."
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, "Password must contain at least one special character (!@#$%^&* etc.)."
    return True, ""

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    phone = data.get('phone', '').strip()
    preferred_language = data.get('preferred_language', 'en')

    if not full_name or not email or not password:
        return jsonify({"status": "error", "message": "Full name, email, and password are required."}), 400

    # Validate Confirm Password
    if confirm_password and password != confirm_password:
        return jsonify({"status": "error", "message": "Passwords do not match."}), 400

    # Validate Password Complexity
    is_valid, err_msg = validate_password_strength(password)
    if not is_valid:
        return jsonify({"status": "error", "message": err_msg}), 400

    # Check duplicate email
    try:
        existing = query_one("SELECT user_id FROM users WHERE email = %s;", (email,))
        if existing:
            return jsonify({"status": "error", "message": "An account with this email already exists."}), 409
    except Exception as e:
        err_str = str(e).lower()
        if any(sig in err_str for sig in ("can't connect to mysql", "name or service not known", "2003", "operationalerror", "connection refused")):
            return jsonify({
                "status": "error",
                "message": "Database service is temporarily unavailable. Please verify cloud database status.",
                "detail": str(e)
            }), 503
        raise

    pwd_hash = generate_password_hash(password)
    try:
        user_id = execute_commit("""
            INSERT INTO users (full_name, email, password_hash, phone, preferred_language, role, account_status)
            VALUES (%s, %s, %s, %s, %s, 'user', 'active');
        """, (full_name, email, pwd_hash, phone, preferred_language))
    except Exception as e:
        err_str = str(e).lower()
        if '1062' in err_str or 'duplicate' in err_str or 'unique' in err_str:
            return jsonify({"status": "error", "message": "An account with this email already exists."}), 409
        if any(sig in err_str for sig in ("can't connect to mysql", "name or service not known", "2003", "operationalerror", "connection refused")):
            return jsonify({
                "status": "error",
                "message": "Database service is temporarily unavailable. Please verify cloud database status.",
                "detail": str(e)
            }), 503
        return jsonify({
            "status": "error",
            "message": "Failed to create account due to a database error.",
            "detail": str(e)
        }), 500

    try:
        user_record = query_one("""
            SELECT user_id, full_name, email, phone, role, preferred_language, account_status, created_at 
            FROM users WHERE user_id = %s;
        """, (user_id,))
    except Exception:
        user_record = {
            "user_id": user_id,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "role": "user",
            "preferred_language": preferred_language,
            "account_status": "active"
        }

    token = generate_token(user_id, email, 'user')
    session['user_id'] = user_id
    session['role'] = 'user'

    return jsonify({
        "status": "success",
        "message": f"Welcome to FlyWise, {full_name}! Account created successfully.",
        "token": token,
        "user": user_record
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required."}), 400

    try:
        user = query_one("""
            SELECT user_id, full_name, email, password_hash, phone, role, preferred_language, account_status, created_at 
            FROM users WHERE email = %s;
        """, (email,))
    except Exception as e:
        err_str = str(e).lower()
        if any(sig in err_str for sig in ("can't connect to mysql", "name or service not known", "2003", "operationalerror", "connection refused")):
            return jsonify({
                "status": "error",
                "message": "Database service is temporarily unavailable. Please verify cloud database status.",
                "detail": str(e)
            }), 503
        raise
    
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"status": "error", "message": "Invalid email or password."}), 401

    if user['account_status'] != 'active':
        return jsonify({"status": "error", "message": "This account is suspended or deactivated."}), 403

    token = generate_token(user['user_id'], user['email'], user['role'])
    session['user_id'] = user['user_id']
    session['role'] = user['role']

    # Remove password_hash before returning
    user.pop('password_hash', None)

    return jsonify({
        "status": "success",
        "message": f"Welcome back, {user['full_name']}!",
        "token": token,
        "user": user
    })

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully."})

@auth_bp.route('/me', methods=['GET'])
def me():
    user = get_current_user()
    if not user:
        return jsonify({"status": "unauthenticated", "user": None}), 200
    return jsonify({"status": "authenticated", "user": user})

@auth_bp.route('/preferences', methods=['GET'])
@login_required
def get_preferences(user):
    prefs = query_all("SELECT preference_type, preference_value FROM user_preferences WHERE user_id = %s;", (user['user_id'],))
    pref_dict = {p['preference_type']: p['preference_value'] for p in prefs}
    reqs = query_all("SELECT requirement_type, requirement_details FROM user_travel_requirements WHERE user_id = %s;", (user['user_id'],))
    return jsonify({
        "status": "success",
        "preferences": pref_dict,
        "travel_requirements": reqs
    })

@auth_bp.route('/preferences', methods=['PUT'])
@login_required
def update_preferences(user):
    data = request.get_json() or {}
    user_id = user['user_id']

    for k, v in data.items():
        existing = query_one("SELECT preference_id FROM user_preferences WHERE user_id = %s AND preference_type = %s;", (user_id, k))
        if existing:
            execute_commit("UPDATE user_preferences SET preference_value = %s WHERE preference_id = %s;", (str(v), existing['preference_id']))
        else:
            execute_commit("INSERT INTO user_preferences (user_id, preference_type, preference_value) VALUES (%s, %s, %s);", (user_id, k, str(v)))

    return jsonify({"status": "success", "message": "Travel preferences updated successfully."})
