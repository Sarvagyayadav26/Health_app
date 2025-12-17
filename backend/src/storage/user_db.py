import email
import sqlite3
import os
import bcrypt
import logging

logger = logging.getLogger("backend")


DB_PATH = os.path.join(os.path.dirname(__file__), "user_data.db")
# DB_PATH = "/var/data/user_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            age INTEGER,
            sex TEXT,
            password_hash TEXT,
            usage_count INTEGER DEFAULT 0,
            chats INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            session_id INTEGER DEFAULT 1,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Index for faster history lookups by email and session_id
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_email_session ON messages (email, session_id);
    """)

    conn.commit()
    conn.close()


def _normalize_email(e):
    try:
        return e.strip().lower() if isinstance(e, str) else e
    except Exception:
        return e
    
def create_user(email: str, age: int, sex: str, password: str):
    email = _normalize_email(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    cursor.execute("""
        INSERT INTO users (email, age, sex, password_hash, usage_count, chats)
        VALUES (?, ?, ?, ?, 0, 5)
    """, (email, age, sex, hashed))

    conn.commit()
    conn.close()
    logger.info("%s: User created", email)

def get_user(email: str):
    email = _normalize_email(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT email, age, sex, password_hash, usage_count, chats FROM users WHERE email = ?",
        (email,)
    )
    row = cursor.fetchone()

    conn.close()
    return row




def save_message(email: str, role: str, content: str, session_id: int = 1):
    # print(f"[DEBUG] save_message called - Email: {email}, Session: {session_id}, Role: {role}, Content: {content}")
    email = _normalize_email(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (email, session_id, role, content)
        VALUES (?, ?, ?, ?);
    """, (email, session_id, role, content))
    conn.commit()
    conn.close()
    # print(f"[DEBUG] save_message completed - Email: {email}, Session: {session_id}")



def get_messages(email: str, limit: int = 10, session_id: int = 1):
    email = _normalize_email(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content, timestamp
        FROM messages
        WHERE email = ? AND session_id = ?
        ORDER BY id DESC
        LIMIT ?;
    """, (email, session_id, limit))
    rows = cursor.fetchall()
    # Debug logging: count and (optionally) rows when debug enabled
    try:
        logger.debug("get_messages - email=%s session_id=%s limit=%s returned=%s", email, session_id, limit, len(rows))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("get_messages rows: %s", rows)
    except Exception:
        # If logging fails for any reason, record the failure so callers can be debugged
        logger.exception("Failed to log get_messages debug info")

    conn.close()
    # return in chronological order (oldest first)
    return rows[::-1]

def increment_usage(email):
    # print("DEBUG: increment_usage param =", email, type(email))

    email = _normalize_email(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET usage_count = usage_count + 1 WHERE email = ?",
        (email,)
    )
    conn.commit()
    conn.close()

def get_usage(email):
    email = _normalize_email(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT usage_count FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if row and row[0] is not None:
        return int(row[0])

    return 0

def get_usage_stats(email):
    """Get usage statistics for a user"""
    email = _normalize_email(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT usage_count, chats FROM users WHERE email = ?",
        (email,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "total_usage": int(row[0]) if row[0] is not None else 0,
            "chats": int(row[1]) if row[1] is not None else 0
        }
    
    return {
        "total_usage": 0,
        "chats": 0
    }

def add_chats(email, chats):
    """Add purchased chats to user's account
    
    Args:
        email: User email
        chats: Number of chats to add
    """
    logger.info("Adding %s chats to %s", chats, email)
    email = _normalize_email(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Simply add to chats
    cursor.execute(
        "UPDATE users SET chats = chats + ? WHERE email = ?",
        (chats, email)
    )
    
    rows_affected = cursor.rowcount
    conn.commit()
    
    # Verify the update
    cursor.execute("SELECT chats FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()
    logger.info("Chats updated! User %s now has %s", email, result[0] if result else 0)
    conn.close()
