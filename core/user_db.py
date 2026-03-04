"""SQLite user database for login/register — passwords hashed with SHA-256 + salt."""

import os
import sqlite3
import hashlib
import secrets

DB_DIR = os.path.join(os.path.expanduser("~"), ".lamiascribe")
DB_PATH = os.path.join(DB_DIR, "users.db")


def _get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  username TEXT UNIQUE NOT NULL,"
        "  display_name TEXT NOT NULL,"
        "  salt TEXT NOT NULL,"
        "  password_hash TEXT NOT NULL"
        ")"
    )
    conn.commit()
    return conn


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def register_user(username: str, display_name: str, password: str) -> tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    username = username.strip().lower()
    display_name = display_name.strip()

    if not username or not display_name or not password:
        return False, "All fields are required."

    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    conn = _get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            return False, "Username already exists. Please choose another."

        salt = secrets.token_hex(16)
        pw_hash = _hash_password(password, salt)
        conn.execute(
            "INSERT INTO users (username, display_name, salt, password_hash) VALUES (?, ?, ?, ?)",
            (username, display_name, salt, pw_hash),
        )
        conn.commit()
        return True, "Account created successfully."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> tuple[bool, str]:
    """Authenticate a user. Returns (success, display_name_or_error_message)."""
    username = username.strip().lower()

    if not username or not password:
        return False, "Username and password are required."

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT display_name, salt, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if not row:
            return False, "Invalid username or password."

        display_name, salt, stored_hash = row
        if _hash_password(password, salt) == stored_hash:
            return True, display_name
        else:
            return False, "Invalid username or password."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        conn.close()
