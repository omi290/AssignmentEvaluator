# ============================================================
# db.py — Database connection module using psycopg2
# Connects to Supabase PostgreSQL using credentials from .env
# ============================================================

import psycopg2
from psycopg2 import OperationalError
from config import (
    SUPABASE_DB_HOST,
    SUPABASE_DB_NAME,
    SUPABASE_DB_USER,
    SUPABASE_DB_PASSWORD,
    SUPABASE_DB_PORT,
)


def get_db_connection():
    """
    Opens and returns a new psycopg2 connection to the Supabase PostgreSQL DB.

    Usage:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT ...")
        rows = cur.fetchall()
        conn.close()

    Returns:
        psycopg2 connection object

    Raises:
        OperationalError: if the connection fails (wrong credentials, host unreachable, etc.)
    """
    try:
        conn = psycopg2.connect(
            host=SUPABASE_DB_HOST,
            dbname=SUPABASE_DB_NAME,
            user=SUPABASE_DB_USER,
            password=SUPABASE_DB_PASSWORD,
            port=SUPABASE_DB_PORT,
            sslmode="require",       # Supabase requires SSL
            connect_timeout=15,      # Fail fast instead of hanging
            options="-c statement_timeout=60000",  # 60s max per query
        )
        return conn
    except OperationalError as e:
        print(f"[db.py] Database connection failed: {e}")
        raise
