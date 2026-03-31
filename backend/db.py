# db.py — Database connection module using psycopg2, connects to Supabase PostgreSQL

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
    # Opens and returns a new psycopg2 connection to the Supabase PostgreSQL DB
    try:
        conn = psycopg2.connect(
            host=SUPABASE_DB_HOST,
            dbname=SUPABASE_DB_NAME,
            user=SUPABASE_DB_USER,
            password=SUPABASE_DB_PASSWORD,
            port=SUPABASE_DB_PORT,
            sslmode="require",
            connect_timeout=15,
            options="-c statement_timeout=60000",
        )
        return conn
    except OperationalError as e:
        print(f"[db.py] Database connection failed: {e}")
        raise
