import importlib
import re
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_database = importlib.import_module('database')
db_register_user = _database.register_user
db_authenticate_user = _database.authenticate_user
db_get_user_profile = _database.get_user_profile
db_upsert_google_user = _database.upsert_google_user
db_verify_user = _database.verify_user
db_reset_password = _database.reset_password
db_change_user_password = _database.change_user_password
db_update_user_name = _database.update_user_name

EMAIL_PATTERN = re.compile(r'^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$', re.IGNORECASE)

_ALLOWED_DOMAINS = {
    'gmail.com',
    'outlook.com',
    'hotmail.com',
    'yahoo.com',
    'yahoo.com.au',
    'icloud.com',
    'live.com',
    'protonmail.com',
    'me.com',
    'msn.com',
    'aol.com',
}


def _is_email_domain_allowed(email: str) -> bool:
    """Accept whitelisted consumer providers and any .edu academic domain."""
    domain = email.rsplit('@', 1)[-1].lower()
    if domain in _ALLOWED_DOMAINS:
        return True
    # Any .edu TLD or subdomain (e.g. student.monash.edu, .edu.au)
    if '.edu' in domain:
        return True
    return False


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_password(password: str) -> str | None:
    if len(password) < 8:
        return 'Password must be at least 8 characters long.'
    if not re.search(r'[A-Z]', password):
        return 'Password must include at least one uppercase letter.'
    if not re.search(r'[a-z]', password):
        return 'Password must include at least one lowercase letter.'
    if not re.search(r'\d', password):
        return 'Password must include at least one number.'
    return None


def register_user(first_name: str, email: str, password: str) -> tuple[bool, str]:
    clean_first_name = first_name.strip()
    clean_email = _normalize_email(email)

    if not clean_first_name:
        return False, 'First name is required.'
    if not clean_email:
        return False, 'Email is required.'
    if not EMAIL_PATTERN.match(clean_email):
        return False, 'Enter a valid email address.'
    if not _is_email_domain_allowed(clean_email):
        return (
            False,
            'Please use a recognised email provider — e.g. Gmail, Outlook, Hotmail, Yahoo, iCloud, or a university .edu address.',
        )

    password_error = _validate_password(password)
    if password_error:
        return False, password_error

    success = db_register_user(clean_first_name, clean_email, password)
    if success:
        return True, 'Account created successfully.'
    return False, 'An account with this email already exists.'


def authenticate_user(email: str, password: str) -> tuple[bool, str, dict | None]:
    clean_email = _normalize_email(email)
    if not clean_email:
        return False, 'Email is required.', None
    if not password:
        return False, 'Password is required.', None

    profile = db_authenticate_user(clean_email, password)
    if profile is None:
        return False, 'Invalid email or password.', None
    return True, 'Login successful.', profile


def get_user_profile(email: str) -> dict | None:
    return db_get_user_profile(_normalize_email(email))


def sync_google_user(
    email: str, first_name: str, google_subject: str | None = None
) -> dict | None:
    clean_email = _normalize_email(email)
    if not clean_email:
        return None
    return db_upsert_google_user(clean_email, first_name.strip(), google_subject)


def reset_password(email: str, new_password: str) -> tuple[bool, str]:
    clean_email = _normalize_email(email)
    if not clean_email:
        return False, 'Email is required.'
    if not EMAIL_PATTERN.match(clean_email):
        return False, 'Enter a valid email address.'
    password_error = _validate_password(new_password)
    if password_error:
        return False, password_error
    success = db_reset_password(clean_email, new_password)
    if success:
        return (
            True,
            'Password reset successfully. You can now log in with your new password.',
        )
    return False, 'No local account found with that email address.'


def update_user_name(email: str, new_first_name: str) -> tuple[bool, str]:
    clean_name = new_first_name.strip()
    if not clean_name:
        return False, 'Name cannot be empty.'
    clean_email = _normalize_email(email)
    if db_get_user_profile(clean_email) is None:
        return False, 'User not found.'
    success = db_update_user_name(clean_email, clean_name)
    if success:
        return True, 'Profile updated successfully.'
    return False, 'Could not update profile.'


def change_password(
    email: str, old_password: str, new_password: str
) -> tuple[bool, str]:
    clean_email = _normalize_email(email)
    profile = db_get_user_profile(clean_email)
    if profile is None:
        return False, 'User not found.'
    if profile.get('auth_provider') != 'local':
        return False, 'Password change is only available for local accounts.'
    password_error = _validate_password(new_password)
    if password_error:
        return False, password_error
    success = db_change_user_password(int(profile['id']), old_password, new_password)
    if success:
        return True, 'Password changed successfully.'
    return False, 'Current password is incorrect.'


def verify_user(email: str, password: str) -> bool:
    return db_verify_user(_normalize_email(email), password)
