# ============================================================
# routes/ai_routes.py — AI Evaluation API (Phase-4)
# Now fetches assignment context for relevance validation
# ============================================================

from flask import Blueprint, jsonify
import psycopg2.extras
from db import get_db_connection
from utils.pdf_parser import extract_text
from ai.evaluator import evaluate_submission

ai_bp = Blueprint("ai", __name__)


def _build_assignment_context(title, description, assignment_file_url):
    """
    Build a combined context string from the assignment's title,
    description, and question paper PDF (if available).
    """
    parts = []

    if title:
        parts.append(f"Assignment Title: {title}")

    if description:
        parts.append(f"Assignment Description / Questions:\n{description}")

    # Try to extract text from the assignment's own PDF (the question paper)
    if assignment_file_url:
        try:
            assignment_text = extract_text(assignment_file_url)
            if assignment_text and assignment_text.strip():
                parts.append(f"Assignment Question Paper Content:\n{assignment_text[:3000]}")
        except Exception as e:
            print(f"[ai_routes.py] Could not extract assignment PDF text: {e}")
            # Non-fatal — we still have title + description

    return "\n\n".join(parts) if parts else ""


@ai_bp.route("/evaluate/<int:submission_id>", methods=["POST"])
def ai_evaluate(submission_id):
    """
    POST /evaluate/<submission_id>

    Flow:
      1. Fetch submission file_url AND assignment context from DB
      2. Extract text from the student's submitted file
      3. Extract text from the assignment's question paper (if exists)
      4. Run AI evaluation with both texts for relevance + scoring
      5. Update submissions table with marks, feedback, ai_probability, relevance
      6. Return evaluation results as JSON
    """
    # --- Step 1: Fetch submission + assignment details ---
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT s.submission_id, s.file_url,
                   a.max_marks,
                   a.title AS assignment_title,
                   a.description AS assignment_description,
                   a.file_url AS assignment_file_url
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
    assignment_title = row.get("assignment_title") or ""
    assignment_description = row.get("assignment_description") or ""
    assignment_file_url = row.get("assignment_file_url") or ""

    if not file_url:
        cur.close()
        conn.close()
        return jsonify({
            "success": False,
            "message": "No file found for this submission."
        }), 400

    # --- Step 2: Extract text from the student's submission ---
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

    # --- Step 3: Build assignment context for relevance check ---
    assignment_context = _build_assignment_context(
        assignment_title, assignment_description, assignment_file_url
    )

    # --- Step 4: Run AI evaluation with context ---
    try:
        result = evaluate_submission(text, max_marks=max_marks, assignment_context=assignment_context)
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
    is_relevant = result.get("is_relevant", True)
    relevance_reason = result.get("relevance_reason", "")
    method = result.get("method", "unknown")

    # --- Step 5: Update the submissions table ---
    try:
        cur.execute(
            """
            UPDATE submissions
            SET marks = %s, feedback = %s, ai_probability = %s,
                is_relevant = %s, relevance_reason = %s
            WHERE submission_id = %s
            RETURNING submission_id
            """,
            (score, feedback, ai_probability, is_relevant, relevance_reason, submission_id),
        )
        updated = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to save results: {e}"}), 500

    if not updated:
        return jsonify({"success": False, "message": "Failed to update submission."}), 500

    # --- Step 6: Return results ---
    return jsonify({
        "success": True,
        "message": "AI evaluation completed successfully.",
        "submission_id": submission_id,
        "evaluation": {
            "score": score,
            "max_marks": max_marks,
            "feedback": feedback,
            "ai_probability": ai_probability,
            "is_relevant": is_relevant,
            "relevance_reason": relevance_reason,
            "method": method,
        },
    }), 200
