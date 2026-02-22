# ============================================================
# routes/teacher.py — Teacher dashboard and profile APIs
# Expects DB: teachers, assignments, submissions, students
# ============================================================

from flask import Blueprint, request, jsonify, current_app
import psycopg2.extras
from db import get_db_connection
import time
from werkzeug.utils import secure_filename
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

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
    """POST /teacher/<teacher_id>/assignments — Create a new assignment with Supabase Storage upload."""
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    deadline = request.form.get("deadline")
    max_marks = request.form.get("max_marks")
    subject = request.form.get("subject", "").strip()

    if not title:
        return jsonify({"success": False, "message": "Assignment title is required."}), 400
    if not deadline:
        return jsonify({"success": False, "message": "Deadline is required."}), 400
    if max_marks is None or max_marks == "":
        return jsonify({"success": False, "message": "Maximum marks is required."}), 400

    file_url = None
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{filename}"
            
            try:
                # Initialize Supabase client
                supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                
                # Read file content
                file_content = file.read()
                
                # Upload to Supabase 'assignments' bucket
                res = supabase.storage.from_('assignments').upload(
                    path=filename,
                    file=file_content,
                    file_options={"content-type": file.content_type}
                )
                
                # Get Public URL
                public_url_res = supabase.storage.from_('assignments').get_public_url(filename)
                file_url = public_url_res
                
            except Exception as e:
                return jsonify({"success": False, "message": f"Storage upload failed: {str(e)}"}), 500

    try:
        max_marks = int(max_marks)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Maximum marks must be a number."}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO assignments (title, description, teacher_id, deadline, max_marks, file_url, subject)
            VALUES (%s, %s, %s, %s::timestamp, %s, %s, %s)
            RETURNING assignment_id
            """,
            (title, description or None, teacher_id, deadline, max_marks, file_url, subject or None),
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
        "message": "Assignment created and uploaded to Supabase.",
        "assignment_id": aid,
        "file_url": file_url
    }), 201


@teacher_bp.route("/teacher/<teacher_id>/dashboard", methods=["GET"])
def get_teacher_dashboard(teacher_id):
    """
    GET /teacher/<teacher_id>/dashboard
    Returns: total_assignments, submissions_received, pending_evaluation, evaluated_count, recent_submissions, and assignments list.
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
        recent_rows = cur.fetchall() or []

        # Get all assignments for management
        cur.execute(
            """
            SELECT assignment_id, title, subject, deadline, file_url, description, max_marks
            FROM assignments
            WHERE teacher_id = %s
            ORDER BY created_at DESC
            """,
            (teacher_id,),
        )
        assignment_rows = cur.fetchall() or []
        
        cur.close()
        conn.close()

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    submissions = [_row_to_submission(dict(r)) for r in recent_rows]
    assignments = []
    for a in assignment_rows:
        assignments.append({
            "assignment_id": a["assignment_id"],
            "title": a["title"] or "",
            "subject": a["subject"] or "",
            "deadline": str(a["deadline"]) if a["deadline"] else "",
            "file_url": a["file_url"] or "",
            "description": a["description"] or "",
            "max_marks": a["max_marks"]
        })

    return jsonify({
        "success": True,
        "teacher_id": teacher_id,
        "total_assignments": total_assignments,
        "submissions_received": submissions_received,
        "pending_evaluation": pending_evaluation,
        "evaluated_count": evaluated_count,
        "recent_submissions": submissions,
        "assignments": assignments
    }), 200


