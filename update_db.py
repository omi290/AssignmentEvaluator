import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from db import get_db_connection

try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("ALTER TABLE submissions ADD COLUMN IF NOT EXISTS student_comments TEXT")
    conn.commit()
    print("Column 'student_comments' added successfully.")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
