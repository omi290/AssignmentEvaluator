# ============================================================
# routes/auth.py — Login endpoint
# ============================================================

from flask import Blueprint, request, jsonify
import psycopg2.extras
from db import get_db_connection

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "No JSON body provided."}), 400

    user_id  = data.get("id")
    password = data.get("password")
    role     = data.get("role")

    if not user_id or not password or not role:
        return jsonify({
            "success": False,
            "message": "Missing required fields: id, password, role."
        }), 400

    role = role.lower().strip()
    if role not in ("student", "teacher"):
        return jsonify({
            "success": False,
            "message": "Invalid role."
        }), 400

    if role == "student":
        table = "students"
        id_column = "student_id"
        name_column = "name"  # use full_name if your schema has that instead
    else:
        table = "teachers"
        id_column = "teacher_id"
        name_column = "name"

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Select id and name so we can return them to frontend
        query = f"""
            SELECT {id_column}, {name_column}
            FROM {table}
            WHERE {id_column} = %s AND password = %s
        """
        cur.execute(query, (user_id, password))
        user = cur.fetchone()

        cur.close()
        conn.close()

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Database error: {str(e)}"
        }), 500

    if user:
        # Support both "name" and "full_name" column names
        name = user.get("name") or user.get("full_name") or user_id
        return jsonify({
            "success": True,
            "message": f"Login successful as {role}",
            "role": role,
            "id": user_id,
            "name": name
        }), 200

    return jsonify({
        "success": False,
        "message": "Invalid ID or password."
    }), 401