import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from db import get_db_connection

try:
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("--- SUBMISSIONS ---")
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'submissions'")
    for col in cur.fetchall():
        print(f"Col: {col[0]}")
    
    print("--- ASSIGNMENTS ---")
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'assignments'")
    for col in cur.fetchall():
        print(f"Col: {col[0]}")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