@teacher_bp.route("/teacher/<teacher_id>/assignment/<int:assignment_id>", methods=["PUT"])
def update_assignment(teacher_id, assignment_id):
    """PUT /teacher/<teacher_id>/assignment/<id> — Update an assignment."""
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    deadline = request.form.get("deadline")
    max_marks = request.form.get("max_marks")
    subject = request.form.get("subject", "").strip()

    if not title:
        return jsonify({"success": False, "message": "Assignment title is required."}), 400

    new_file_url = None
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{filename}"
            try:
                supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                file_content = file.read()
                supabase.storage.from_('assignments').upload(
                    path=filename,
                    file=file_content,
                    file_options={"content-type": file.content_type}
                )
                new_file_url = supabase.storage.from_('assignments').get_public_url(filename)
            except Exception as e:
                return jsonify({"success": False, "message": f"Storage upload failed: {str(e)}"}), 500

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # If new file, consider deleting old one (optional but cleaner)
        if new_file_url:
            cur.execute("SELECT file_url FROM assignments WHERE assignment_id = %s", (assignment_id,))
            old = cur.fetchone()
            if old and old['file_url']:
                try:
                    # Extract path from URL (Supabase URL format usually ends with filename)
                    # For simplicity, we stick to the database update first.
                    pass
                except: pass

        update_query = """
            UPDATE assignments
            SET title = %s, description = %s, deadline = %s::timestamp, max_marks = %s, subject = %s
        """
        params = [title, description or None, deadline, max_marks, subject or None]
        
        if new_file_url:
            update_query += ", file_url = %s"
            params.append(new_file_url)
            
        update_query += " WHERE assignment_id = %s AND teacher_id = %s"
        params.extend([assignment_id, teacher_id])
        
        cur.execute(update_query, tuple(params))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    return jsonify({"success": True, "message": "Assignment updated successfully."}), 200


@teacher_bp.route("/teacher/<teacher_id>/assignment/<int:assignment_id>", methods=["DELETE"])
def delete_assignment(teacher_id, assignment_id):
    """DELETE /teacher/<teacher_id>/assignment/<id> — Delete assignment and its files."""

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 1. Get assignment file and submission files
        cur.execute("SELECT file_url FROM assignments WHERE assignment_id = %s", (assignment_id,))
        a_row = cur.fetchone()
        
        cur.execute("SELECT file_url FROM submissions WHERE assignment_id = %s", (assignment_id,))
        s_rows = cur.fetchall()

        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # 2. Delete assignment file from Supabase
        if a_row and a_row['file_url']:
            try:
                fname = a_row['file_url'].split("/")[-1]
                supabase.storage.from_('assignments').remove([fname])
            except: pass

        # 3. Delete submission files from Supabase
        for s in s_rows:
            if s['file_url']:
                try:
                    fname = s['file_url'].split("/")[-1]
                    supabase.storage.from_('submissions').remove([fname])
                except: pass

        # 4. Delete from DB (submissions first then assignment)
        cur.execute("DELETE FROM submissions WHERE assignment_id = %s", (assignment_id,))
        cur.execute("DELETE FROM assignments WHERE assignment_id = %s AND teacher_id = %s", (assignment_id, teacher_id))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    return jsonify({"success": True, "message": "Assignment and associated data deleted."}), 200


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
                   a.deadline::text AS assignment_deadline, a.max_marks, s.file_url,
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
            "max_marks": r.get("max_marks"),
            "status": r.get("status") or "submitted",
            "submitted_at": (r.get("submitted_at") or "").__str__(),
            "deadline": (r.get("assignment_deadline") or "").__str__(),
            "file_url": r.get("file_url") or "",
        },
    }), 200


@teacher_bp.route("/teacher/submission/<int:submission_id>/evaluate", methods=["POST"])
def evaluate_submission(submission_id):
    """POST /teacher/submission/<id>/evaluate — Save marks and feedback for a submission."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No JSON body."}), 400

    marks = data.get("marks")
    feedback = (data.get("feedback") or "").strip()

    if marks is None or marks == "":
        return jsonify({"success": False, "message": "Marks are required."}), 400

    try:
        marks = float(marks)
        if marks < 0:
            return jsonify({"success": False, "message": "Marks cannot be negative."}), 400
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Marks must be a number."}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE submissions
            SET marks = %s, feedback = %s
            WHERE submission_id = %s
            RETURNING submission_id
            """,
            (marks, feedback or None, submission_id),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"success": False, "message": "Submission not found."}), 404

        return jsonify({
            "success": True,
            "message": "Evaluation submitted successfully.",
            "submission_id": submission_id
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
