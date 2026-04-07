# ============================================================
# routes/ai_routes.py — AI Evaluation API (Phase-3)
# New blueprint — does NOT modify any existing routes
# ============================================================

from flask import Blueprint, jsonify
import psycopg2.extras
from db import get_db_connection
from utils.pdf_parser import extract_text
from ai.evaluator import evaluate_submission

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/evaluate/<int:submission_id>", methods=["POST"])
def ai_evaluate(submission_id):
    """
    POST /evaluate/<submission_id>
    
    Flow:
      1. Fetch submission file_url and max_marks from DB
      2. Extract text from the file (PDF or plain text)
      3. Run AI evaluation on the extracted text
      4. Update submissions table with marks, feedback, ai_probability
      5. Return evaluation results as JSON
    """
    # --- Step 1: Fetch submission details ---
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT s.submission_id, s.file_url, a.max_marks
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            WHERE s.submission_id = %s
            """,
            (submission_id,),
        )
        row = cur.fetchone()
    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500

    if not row:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Submission not found."}), 404

    file_url = row.get("file_url") or ""
    max_marks = int(row.get("max_marks") or 100)

    if not file_url:
        cur.close()
        conn.close()
        return jsonify({
            "success": False,
            "message": "No file found for this submission."
        }), 400

    # --- Step 2: Extract text from the file ---
    try:
        text = extract_text(file_url)
    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({
            "success": False,
            "message": f"Text extraction failed: {e}"
        }), 422

    if not text or not text.strip():
        cur.close()
        conn.close()
        return jsonify({
            "success": False,
            "message": "No readable text could be extracted from the submission file."
        }), 422

    # --- Step 3: Run AI evaluation ---
    try:
        result = evaluate_submission(text, max_marks=max_marks)
    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({
            "success": False,
            "message": f"AI evaluation failed: {e}"
        }), 500

    score = result.get("score", 0)
    feedback = result.get("feedback", "")
    ai_probability = result.get("ai_probability", 0)
    method = result.get("method", "unknown")

    # --- Step 4: Update the submissions table ---
    try:
        cur.execute(
            """
            UPDATE submissions
            SET marks = %s, feedback = %s, ai_probability = %s
            WHERE submission_id = %s
            RETURNING submission_id
            """,
            (score, feedback, ai_probability, submission_id),
        )
        updated = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to save results: {e}"}), 500

    if not updated:
        return jsonify({"success": False, "message": "Failed to update submission."}), 500

    # --- Step 5: Return results ---
    return jsonify({
        "success": True,
        "message": "AI evaluation completed successfully.",
        "submission_id": submission_id,
        "evaluation": {
            "score": score,
            "max_marks": max_marks,
            "feedback": feedback,
            "ai_probability": ai_probability,
            "method": method,
        },
    }), 200
