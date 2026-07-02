"""
Authentication Module
=====================

JWT-based authentication for the PDF ChatBot API.

Provides:
    - User registration (signup)
    - User login with JWT token generation
    - Current user profile endpoint
    - jwt_required decorator for protecting routes

The auth routes are registered as a Flask Blueprint so they
can be cleanly plugged into the main app.

Usage:
    from backend.auth import auth_bp, jwt_required, get_current_user_id

    # Register in app.py:
    app.register_blueprint(auth_bp)

    # Protect a route:
    @app.route("/api/protected")
    @jwt_required
    def protected():
        user_id = get_current_user_id()
        return jsonify({"user_id": user_id})
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from functools import wraps

import jwt
from flask import Blueprint, request, jsonify, g
import psycopg2.errors

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import settings
from backend.models import UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

# Flask Blueprint for auth routes
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ----------------------------------------------------------------
# JWT Helpers
# ----------------------------------------------------------------
def _generate_token(user_id: str) -> str:
    """
    Generate a JWT token for a user.

    The token contains:
        - sub: user ID
        - iat: issued at timestamp
        - exp: expiration timestamp

    Args:
        user_id: The user's ID as a string.

    Returns:
        str: Encoded JWT token.
    """
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def _decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string.

    Returns:
        dict: Decoded payload.

    Raises:
        jwt.ExpiredSignatureError: If token has expired.
        jwt.InvalidTokenError: If token is invalid.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])


# ----------------------------------------------------------------
# Auth Decorator
# ----------------------------------------------------------------
def jwt_required(f):
    """
    Decorator to protect Flask routes with JWT authentication.

    Expects the Authorization header: "Bearer <token>"
    Sets g.current_user_id for the decorated function.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid authorization header"}), 401

        token = auth_header.split(" ")[1]

        try:
            payload = _decode_token(token)
            g.current_user_id = payload["sub"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired. Please login again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token. Please login again."}), 401

        return f(*args, **kwargs)

    return decorated


def get_current_user_id() -> str:
    """
    Get the current authenticated user's ID from Flask's g object.

    Must be called inside a @jwt_required decorated route.

    Returns:
        str: The current user's ID as a string.
    """
    return g.current_user_id


# ----------------------------------------------------------------
# Auth Routes
# ----------------------------------------------------------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    """
    Register a new user.

    Expects JSON body:
        {
            "name": "Prashant",
            "email": "prashant@example.com",
            "password": "securepassword123"
        }

    Returns:
        JSON with user info and JWT token, or error message.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    # Validation
    if not name or len(name) < 2:
        return jsonify({"error": "Name must be at least 2 characters"}), 400

    if not email or "@" not in email:
        return jsonify({"error": "Valid email is required"}), 400

    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    try:
        user_id = UserModel.create(name, email, password)
        token = _generate_token(user_id)

        logger.info(f"New user registered: {email}")

        return jsonify({
            "message": "Account created successfully!",
            "token": token,
            "user": {
                "id": user_id,
                "name": name,
                "email": email.lower(),
            },
        }), 201

    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": "An account with this email already exists"}), 409

    except Exception as e:
        logger.error(f"Signup failed: {e}")
        return jsonify({"error": "Registration failed. Please try again."}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate a user and return a JWT token.

    Expects JSON body:
        {
            "email": "prashant@example.com",
            "password": "securepassword123"
        }

    Returns:
        JSON with user info and JWT token, or error message.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Find user by email
    user = UserModel.find_by_email(email)

    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    # Verify password
    if not UserModel.verify_password(password, user["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    user_id = str(user["id"])
    token = _generate_token(user_id)

    logger.info(f"User logged in: {email}")

    return jsonify({
        "message": "Login successful!",
        "token": token,
        "user": {
            "id": user_id,
            "name": user["name"],
            "email": user["email"],
        },
    })


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def get_profile():
    """
    Get the current authenticated user's profile.

    Requires Authorization header: "Bearer <token>"

    Returns:
        JSON with user profile data.
    """
    user_id = get_current_user_id()
    user = UserModel.find_by_id(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user": {
            "id": str(user["id"]),
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"].isoformat(),
        }
    })
