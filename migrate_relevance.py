# migrate_relevance.py — Add content relevance columns to submissions table (idempotent)
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from db import get_db_connection

try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS is_relevant BOOLEAN DEFAULT NULL")
    cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS relevance_reason TEXT DEFAULT NULL")
    conn.commit()
    print("✅ Columns 'is_relevant' and 'relevance_reason' added (or already exist) in submissions table.")
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
