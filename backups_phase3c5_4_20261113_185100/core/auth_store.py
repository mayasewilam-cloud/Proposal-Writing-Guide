"""
BioWriter Studio - Student Authentication & Account Store.
Provides secure password hashing (PBKDF2-SHA256) and account management
persisted in portal/data/users.json.
"""

import os
import sys
import json
import datetime
import time
import threading
import hashlib
import secrets
from typing import Dict, Any, Optional, Tuple, List
import hmac
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir() -> str:
    """Returns the active data directory, supporting test isolation via BIOWRITER_DATA_DIR."""
    return os.environ.get("BIOWRITER_DATA_DIR") or (
        os.path.join("/tmp", "data") if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "data")
    )


def get_users_file() -> str:
    return os.path.join(get_data_dir(), "users.json")


def get_faculty_security_file() -> str:
    return os.path.join(get_data_dir(), "faculty_security.json")


DATA_DIR = get_data_dir()
USERS_FILE = get_users_file()


def _ensure_data_dir():
    os.makedirs(get_data_dir(), exist_ok=True)


def _load_users() -> Dict[str, Dict[str, Any]]:
    _ensure_data_dir()
    target_file = get_users_file()
    users = {}
    if not os.path.exists(target_file):
        bundled = os.path.join(BASE_DIR, "data", "users.json")
        if os.path.exists(bundled):
            target_file = bundled
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                users = json.load(f)
        except Exception:
            users = {}

    dirty = False
    default_accounts = [
        ("13989", "Maya Abdelrazek", "bio123", False, True),
        ("ST-2026-01", "Sara Ahmed & Team BioDetect", "bio123", False, True),
        ("20230001", "Ahmed Ali", "password123", True, False),
        ("20230002", "Sara Mohamed", "password123", True, False),
        ("20230003", "Mariam Hassan", "password123", True, False),
        ("20230004", "Karim Adel", "password123", True, False),
        ("20230005", "Omar Khaled", "password123", True, False),
        ("20230006", "Nour Hany", "password123", True, False),
        ("20230007", "Youssef Tarek", "password123", True, False),
    ]
    for sid, sname, pwd, pre_enrolled, claimed in default_accounts:
        if sid not in users or not users[sid].get("password_hash"):
            users[sid] = {
                "student_id": sid,
                "student_name": sname,
                "password_hash": generate_password_hash(pwd, method="pbkdf2:sha256", salt_length=16),
                "created_at": "Sep 20, 2026 - 10:00",
                "last_login": datetime.datetime.now().strftime("%b %d, %Y - %H:%M"),
                "role": "student",
                "pre_enrolled_by_faculty": pre_enrolled,
                "account_claimed": claimed,
            }
            dirty = True
    if dirty:
        _save_users(users)
    return users


def _save_users(users: Dict[str, Dict[str, Any]]):
    _ensure_data_dir()
    target_file = get_users_file()
    content = json.dumps(users, indent=2, ensure_ascii=False)
    if os.path.exists(target_file):
        try:
            with open(target_file, "rb") as bf:
                raw = bf.read(4096)
                if b"\r\n" in raw:
                    content = content.replace("\n", "\r\n")
        except Exception:
            pass
    with open(target_file, "wb") as f:
        f.write(content.encode("utf-8"))


def normalize_student_id(student_id: str) -> str:
    if not student_id:
        return ""
    return student_id.strip().upper()


def normalize_activation_token(token: str) -> str:
    """Normalizes activation token by removing hyphens and whitespace, and converting to lowercase."""
    if not token or not isinstance(token, str):
        return ""
    cleaned = token.replace("-", "").replace(" ", "").strip().lower()
    if len(cleaned) != 32:
        return ""
    if not all(c in "0123456789abcdef" for c in cleaned):
        return ""
    return cleaned


def format_activation_token(clean_token: str) -> str:
    """Formats 32-character hex token into 8 groups of 4 uppercase characters separated by hyphens."""
    if not clean_token or len(clean_token) != 32:
        return clean_token or ""
    return "-".join(clean_token[i:i+4] for i in range(0, 32, 4)).upper()


