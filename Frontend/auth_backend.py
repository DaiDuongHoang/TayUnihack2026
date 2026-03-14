import importlib
import re
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_database = importlib.import_module("database")
db_register_user = _database.register_user
db_authenticate_user = _database.authenticate_user
db_get_user_profile = _database.get_user_profile
db_upsert_google_user = _database.upsert_google_user
db_verify_user = _database.verify_user

EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_password(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return "Password must include at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "Password must include at least one lowercase letter."
    if not re.search(r"\d", password):
        return "Password must include at least one number."
    return None


def register_user(first_name: str, email: str, password: str) -> tuple[bool, str]:
    clean_first_name = first_name.strip()
    clean_email = _normalize_email(email)

    if not clean_first_name:
        return False, "First name is required."
    if not clean_email:
        return False, "Email is required."
    if not EMAIL_PATTERN.match(clean_email):
        return False, "Enter a valid email address."

    password_error = _validate_password(password)
    if password_error:
        return False, password_error

    success = db_register_user(clean_first_name, clean_email, password)
    if success:
        return True, "Account created successfully."
    return False, "An account with this email already exists."


def authenticate_user(email: str, password: str) -> tuple[bool, str, dict | None]:
    clean_email = _normalize_email(email)
    if not clean_email:
        return False, "Email is required.", None
    if not password:
        return False, "Password is required.", None

    profile = db_authenticate_user(clean_email, password)
    if profile is None:
        return False, "Invalid email or password.", None
    return True, "Login successful.", profile


def get_user_profile(email: str) -> dict | None:
    return db_get_user_profile(_normalize_email(email))


def sync_google_user(
    email: str, first_name: str, google_subject: str | None = None
) -> dict | None:
    clean_email = _normalize_email(email)
    if not clean_email:
        return None
    return db_upsert_google_user(clean_email, first_name.strip(), google_subject)


def verify_user(email: str, password: str) -> bool:
    return db_verify_user(_normalize_email(email), password)
