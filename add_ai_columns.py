# add_ai_columns.py — Add ai_probability column to submissions table (idempotent)
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from db import get_db_connection

try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS ai_probability REAL")
    conn.commit()
    print("✅ Column 'ai_probability' added (or already exists) in submissions table.")
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
