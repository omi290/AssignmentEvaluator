# ============================================================
# routes/student.py — Student dashboard and profile APIs
# No "status" column in DB; status is computed from submission_id/marks.
# ============================================================

from flask import Blueprint, request, jsonify
import psycopg2.extras
from db import get_db_connection
import time
from werkzeug.utils import secure_filename
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

student_bp = Blueprint("student", __name__)


def _row_to_assignment(r):
    """Convert DB row (dict) to a consistent assignment object for frontend."""
    return {
        "id": r.get("assignment_id"),
        "title": r.get("title") or "",
        "subject": r.get("subject") or "",
        "description": r.get("description") or "",
        "deadline": (r.get("deadline") or "").__str__() if r.get("deadline") else "",
        "submission_id": r.get("submission_id"),
        "submission_status": r.get("submission_status"),
        "max_marks": r.get("max_marks"),
        "file_url": r.get("file_url") or "",
        "submitted_at": (r.get("submitted_at") or "").__str__() if r.get("submitted_at") else "",
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
                a.subject,
                a.deadline::text AS deadline,
                a.max_marks,
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
                a.subject,
                a.description,
                a.max_marks,
                a.deadline::text AS deadline,
                s.submission_id,
                s.file_url,
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
                   s.file_url AS submission_file_url, s.student_comments,
                   a.title AS assignment_title, a.max_marks, a.file_url AS assignment_file_url
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
            "max_marks": r.get("max_marks"),
            "submission_file_url": r.get("submission_file_url") or "",
            "assignment_file_url": r.get("assignment_file_url") or "",
            "student_comments": r.get("student_comments") or "",
            "score": r.get("score"),
            "feedback": r.get("feedback") or "",
        })
    return jsonify({"success": True, "results": results}), 200


@student_bp.route("/student/<student_id>/submissions", methods=["POST"])
def create_submission(student_id):
    """POST /student/<student_id>/submissions — Create a submission with Supabase Storage upload."""
    from flask import current_app
    from werkzeug.utils import secure_filename
    from supabase import create_client, Client
    from config import SUPABASE_URL, SUPABASE_KEY
    import time

    assignment_id = request.form.get("assignment_id")
    comments = request.form.get("comments", "").strip()
    if not assignment_id:
        return jsonify({"success": False, "message": "assignment_id is required."}), 400

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
                
                # Upload to Supabase 'submissions' bucket
                res = supabase.storage.from_('submissions').upload(
                    path=filename,
                    file=file_content,
                    file_options={"content-type": file.content_type}
                )
                
                # Get Public URL
                public_url_res = supabase.storage.from_('submissions').get_public_url(filename)
                file_url = public_url_res
                
            except Exception as e:
                return jsonify({"success": False, "message": f"Storage upload failed: {str(e)}"}), 500
    
    if not file_url:
        return jsonify({"success": False, "message": "File upload is required."}), 400

    try:
        assignment_id = int(assignment_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid assignment_id."}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO submissions (assignment_id, student_id, file_url, student_comments)
            VALUES (%s, %s, %s, %s)
            RETURNING submission_id
            """,
            (assignment_id, student_id, file_url, comments or None),
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
        "message": "Submission uploaded to Supabase.",
        "submission_id": sid,
        "file_url": file_url
    }), 201


@student_bp.route("/assignment/<int:assignment_id>", methods=["GET"])
def get_assignment_by_id(assignment_id):
    """GET /assignment/<id> — Single assignment details for submission page."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT a.assignment_id, a.title, a.teacher_id, a.subject,
                   a.deadline::text AS deadline, a.description, a.file_url
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
            "subject": r.get("subject") or "",
            "deadline": r.get("deadline") or "",
            "description": r.get("description") or "",
            "file_url": r.get("file_url") or "",
        },
    }), 200


@student_bp.route("/student/<student_id>/submission/<int:submission_id>", methods=["PUT"])
def update_submission(student_id, submission_id):
    """PUT /student/<student_id>/submission/<id> — Replace submission file."""

    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "Empty filename."}), 400

    filename = secure_filename(file.filename)
    filename = f"{int(time.time())}_{filename}"

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        file_content = file.read()
        
        # Upload new file
        supabase.storage.from_('submissions').upload(
            path=filename,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
        new_file_url = supabase.storage.from_('submissions').get_public_url(filename)

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT file_url FROM submissions WHERE submission_id = %s", (submission_id,))
        old = cur.fetchone()
        
        cur.execute(
            """
            UPDATE submissions
            SET file_url = %s, submitted_at = CURRENT_TIMESTAMP
            WHERE submission_id = %s AND student_id = %s
            """,
            (new_file_url, submission_id, student_id)
        )
        conn.commit()
        
        if old and old['file_url']:
            try:
                old_fname = old['file_url'].split("/")[-1]
                supabase.storage.from_('submissions').remove([old_fname])
            except: pass

        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    return jsonify({"success": True, "message": "Submission updated successfully.", "file_url": new_file_url}), 200


@student_bp.route("/student/<student_id>/submission/<int:submission_id>", methods=["DELETE"])
def delete_submission(student_id, submission_id):
    """DELETE /student/<student_id>/submission/<id> — Delete submission and its file."""

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT file_url FROM submissions WHERE submission_id = %s AND student_id = %s", (submission_id, student_id))
        row = cur.fetchone()
        
        if not row:
            return jsonify({"success": False, "message": "Submission not found."}), 404

        if row['file_url']:
            try:
                supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                fname = row['file_url'].split("/")[-1]
                supabase.storage.from_('submissions').remove([fname])
            except: pass

        cur.execute("DELETE FROM submissions WHERE submission_id = %s", (submission_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    return jsonify({"success": True, "message": "Submission deleted."}), 200
