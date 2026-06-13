"""Application configuration — loads from settings table, falls back to JSON defaults."""
import json
import os

_default_settings_path = os.path.join(os.path.dirname(__file__), "default_settings.json")
with open(_default_settings_path) as f:
    _DEFAULT_SETTINGS = json.load(f)

DEFAULT_COMPANY_NAME = _DEFAULT_SETTINGS["company"]["name"]
DEFAULT_CURRENCY = _DEFAULT_SETTINGS["company"]["currency"]
DEFAULT_CURRENCY_SYMBOL = _DEFAULT_SETTINGS["company"]["currency_symbol"]
DEFAULT_MAX_DEVICES = _DEFAULT_SETTINGS["defaults"]["max_devices"]
DEFAULT_SESSION_TIMEOUT = _DEFAULT_SETTINGS["defaults"]["session_timeout"]

# psycopg (v3) has cp314 wheels on Arch. psycopg2 does not.
# SQLAlchemy uses psycopg (v3) by default with this URL.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://radius:radpass@localhost:5432/radius",
)

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-use-a-long-random-string")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 hours

RADIUS_SECRET = os.getenv("RADIUS_KEY", "testing123")
