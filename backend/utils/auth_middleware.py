# ============================================================
# utils/auth_middleware.py — JWT Authentication Middleware
# Generates and validates JSON Web Tokens for API security
# ============================================================

import jwt
import datetime
from functools import wraps
from flask import request, jsonify
from config import SECRET_KEY


def generate_token(user_id, role, name=""):
    """
    Generate a JWT token for an authenticated user.

    Args:
        user_id (str): The student_id or teacher_id.
        role (str): 'student' or 'teacher'.
        name (str): The user's display name.

    Returns:
        str: Encoded JWT token string.
    """
    payload = {
        "user_id": user_id,
        "role": role,
        "name": name,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token):
    """
    Decode and validate a JWT token.

    Args:
        token (str): The JWT token string.

    Returns:
        dict: Decoded payload if valid.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is invalid.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


def token_required(f):
    """
    Decorator for Flask routes that require JWT authentication.
    Extracts the token from the Authorization header (Bearer <token>)
    and injects `current_user` dict into the route kwargs.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

        if not token:
            return jsonify({
                "success": False,
                "message": "Authentication token is missing. Please log in."
            }), 401

        try:
            payload = decode_token(token)
            current_user = {
                "user_id": payload.get("user_id"),
                "role": payload.get("role"),
                "name": payload.get("name", ""),
            }
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "message": "Token has expired. Please log in again."
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "message": "Invalid token. Please log in again."
            }), 401

        # Inject current_user into the route function
        kwargs["current_user"] = current_user
        return f(*args, **kwargs)

    return decorated
