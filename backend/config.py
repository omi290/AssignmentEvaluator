# config.py — Load environment variables from .env file

import os
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

# Database connection settings from .env
SUPABASE_DB_HOST     = os.getenv("SUPABASE_DB_HOST")
SUPABASE_DB_NAME     = os.getenv("SUPABASE_DB_NAME")
SUPABASE_DB_USER     = os.getenv("SUPABASE_DB_USER")
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")
SUPABASE_DB_PORT     = os.getenv("SUPABASE_DB_PORT", "6543")  # 6543 for pooler, 5432 for direct

# Flask secret key──
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_dev_key")


# Upload settings──
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# OpenAI API key for AI evaluation (optional — system falls back to heuristic if missing)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Validate that required vars are present
REQUIRED_VARS = [
    "SUPABASE_DB_HOST",
    "SUPABASE_DB_NAME",
    "SUPABASE_DB_USER",
    "SUPABASE_DB_PASSWORD",
    "SUPABASE_URL",
    "SUPABASE_KEY",
]

missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
if missing:
    raise EnvironmentError(
        f"[config.py] Missing required environment variables: {', '.join(missing)}\n"
        "Please fill in your .env file."
    )