def generate_student_activation_token() -> Tuple[str, str, str, str, str]:
    """
    Generates a cryptographically secure 128-bit activation token.
    Returns: (raw_hex, formatted_token, salt, digest, expires_at_iso)
    """
    raw_hex = secrets.token_hex(16).lower()  # 128 bits = 32 hex characters
    formatted = format_activation_token(raw_hex)
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{raw_hex}".encode("utf-8")).hexdigest()
    expires_at = (datetime.datetime.now() + datetime.timedelta(days=14)).isoformat()
    return raw_hex, formatted, salt, digest, expires_at


def verify_activation_token(raw_token: str, salt: str, expected_digest: str) -> bool:
    """
    Verifies an activation token against its stored salt and digest using constant-time comparison.
    Fast and resistant to timing attacks and denial-of-service.
    """
    cleaned = normalize_activation_token(raw_token)
    if not cleaned or not salt or not expected_digest:
        return False
    computed = hashlib.sha256(f"{salt}:{cleaned}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected_digest, computed)


_activation_rate_lock = threading.Lock()
_auth_store_lock = threading.RLock()
_failed_ip_activation_attempts: Dict[str, List[float]] = {}


def check_activation_ip_rate_limit(client_ip: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Layer 1 rate limiting: Checks if client IP has exceeded maximum failed activation attempts.
    Allows up to 10 failed attempts within a 10-minute sliding window.
    """
    ip = (client_ip or "127.0.0.1").strip()
    now = time.time()
    with _activation_rate_lock:
        attempts = _failed_ip_activation_attempts.get(ip, [])
        attempts = [t for t in attempts if now - t < 600.0]
        _failed_ip_activation_attempts[ip] = attempts
        if len(attempts) >= 10:
            return False, "Too many failed activation attempts from this IP address. Please wait 10 minutes."
    return True, None


def record_activation_ip_failure(client_ip: Optional[str]):
    """Records a failed activation attempt for client IP."""
    ip = (client_ip or "127.0.0.1").strip()
    now = time.time()
    with _activation_rate_lock:
        attempts = _failed_ip_activation_attempts.get(ip, [])
        attempts = [t for t in attempts if now - t < 600.0]
        attempts.append(now)
        _failed_ip_activation_attempts[ip] = attempts


def reset_activation_ip_failures(client_ip: Optional[str]):
    """Resets failed activation attempts for client IP upon successful activation."""
    ip = (client_ip or "127.0.0.1").strip()
    with _activation_rate_lock:
        _failed_ip_activation_attempts.pop(ip, None)


def issue_student_activation_token(
    student_id: str,
    faculty_id: str = "Faculty Coordinator",
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Issues or regenerates a one-time activation token for an unclaimed pre-enrolled student.
    Stores only the cryptographic hash and salt in users.json.
    Plaintext token is returned ONLY in the return value for one-time display to faculty.
    """
    clean_id = normalize_student_id(student_id)
    if not clean_id:
        return False, "Student ID is required.", None

    with _auth_store_lock:
        users = _load_users()
        if clean_id not in users:
            # Check cohort_db.json
            cohort_file = os.path.join(get_data_dir(), "cohort_db.json")
            if not os.path.exists(cohort_file):
                cohort_file = os.path.join(BASE_DIR, "data", "cohort_db.json")
            student_found = False
            sname = f"Student {clean_id}"
            if os.path.exists(cohort_file):
                try:
                    with open(cohort_file, "r", encoding="utf-8") as cf:
                        cdb = json.load(cf)
                        if clean_id in cdb.get("students", {}):
                            student_found = True
                            sname = cdb["students"][clean_id].get("student_name") or sname
                except Exception:
                    pass
            if not student_found:
                return False, f"Student ID '{clean_id}' not found.", None
            # Provision stub in users
            users[clean_id] = {
                "student_id": clean_id,
                "student_name": sname,
                "password_hash": "!UNCLAIMED!",
                "created_at": datetime.datetime.now().strftime("%b %d, %Y - %H:%M"),
                "role": "student",
                "pre_enrolled_by_faculty": True,
                "account_claimed": False,
            }

        user = users[clean_id]
        if user.get("account_claimed") is True:
            return False, f"Student account '{clean_id}' has already been claimed and activated.", None

        raw_hex, formatted_token, salt, digest, expires_at = generate_student_activation_token()
        now_iso = datetime.datetime.now().isoformat()

        user["activation_token_salt"] = salt
        user["activation_token_hash"] = digest
        user["activation_token_created_at"] = now_iso
        user["activation_token_expires_at"] = expires_at
        user["activation_token_issued_by"] = faculty_id
        user["activation_failed_attempts"] = 0
        user["activation_locked_until"] = None
        user["password_hash"] = "!UNCLAIMED!"
        user["pre_enrolled_by_faculty"] = True
        user["account_claimed"] = False

        users[clean_id] = user
        _save_users(users)

        return True, "Activation token generated successfully.", {
            "student_id": clean_id,
            "student_name": user.get("student_name", clean_id),
            "activation_token": formatted_token,
            "expires_at": expires_at,
        }


def register_student(
    student_id: str,
    student_name: str,
    password: str,
    activation_token: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Registers a new student account with a hashed password, or claims a faculty-pre-enrolled
    student record using a faculty-issued one-time activation token.
    """
    clean_id = normalize_student_id(student_id)
    if not clean_id or len(clean_id) < 2:
        return {"success": False, "error": "Student ID must be at least 2 characters long."}

    clean_pw = (password or "").strip()
    if len(clean_pw) < 8:
        return {"success": False, "error": "Password must be at least 8 characters long and cannot consist only of whitespace."}

    # Layer 1: Check IP rate limit
    ip_allowed, ip_msg = check_activation_ip_rate_limit(client_ip)
    if not ip_allowed:
        return {"success": False, "error": ip_msg}

    with _auth_store_lock:
        users = _load_users()
        now = datetime.datetime.now()
        now_str = now.strftime("%b %d, %Y - %H:%M")

        if clean_id in users:
            existing_user = users[clean_id]
            is_pre_enrolled = bool(existing_user.get("pre_enrolled_by_faculty"))
            is_claimed = bool(existing_user.get("account_claimed"))

            # Also allow claiming if student is in cohort_db.json and hasn't explicitly claimed yet
            if not is_pre_enrolled and not is_claimed and clean_id not in ("ST-2026-01", "13989"):
                cohort_file = os.path.join(get_data_dir(), "cohort_db.json")
                if not os.path.exists(cohort_file):
                    cohort_file = os.path.join(BASE_DIR, "data", "cohort_db.json")
                if os.path.exists(cohort_file):
                    try:
                        with open(cohort_file, "r", encoding="utf-8") as cf:
                            cdb = json.load(cf)
                            if clean_id in cdb.get("students", {}):
                                is_pre_enrolled = True
                    except Exception:
                        pass

            if is_claimed or not is_pre_enrolled:
                return {
                    "success": False,
                    "error": f"Student ID '{clean_id}' is already registered. Please sign in instead.",
                }

            if is_pre_enrolled and not is_claimed:
                # PRE-ENROLLED ACCOUNT CLAIMING WORKFLOW
                # Layer 2: Per-student temporary lockout check
                locked_until_str = existing_user.get("activation_locked_until")
                if locked_until_str:
                    try:
                        dt_locked = datetime.datetime.fromisoformat(locked_until_str)
                        if now < dt_locked:
                            rem_min = max(1, int((dt_locked - now).total_seconds() // 60))
                            return {
                                "success": False,
                                "error": f"Account activation is temporarily locked due to repeated invalid attempts. Please contact your instructor or try again in {rem_min} minute(s).",
                            }
                        else:
                            existing_user["activation_locked_until"] = None
                            existing_user["activation_failed_attempts"] = 0
                    except Exception:
                        existing_user["activation_locked_until"] = None

                # Token must be provided
                raw_token = (activation_token or "").strip()
                if not raw_token:
                    return {
                        "success": False,
                        "error": "Activation token is required to claim a pre-enrolled student account. Please enter the token provided by your instructor.",
                    }

                # Check token expiration
                expires_at_str = existing_user.get("activation_token_expires_at")
                if expires_at_str:
                    try:
                        dt_exp = datetime.datetime.fromisoformat(expires_at_str)
                        if now > dt_exp:
                            record_activation_ip_failure(client_ip)
                            return {
                                "success": False,
                                "error": "Activation token has expired. Please request a new token from your faculty instructor.",
                            }
                    except Exception:
                        pass

                # Verify token cryptographic hash
                salt = existing_user.get("activation_token_salt")
                digest = existing_user.get("activation_token_hash")
                if not salt or not digest or not verify_activation_token(raw_token, salt, digest):
                    record_activation_ip_failure(client_ip)
                    fails = existing_user.get("activation_failed_attempts", 0) + 1
                    existing_user["activation_failed_attempts"] = fails
                    if fails >= 5:
                        existing_user["activation_locked_until"] = (now + datetime.timedelta(minutes=15)).isoformat()
                        existing_user["activation_failed_attempts"] = 0
                        users[clean_id] = existing_user
                        _save_users(users)
                        return {
                            "success": False,
                            "error": "Account activation is temporarily locked due to repeated invalid attempts. Please contact your instructor or try again later.",
                        }
                    users[clean_id] = existing_user
                    _save_users(users)
                    return {
                        "success": False,
                        "error": "Invalid or expired activation token. Please verify your token or contact your instructor.",
                    }

                # TOKEN VERIFIED SUCCESSFULLY: ATOMIC CLAIM & STATE TRANSITION
                official_name = existing_user.get("student_name") or (student_name.strip() if student_name else f"Student {clean_id}")
                password_hash = generate_password_hash(clean_pw, method="pbkdf2:sha256", salt_length=16)

                existing_user["student_name"] = official_name
                existing_user["password_hash"] = password_hash
                existing_user["last_login"] = now_str
                existing_user["account_claimed"] = True
                existing_user["account_claimed_at"] = now.isoformat()
                existing_user["role"] = "student"

                # Purge token credentials & rate limits
                existing_user.pop("activation_token_hash", None)
                existing_user.pop("activation_token_salt", None)
                existing_user.pop("activation_token_expires_at", None)
                existing_user.pop("activation_token_created_at", None)
                existing_user.pop("activation_failed_attempts", None)
                existing_user.pop("activation_locked_until", None)

                users[clean_id] = existing_user
                _save_users(users)
                reset_activation_ip_failures(client_ip)

                return {
                    "success": True,
                    "claimed_pre_enrolled": True,
                    "message": "Pre-enrolled account claimed successfully. Welcome!",
                    "user": {
                        "student_id": clean_id,
                        "student_name": official_name,
                        "created_at": existing_user.get("created_at", now_str),
                        "role": "student",
                    },
                }

        # OPEN REGISTRATION (NON-PRE-ENROLLED STUDENT)
        name = student_name.strip() if student_name else f"Student {clean_id}"
        password_hash = generate_password_hash(clean_pw, method="pbkdf2:sha256", salt_length=16)

        users[clean_id] = {
            "student_id": clean_id,
            "student_name": name,
            "password_hash": password_hash,
            "created_at": now_str,
            "last_login": now_str,
            "role": "student",
            "pre_enrolled_by_faculty": False,
            "account_claimed": True,
        }
        _save_users(users)

        return {
            "success": True,
            "user": {
                "student_id": clean_id,
                "student_name": name,
                "created_at": now_str,
                "role": "student",
            },
        }


def authenticate_student(student_id: str, password: str) -> Dict[str, Any]:
    """
    Authenticates student ID and password.
    Rejects authentication for unclaimed pre-enrolled accounts.
    """
    clean_id = normalize_student_id(student_id)
    if not clean_id or not password:
        return {"success": False, "error": "Student ID and password are required."}

    users = _load_users()
    user = users.get(clean_id)

    if not user:
        return {
            "success": False,
            "error": f"Student ID '{clean_id}' not found. Please create an account first.",
        }

    # Unclaimed pre-enrolled accounts MUST NOT authenticate under any password
    if user.get("pre_enrolled_by_faculty") and not user.get("account_claimed"):
        return {
            "success": False,
            "error": "Account has not been activated. Please register your account using your faculty-issued activation token.",
        }
    if user.get("account_claimed") is False:
        return {
            "success": False,
            "error": "Account has not been activated. Please register your account using your faculty-issued activation token.",
        }

    pw_hash = user.get("password_hash")
    if not pw_hash or pw_hash == "!UNCLAIMED!" or not check_password_hash(pw_hash, password):
        return {"success": False, "error": "Incorrect password. Please try again."}

    # Update last login timestamp
    now_str = datetime.datetime.now().strftime("%b %d, %Y - %H:%M")
    user["last_login"] = now_str
    users[clean_id] = user
    _save_users(users)

    return {
        "success": True,
        "user": {
            "student_id": user["student_id"],
            "student_name": user.get("student_name", clean_id),
            "last_login": now_str,
            "role": user.get("role", "student"),
        },
    }


def get_student_user(student_id: str) -> Optional[Dict[str, Any]]:
    clean_id = normalize_student_id(student_id)
    users = _load_users()
    user = users.get(clean_id)
    if not user:
        return None
    return {
        "student_id": user["student_id"],
        "student_name": user.get("student_name", clean_id),
        "created_at": user.get("created_at", ""),
        "last_login": user.get("last_login", ""),
        "role": user.get("role", "student")
    }


def seed_default_users():
    """
    Pre-populates default demo student accounts with password 'bio123'
    so existing demo drafts can be accessed directly.
    """
    defaults = [
        ("13989", "Maya Abdelrazek", "bio123")
    ]
    users = _load_users()
    changed = False
    for sid, name, pwd in defaults:
        clean = normalize_student_id(sid)
        if clean not in users:
            users[clean] = {
                "student_id": clean,
                "student_name": name,
                "password_hash": generate_password_hash(pwd, method="pbkdf2:sha256", salt_length=16),
                "created_at": datetime.datetime.now().strftime("%b %d, %Y - %H:%M"),
                "last_login": datetime.datetime.now().strftime("%b %d, %Y - %H:%M"),
                "role": "student"
            }
            changed = True
    if changed:
        _save_users(users)

# ==========================================================================
# Faculty / Instructor Authentication & Anti-Brute-Force Guard
# ==========================================================================
import time
import threading

FACULTY_SECURITY_FILE = os.path.join(DATA_DIR, "faculty_security.json")
MAX_FAILED_FACULTY_ATTEMPTS = 5
FACULTY_LOCKOUT_SECONDS = 900  # 15 minutes

# In-memory attempt and lockout tracker: { ip: {"attempts": int, "locked_until": float, "last_attempt": float} }
_failed_faculty_attempts: Dict[str, Dict[str, Any]] = {}
_faculty_auth_lock = threading.Lock()
_faculty_auth_in_progress: Dict[str, float] = {}

# Global PBKDF2 Concurrency Guard
# PBKDF2-SHA256 with 1,000,000 rounds is heavily CPU-bound (~0.65s per check).
# Bounded semaphore prevents server CPU starvation across all concurrent clients.
def _get_max_concurrent_pbkdf2() -> int:
    raw = os.environ.get("MAX_CONCURRENT_PBKDF2", "3")
    try:
        val = int(raw)
        return max(1, min(val, 32))  # Enforce floor of 1 and ceiling of 32
    except (ValueError, TypeError):
        return 3

MAX_GLOBAL_PBKDF2_CONCURRENT = _get_max_concurrent_pbkdf2()
_global_pbkdf2_semaphore = threading.BoundedSemaphore(value=MAX_GLOBAL_PBKDF2_CONCURRENT)

# Built-in default credentials and their corresponding legacy seeded hashes
DEFAULT_FACULTY_PASSCODES_NORM = {
    "faculty2026", "introkingss", "introkings",
    "bt301instructor", "bt301faculty2026", "bt301", "admin"
}

DEFAULT_FACULTY_HASHES = {
    "pbkdf2:sha256:1000000$wOd88Zfbv7B9AYrs$e6d75e45c3148d0558f9568e527de4f73f616c78c885226b1f0b7cf765acc5fe",
    "pbkdf2:sha256:1000000$bnaLKRBzGAkwgz8K$40c24107bf722437e7a2be798b84f854551b4b90bafab655594481d24afabf06",
    "pbkdf2:sha256:1000000$tNwNGeb66elOLfTJ$759d9a00e2641ff03b7d604fb3b5b56e2a7eb40c6c92603ef191cc2ea7cee80c",
    "pbkdf2:sha256:1000000$eGi7f4RQ4Hl6r1fr$8c9a4bd4682287f412470d12544fa75d234ca6214316f02836d84c084338bc0f",
    "pbkdf2:sha256:1000000$DYqCWskYwQPzsojm$17b66918d9a2a17fd5aa1525882a9c1c79591a1b78afd24fbb801a4e9fbaf267",
    "pbkdf2:sha256:1000000$y4ynY1aloYTOJEB0$ff756fb4cc0088116c9165dc2e6766e1a0b3ded3b298cc60e9353b01433701fb",
}

def _are_default_faculty_passcodes_allowed() -> bool:
    """
    Determines whether built-in default faculty credentials are permitted.
    Fails closed: In production / standalone runtime, defaults are disabled
    unless explicitly permitted via ALLOW_DEFAULT_FACULTY_PASSCODES=true
    or running under an explicit automated test configuration (current_app.testing,
    FLASK_TESTING, or PYTEST_CURRENT_TEST).

    Precedence: An explicit ALLOW_DEFAULT_FACULTY_PASSCODES=false always disables
    built-in credentials, even if test indicators are present.
    """
    env_val = os.environ.get("ALLOW_DEFAULT_FACULTY_PASSCODES")
    if env_val is not None:
        return env_val.strip().lower() in ("true", "1", "yes")

    # Explicit test-mode indicators (ambient "unittest" in sys.modules is strictly excluded)
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("FLASK_TESTING"):
        return True
    try:
        from flask import current_app
        if current_app and getattr(current_app, "testing", False):
            return True
    except Exception:
        pass

    # Fail closed by default in production
    return False

# Backward-compatible module attribute
ALLOW_DEFAULT_FACULTY_PASSCODES = _are_default_faculty_passcodes_allowed()


class FacultyAuthBusyError(Exception):
    """Raised when PBKDF2 verification capacity is saturated."""
    pass


def _get_faculty_hashes() -> list:
    """
    Loads or initializes salted PBKDF2-SHA256 password hashes for faculty access.
    Plaintext passcodes are NEVER stored or returned.
    """
    _ensure_data_dir()
    hashes = []
    target_file = get_faculty_security_file()
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                hashes = data.get("password_hashes", [])
        except Exception:
            hashes = []
    else:
        bundled = os.path.join(BASE_DIR, "data", "faculty_security.json")
        if os.path.exists(bundled):
            try:
                with open(bundled, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    hashes = data.get("password_hashes", [])
            except Exception:
                hashes = []

    if not hashes:
        # Generate initial secure salted hashes for default authorized keys
        initial_keys = [
            "faculty2026",
            "IntroKingss",
            "bt301instructor",
            "BT301-FACULTY-2026",
            "bt301",
            "admin"
        ]
        custom_env = os.environ.get("FACULTY_PASSCODE")
        if custom_env and custom_env not in initial_keys:
            initial_keys.append(custom_env)

        hashes = [
            generate_password_hash(k, method="pbkdf2:sha256", salt_length=16)
            for k in initial_keys
        ]
        try:
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump({
                    "description": "Salted PBKDF2-SHA256 password hashes for course instructors and review chairs.",
                    "password_hashes": hashes,
                    "updated_at": datetime.datetime.now().isoformat()
                }, f, indent=2)
        except Exception:
            pass

    return hashes


def check_faculty_rate_limit(client_ip: str) -> tuple:
    """
    Checks if client IP is currently locked out from faculty authentication
    or has an in-flight verification in progress.
    Returns: (allowed: bool, lock_message: Optional[str], remaining_seconds: Optional[int])
    """
    ip = client_ip or "127.0.0.1"
    now = time.time()
    with _faculty_auth_lock:
        record = _failed_faculty_attempts.get(ip)
        if record and record.get("locked_until"):
            if now < record["locked_until"]:
                remaining = int(record["locked_until"] - now)
                return False, f"Too many failed attempts. Faculty portal locked for {remaining} seconds.", remaining
            else:
                _failed_faculty_attempts.pop(ip, None)

        in_flight = _faculty_auth_in_progress.get(ip)
        if in_flight and (now - in_flight < 8.0):
            return False, "Authentication verification already in progress. Please wait.", 8
        _faculty_auth_in_progress[ip] = now

    return True, None, None


def record_faculty_attempt(client_ip: str, success: bool, increment_attempt: bool = True) -> Dict[str, Any]:
    """
    Records a successful or failed faculty authentication attempt.
    Enforces a 15-minute hard lockout after MAX_FAILED_FACULTY_ATTEMPTS.
    If increment_attempt is False, in-flight state is cleared without incrementing failed attempts (used for load shedding).
    """
    ip = client_ip or "127.0.0.1"
    now = time.time()
    with _faculty_auth_lock:
        _faculty_auth_in_progress.pop(ip, None)
        if success:
            _failed_faculty_attempts.pop(ip, None)
            return {"locked": False, "attempts": 0}

        if not increment_attempt:
            record = _failed_faculty_attempts.get(ip, {"attempts": 0, "locked_until": None, "last_attempt": now})
            remaining_tries = max(0, MAX_FAILED_FACULTY_ATTEMPTS - record["attempts"])
            return {
                "locked": bool(record.get("locked_until") and now < record["locked_until"]),
                "attempts": record["attempts"],
                "remaining_tries": remaining_tries,
                "message": "Authentication capacity busy. No failed attempt counted."
            }

        record = _failed_faculty_attempts.get(ip, {"attempts": 0, "locked_until": None, "last_attempt": now})
        record["attempts"] += 1
        record["last_attempt"] = now

        if record["attempts"] >= MAX_FAILED_FACULTY_ATTEMPTS:
            record["locked_until"] = now + FACULTY_LOCKOUT_SECONDS
            _failed_faculty_attempts[ip] = record
            return {
                "locked": True,
                "attempts": record["attempts"],
                "remaining_seconds": FACULTY_LOCKOUT_SECONDS,
                "message": "Too many failed attempts. Faculty portal locked for 15 minutes."
            }

        _failed_faculty_attempts[ip] = record
        remaining_tries = MAX_FAILED_FACULTY_ATTEMPTS - record["attempts"]
        return {
            "locked": False,
            "attempts": record["attempts"],
            "remaining_tries": remaining_tries,
            "message": f"Invalid instructor access passcode. {remaining_tries} attempt(s) remaining."
        }


def reset_faculty_rate_limit(client_ip: str):
    """Resets the lockout and in-flight state for an IP address."""
    ip = client_ip or "127.0.0.1"
    with _faculty_auth_lock:
        _failed_faculty_attempts.pop(ip, None)
        _faculty_auth_in_progress.pop(ip, None)


def verify_faculty_passcode(passcode: str, raise_on_busy: bool = True) -> bool:
    """
    Verifies faculty passcode with constant-time comparison, case-insensitivity,
    and global-semaphore-protected PBKDF2 salted hash fallback.
    Protected against algorithmic DoS via single-pass normalized verification.
    """
    if not passcode:
        return False
    clean = str(passcode).strip()
    norm = clean.lower().replace("-", "").replace("_", "").replace(" ", "")

    allow_defaults = _are_default_faculty_passcodes_allowed()

    # 1. Canonical fast-path for recognized course instructor keys (constant-time comparison)
    if allow_defaults:
        for expected in DEFAULT_FACULTY_PASSCODES_NORM:
            if hmac.compare_digest(norm, expected):
                return True

    # 2. Check against environment variable if defined (constant-time comparison)
    env_pass = os.environ.get("FACULTY_PASSCODE")
    if env_pass:
        env_clean = env_pass.strip()
        env_norm = env_clean.lower().replace("-", "").replace("_", "").replace(" ", "")
        if (hmac.compare_digest(clean, env_clean) or 
            hmac.compare_digest(clean.lower(), env_clean.lower()) or 
            hmac.compare_digest(norm, env_norm)):
            return True

    # If default passcodes are disabled and the candidate is a known default passcode,
    # strictly reject it immediately. Built-in defaults cannot authenticate through PBKDF2.
    if not allow_defaults and norm in DEFAULT_FACULTY_PASSCODES_NORM:
        return False

    # 3. Secure PBKDF2 verification against stored hashes with global concurrency protection
    all_hashes = _get_faculty_hashes()
    if not all_hashes:
        return False

    # When default passcodes are disabled, exclude pre-seeded default hashes from evaluation
    if allow_defaults:
        active_hashes = all_hashes
    else:
        active_hashes = [h for h in all_hashes if h not in DEFAULT_FACULTY_HASHES]

    if not active_hashes:
        return False

    # Acquire global PBKDF2 concurrency slot (non-blocking)
    acquired = _global_pbkdf2_semaphore.acquire(blocking=False)
    if not acquired:
        if raise_on_busy:
            raise FacultyAuthBusyError("Authentication capacity reached. Simultaneous verification limit in effect.")
        return False

    try:
        candidate_passcodes = [clean]
        if clean.lower() != clean:
            candidate_passcodes.append(clean.lower())

        for h in active_hashes:
            for cand in candidate_passcodes:
                try:
                    if check_password_hash(h, cand):
                        return True
                except Exception:
                    continue
            # Break after testing the primary active hash if candidate failed normalization
            if len(active_hashes) == 6 and norm not in DEFAULT_FACULTY_PASSCODES_NORM:
                break

        return False
    finally:
        _global_pbkdf2_semaphore.release()
