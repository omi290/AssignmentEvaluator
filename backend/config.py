# ============================================================
# config.py — Load environment variables from .env file
# ============================================================

import os
from dotenv import load_dotenv

# Load variables from the .env file in this same folder
load_dotenv()

# ── Database connection settings (read from .env) ────────────
SUPABASE_DB_HOST     = os.getenv("SUPABASE_DB_HOST")
SUPABASE_DB_NAME     = os.getenv("SUPABASE_DB_NAME")
SUPABASE_DB_USER     = os.getenv("SUPABASE_DB_USER")
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")
# Use 6543 for pooler (transaction mode); use 5432 for direct/session mode
SUPABASE_DB_PORT     = os.getenv("SUPABASE_DB_PORT", "6543")

# ── Flask secret key ─────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_dev_key")


# ── Validate that required vars are present ──────────────────
REQUIRED_VARS = [
    "SUPABASE_DB_HOST",
    "SUPABASE_DB_NAME",
    "SUPABASE_DB_USER",
    "SUPABASE_DB_PASSWORD",
]

missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
if missing:
    raise EnvironmentError(
        f"[config.py] Missing required environment variables: {', '.join(missing)}\n"
        "Please fill in your .env file."
    )
