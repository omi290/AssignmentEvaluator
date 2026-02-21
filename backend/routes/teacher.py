# ============================================================
# routes/teacher.py — Teacher dashboard and profile APIs
# Expects DB: teachers, assignments, submissions, students
# ============================================================

from flask import Blueprint, request, jsonify
import psycopg2.extras
from db import get_db_connection

teacher_bp = Blueprint("teacher", __name__)


def _row_to_submission(r):
    """Convert DB row to a consistent object for frontend. status is computed in SQL."""
    return {
        "submission_id": r.get("submission_id"),
        "student_id": r.get("student_id"),
        "student_name": r.get("student_name") or r.get("student_id"),
        "assignment_id": r.get("assignment_id"),
        "assignment_title": r.get("assignment_title") or "",
        "submitted_at": (r.get("submitted_at") or "").__str__() if r.get("submitted_at") else "",
        "status": r.get("status") or "submitted",
    }


@teacher_bp.route("/teacher/<teacher_id>/info", methods=["GET"])
def get_teacher_info(teacher_id):
    """GET /teacher/<teacher_id>/info — Returns current teacher name and id for navbar."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT teacher_id, name, email
            FROM teachers
            WHERE teacher_id = %s
            """,
            (teacher_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    if not row:
        return jsonify({"success": False, "message": "Teacher not found."}), 404

    name = row.get("name") or teacher_id
    return jsonify({
        "success": True,
        "teacher_id": row.get("teacher_id"),
        "name": name,
        "email": row.get("email") or "",
    }), 200


@teacher_bp.route("/teacher/<teacher_id>/profile", methods=["GET"])
def get_teacher_profile(teacher_id):
    """GET /teacher/<teacher_id>/profile — Returns teacher_id, name, email for profile page."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT teacher_id, name, email
            FROM teachers
            WHERE teacher_id = %s
            """,
            (teacher_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    if not row:
        return jsonify({"success": False, "message": "Teacher not found."}), 404
    return jsonify({
        "success": True,
        "teacher_id": row.get("teacher_id"),
        "name": row.get("name") or "",
        "email": row.get("email") or "",
    }), 200


@teacher_bp.route("/teacher/<teacher_id>/assignments", methods=["POST"])
def create_assignment(teacher_id):
    """POST /teacher/<teacher_id>/assignments — Create a new assignment. Description optional, file_url optional."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No JSON body."}), 400
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    deadline = data.get("deadline")
    max_marks = data.get("max_marks")
    file_url = (data.get("file_url") or "").strip() or None
    if not title:
        return jsonify({"success": False, "message": "Assignment title is required."}), 400
    if not deadline:
        return jsonify({"success": False, "message": "Deadline is required."}), 400
    if max_marks is None or max_marks == "":
        return jsonify({"success": False, "message": "Maximum marks is required."}), 400
    try:
        max_marks = int(max_marks)
        if max_marks < 1:
            raise ValueError("max_marks must be >= 1")
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Maximum marks must be a positive number."}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Omit subject - add it if your assignments table has a subject column
        cur.execute(
            """
            INSERT INTO assignments (title, description, teacher_id, deadline, max_marks, file_url)
            VALUES (%s, %s, %s, %s::timestamp, %s, %s)
            RETURNING assignment_id
            """,
            (title, description or None, teacher_id, deadline, max_marks, file_url),
        )
        row = cur.fetchone()
        conn.commit()
        aid = row[0] if row else None
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    return jsonify({
        "success": True,
        "message": "Assignment created.",
        "assignment_id": aid,
    }), 201


@teacher_bp.route("/teacher/<teacher_id>/dashboard", methods=["GET"])
def get_teacher_dashboard(teacher_id):
    """
    GET /teacher/<teacher_id>/dashboard
    Returns: total_assignments, submissions_received, pending_evaluation, evaluated_count, recent_submissions.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Total assignments created by this teacher
        cur.execute(
            "SELECT COUNT(*) AS total FROM assignments WHERE teacher_id = %s",
            (teacher_id,),
        )
        total_assignments = (cur.fetchone() or {}).get("total") or 0

        # Submissions received (for this teacher's assignments)
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            WHERE a.teacher_id = %s
            """,
            (teacher_id,),
        )
        submissions_received = (cur.fetchone() or {}).get("cnt") or 0

        # Pending evaluation (submitted but marks not yet set)
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            WHERE a.teacher_id = %s AND s.marks IS NULL
            """,
            (teacher_id,),
        )
        pending_evaluation = (cur.fetchone() or {}).get("cnt") or 0

        # Evaluated count (no status column)
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            WHERE a.teacher_id = %s AND s.marks IS NOT NULL
            """,
            (teacher_id,),
        )
        evaluated_count = (cur.fetchone() or {}).get("cnt") or 0

        # Recent submissions; status computed (no status column)
        cur.execute(
            """
            SELECT s.submission_id, s.student_id, s.assignment_id, s.submitted_at,
                   st.name AS student_name, a.title AS assignment_title,
                   CASE WHEN s.marks IS NULL THEN 'submitted' ELSE 'evaluated' END AS status
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            LEFT JOIN students st ON st.student_id = s.student_id
            WHERE a.teacher_id = %s
            ORDER BY s.submitted_at DESC NULLS LAST
            LIMIT 50
            """,
            (teacher_id,),
        )
        rows = cur.fetchall() or []
        cur.close()
        conn.close()

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    submissions = [_row_to_submission(dict(r)) for r in rows]
    return jsonify({
        "success": True,
        "teacher_id": teacher_id,
        "total_assignments": total_assignments,
        "submissions_received": submissions_received,
        "pending_evaluation": pending_evaluation,
        "evaluated_count": evaluated_count,
        "recent_submissions": submissions,
    }), 200


@teacher_bp.route("/teacher/<teacher_id>/submissions", methods=["GET"])
def get_teacher_submissions(teacher_id):
    """GET /teacher/<teacher_id>/submissions — Full list of submissions for submissions page."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT s.submission_id, s.student_id, s.assignment_id, s.submitted_at,
                   st.name AS student_name, a.title AS assignment_title,
                   CASE WHEN s.marks IS NULL THEN 'submitted' ELSE 'evaluated' END AS status
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            LEFT JOIN students st ON st.student_id = s.student_id
            WHERE a.teacher_id = %s
            ORDER BY s.submitted_at DESC NULLS LAST
            """,
            (teacher_id,),
        )
        rows = cur.fetchall() or []
        cur.execute(
            """
            SELECT assignment_id, title FROM assignments WHERE teacher_id = %s ORDER BY title
            """,
            (teacher_id,),
        )
        assign_rows = cur.fetchall() or []
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    submissions = [_row_to_submission(dict(r)) for r in rows]
    assignments = [{"id": dict(a).get("assignment_id"), "title": dict(a).get("title") or ""} for a in assign_rows]
    return jsonify({
        "success": True,
        "submissions": submissions,
        "assignments": assignments,
    }), 200


@teacher_bp.route("/submission/<int:submission_id>", methods=["GET"])
def get_submission_by_id(submission_id):
    """GET /submission/<id> — Single submission details for evaluate page."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT s.submission_id, s.student_id, s.assignment_id, s.submitted_at,
                   st.name AS student_name, a.title AS assignment_title,
                   a.deadline::text AS assignment_deadline, s.file_url,
                   CASE WHEN s.marks IS NULL THEN 'submitted' ELSE 'evaluated' END AS status
            FROM submissions s
            JOIN assignments a ON a.assignment_id = s.assignment_id
            LEFT JOIN students st ON st.student_id = s.student_id
            WHERE s.submission_id = %s
            """,
            (submission_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    if not row:
        return jsonify({"success": False, "message": "Submission not found."}), 404
    r = dict(row)
    return jsonify({
        "success": True,
        "submission": {
            "id": r.get("submission_id"),
            "student_id": r.get("student_id"),
            "student_name": r.get("student_name") or r.get("student_id"),
            "assignment_id": r.get("assignment_id"),
            "assignment_title": r.get("assignment_title") or "",
            "status": r.get("status") or "submitted",
            "submitted_at": (r.get("submitted_at") or "").__str__(),
            "deadline": (r.get("assignment_deadline") or "").__str__(),
            "file_url": r.get("file_url") or "",
        },
    }), 200
