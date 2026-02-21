from db import get_db_connection

try:
    conn = get_db_connection()
    print("DB CONNECTED")
    conn.close()
except Exception as e:
    print(e)