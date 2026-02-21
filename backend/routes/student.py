# ============================================================
# routes/student.py — Student dashboard and profile APIs
# No "status" column in DB; status is computed from submission_id/marks.
# ============================================================

from flask import Blueprint, request, jsonify
import psycopg2.extras
from db import get_db_connection

student_bp = Blueprint("student", __name__)


def _row_to_assignment(r):
    """Convert DB row (dict) to a consistent assignment object for frontend."""
    return {
        "id": r.get("assignment_id"),
        "title": r.get("title") or "",
        "subject": r.get("subject") or "",
        "deadline": (r.get("deadline") or "").__str__() if r.get("deadline") else "",
        "submission_status": r.get("submission_status"),
        "submitted_at": (r.get("submitted_at") or "").__str__() if r.get("submitted_at") else None,
    }


@student_bp.route("/student/<student_id>/info", methods=["GET"])
def get_student_info(student_id):
    """GET /student/<student_id>/info — Returns current student name and id for navbar/profile."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT student_id, name, email
            FROM students
            WHERE student_id = %s
            """,
            (student_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    if not row:
        return jsonify({"success": False, "message": "Student not found."}), 404

    name = (row.get("name") or student_id)
    return jsonify({
        "success": True,
        "student_id": row.get("student_id"),
        "name": name,
        "email": row.get("email") or "",
    }), 200


@student_bp.route("/student/<student_id>/profile", methods=["GET"])
def get_student_profile(student_id):
    """GET /student/<student_id>/profile — Returns student_id, name, email for profile page."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT student_id, name, email
            FROM students
            WHERE student_id = %s
            """,
            (student_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    if not row:
        return jsonify({"success": False, "message": "Student not found."}), 404
    return jsonify({
        "success": True,
        "student_id": row.get("student_id"),
        "name": row.get("name") or "",
        "email": row.get("email") or "",
    }), 200


@student_bp.route("/student/<student_id>/dashboard", methods=["GET"])
def get_student_dashboard(student_id):
    """
    GET /student/<student_id>/dashboard
    Counts and assignment list; status computed via SQL (no status column in DB).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Single query for counts (no status column)
        cur.execute(
            """
            SELECT
                COUNT(a.assignment_id) AS total,
                COUNT(s.submission_id) AS submitted,
                COUNT(CASE WHEN s.marks IS NOT NULL THEN 1 END) AS evaluated,
                COUNT(a.assignment_id) - COUNT(s.submission_id) AS pending
            FROM assignments a
            LEFT JOIN submissions s
                ON a.assignment_id = s.assignment_id AND s.student_id = %s
            """,
            (student_id,),
        )
        counts = cur.fetchone() or {}
        total_assignments = int(counts.get("total") or 0)
        submitted_count = int(counts.get("submitted") or 0)
        evaluated_count = int(counts.get("evaluated") or 0)
        pending = int(counts.get("pending") or 0)

        # Assignments with computed status (no status column)
        cur.execute(
            """
            SELECT
                a.assignment_id,
                a.title,
                a.deadline::text AS deadline,
                s.marks,
                s.submitted_at,
                CASE
                    WHEN s.submission_id IS NULL THEN 'pending'
                    WHEN s.marks IS NULL THEN 'submitted'
                    ELSE 'evaluated'
                END AS submission_status
            FROM assignments a
            LEFT JOIN submissions s
                ON a.assignment_id = s.assignment_id AND s.student_id = %s
            ORDER BY a.deadline ASC
            LIMIT 50
            """,
            (student_id,),
        )
        rows = cur.fetchall() or []
        cur.close()
        conn.close()

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    assignments = [_row_to_assignment(dict(r)) for r in rows]
    return jsonify({
        "success": True,
        "student_id": student_id,
        "total_assignments": total_assignments,
        "submitted_count": submitted_count,
        "evaluated_count": evaluated_count,
        "pending_count": pending,
        "assignments": assignments,
    }), 200


@student_bp.route("/student/<student_id>/assignments", methods=["GET"])
def get_student_assignments(student_id):
    """GET /student/<student_id>/assignments — Full list; status computed (no status column)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT
                a.assignment_id,
                a.title,
                a.deadline::text AS deadline,
                s.submitted_at,
                CASE
                    WHEN s.submission_id IS NULL THEN 'pending'
                    WHEN s.marks IS NULL THEN 'submitted'
                    ELSE 'evaluated'
                END AS submission_status
            FROM assignments a
            LEFT JOIN submissions s
                ON a.assignment_id = s.assignment_id AND s.student_id = %s
            ORDER BY a.deadline ASC
            """,
            (student_id,),
        )
        rows = cur.fetchall() or []
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    assignments = [_row_to_assignment(dict(r)) for r in rows]
    return jsonify({"success": True, "assignments": assignments}), 200


@student_bp.route("/student/<student_id>/results", methods=["GET"])
def get_student_results(student_id):
    """GET /student/<student_id>/results — Evaluated submissions (marks IS NOT NULL)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT s.submission_id, s.assignment_id, s.submitted_at, s.marks, s.feedback,
                   a.title AS assignment_title
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            WHERE s.student_id = %s AND s.marks IS NOT NULL
            ORDER BY s.submitted_at DESC NULLS LAST
            """,
            (student_id,),
        )
        rows = cur.fetchall() or []
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    results = []
    for r in (dict(x) for x in rows):
        results.append({
            "submission_id": r.get("submission_id"),
            "assignment_id": r.get("assignment_id"),
            "assignment_title": r.get("assignment_title") or "",
            "subject": r.get("subject") or "",
            "submitted_at": (r.get("submitted_at") or "").__str__() if r.get("submitted_at") else "",
            "marks": r.get("marks"),
            "score": r.get("score"),
            "feedback": r.get("feedback") or "",
        })
    return jsonify({"success": True, "results": results}), 200


@student_bp.route("/student/<student_id>/submissions", methods=["POST"])
def create_submission(student_id):
    """POST /student/<student_id>/submissions — Create a submission. file_url required (e.g. filename or URL)."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No JSON body."}), 400
    assignment_id = data.get("assignment_id")
    file_url = (data.get("file_url") or "").strip()
    if not assignment_id:
        return jsonify({"success": False, "message": "assignment_id is required."}), 400
    if not file_url:
        return jsonify({"success": False, "message": "File upload is required (file_url)."}), 400
    try:
        assignment_id = int(assignment_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid assignment_id."}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO submissions (assignment_id, student_id, file_url)
            VALUES (%s, %s, %s)
            RETURNING submission_id
            """,
            (assignment_id, student_id, file_url),
        )
        row = cur.fetchone()
        conn.commit()
        sid = row[0] if row else None
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    return jsonify({
        "success": True,
        "message": "Submission recorded.",
        "submission_id": sid,
    }), 201


@student_bp.route("/assignment/<int:assignment_id>", methods=["GET"])
def get_assignment_by_id(assignment_id):
    """GET /assignment/<id> — Single assignment details for submission page."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT a.assignment_id, a.title, a.teacher_id,
                   a.deadline::text AS deadline, a.description
            FROM assignments a
            WHERE a.assignment_id = %s
            """,
            (assignment_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    if not row:
        return jsonify({"success": False, "message": "Assignment not found."}), 404
    r = dict(row)
    return jsonify({
        "success": True,
        "assignment": {
            "id": r.get("assignment_id"),
            "title": r.get("title") or "",
            "subject": r.get("subject") or "",  # empty if column not in table
            "deadline": r.get("deadline") or "",
            "description": r.get("description") or "",
        },
    }), 200
