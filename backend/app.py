# ============================================================
# app.py — Flask application entry point
# Assignment Evaluator — Phase-2 Backend
# ============================================================

from flask import Flask, jsonify
from flask_cors import CORS
from config import SECRET_KEY

# Import route blueprints
from routes.auth import auth_bp
from routes.student import student_bp
from routes.teacher import teacher_bp

# ── Create Flask app ──────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

# ── Enable CORS so the frontend (HTML/JS) can call this API ──
# Update the origins list if your frontend is hosted elsewhere
CORS(app, resources={r"/*": {"origins": "*"}})

# ── Register Blueprints ───────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(teacher_bp)

# ── Health-check endpoint ─────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    """GET / — confirms the backend is running."""
    return jsonify({
        "status":  "ok",
        "message": "Assignment Evaluator Backend is running.",
        "phase":   "Phase-2"
    }), 200


# ── Run the app ───────────────────────────────────────────────
if __name__ == "__main__":
    # debug=True gives auto-reload during development.
    # Set debug=False before deploying to production.
    app.run(debug=True, host="0.0.0.0", port=5000)
