"""
migrate_plagiarism.py — Add plagiarism columns to the submissions table.
Run once to add:
  - plagiarism_score (REAL)
  - plagiarism_flag (BOOLEAN)
  - plagiarism_matches (TEXT) — JSON string of matched submission IDs
  - extracted_text (TEXT) — cached extracted text for future comparisons
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from db import get_db_connection

def migrate():
    conn = get_db_connection()
    cur = conn.cursor()

    columns = [
        ("plagiarism_score",   "REAL DEFAULT NULL"),
        ("plagiarism_flag",    "BOOLEAN DEFAULT NULL"),
        ("plagiarism_matches", "TEXT DEFAULT NULL"),
        ("extracted_text",     "TEXT DEFAULT NULL"),
    ]

    for col_name, col_type in columns:
        try:
            cur.execute(f"ALTER TABLE submissions ADD COLUMN {col_name} {col_type}")
            conn.commit()
            print(f"[OK] Added column: {col_name}")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print(f"[SKIP] Column '{col_name}' already exists.")
            else:
                print(f"[ERROR] Adding '{col_name}': {e}")

    cur.close()
    conn.close()
    print("\n[DONE] Migration complete.")

if __name__ == "__main__":
    migrate()
