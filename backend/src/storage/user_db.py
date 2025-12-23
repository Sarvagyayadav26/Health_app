import email
import sqlite3
import os
import bcrypt
import logging

logger = logging.getLogger("backend")


DB_PATH = os.path.join(os.path.dirname(__file__), "user_data.db")
# DB_PATH = "/var/data/user_data.db"

print("DB PATH:", DB_PATH)
print("DIR EXISTS:", os.path.exists("/var/data"))
os.makedirs("/var/data", exist_ok=True)

print("DIR EXISTS (after):", os.path.exists("/var/data"))

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
            history_hidden INTEGER DEFAULT 0,
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

    # Table to store processed purchase tokens for idempotency
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_purchases (
            purchase_token TEXT PRIMARY KEY,
            email TEXT,
            product_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Index for faster history lookups by email and session_id
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_email_session ON messages (email, session_id);
    """)

    conn.commit()
    conn.close()

    # Ensure legacy databases have required columns (safe migration)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info('users')")
        cols = [r[1] for r in cursor.fetchall()]
        # Add missing columns with safe defaults
        if 'usage_count' not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN usage_count INTEGER DEFAULT 0")
        if 'chats' not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN chats INTEGER DEFAULT 5")
        if 'history_hidden' not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN history_hidden INTEGER DEFAULT 0")
        if 'created_at' not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        conn.commit()
    except Exception:
        logger.exception("Failed to migrate users table columns (non-fatal)")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def create_user(email: str, age: int, sex: str, password: str):
    # Do NOT normalize email here; preserve the exact value provided by the client.
    def _normalize_email(e):
        try:
            return e.strip().lower() if isinstance(e, str) else e
        except Exception:
            return e
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        cursor.execute("""
            INSERT INTO users (email, age, sex, password_hash, usage_count, chats)
            VALUES (?, ?, ?, ?, 0, 5)
        """, (email, age, sex, hashed))
        conn.commit()
        logger.info("%s: User created", email)
    except sqlite3.IntegrityError:
        # Re-raise as a ValueError so callers can handle duplicate-user cases cleanly
        conn.rollback()
        raise ValueError("user_exists")
    finally:
        conn.close()

def get_user(email: str):
    # Preserve email as provided; do not normalize
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Select explicit columns and coalesce nullable numeric fields so callers can
    # safely index into the returned row without extra length checks.
    cursor.execute(
        "SELECT email, age, sex, password_hash, COALESCE(usage_count,0) as usage_count, COALESCE(chats,0) as chats FROM users WHERE email = ?",
        (email,)
    )
    row = cursor.fetchone()

    conn.close()
    return row




def save_message(email: str, role: str, content: str, session_id: int = 1):
    # print(f"[DEBUG] save_message called - Email: {email}, Session: {session_id}, Role: {role}, Content: {content}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (email, session_id, role, content)
        VALUES (?, ?, ?, ?);
    """, (email, session_id, role, content))
    conn.commit()
    try:
        # If a real user message arrives, unhide history so new chats display
        if isinstance(role, str) and role.lower() == 'user':
            try:
                cursor.execute("UPDATE users SET history_hidden = 0 WHERE email = ?", (email,))
                conn.commit()
            except Exception:
                pass
    except Exception:
        pass
    conn.close()
    # print(f"[DEBUG] save_message completed - Email: {email}, Session: {session_id}") 



def get_messages(email: str, limit: int = 20, session_id: int = 1):
    # Do not normalize email
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT role, content, timestamp
        FROM messages
        WHERE email = ? AND session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (email, session_id, limit)
    )
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET usage_count = usage_count + 1 WHERE email = ?",
        (email,)
    )
    conn.commit()
    conn.close()

def get_usage(email):
    # Preserve email as provided
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
    # Preserve email as provided
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
    # Preserve email as provided
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


def is_purchase_token_processed(token: str) -> bool:
    """Return True if the purchase token has already been processed."""
    if not token:
        return False
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_purchases WHERE purchase_token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def mark_purchase_token_processed(token: str, email: str = None, product_id: str = None):
    """Record the purchase token so future requests are idempotent."""
    if not token:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO processed_purchases (purchase_token, email, product_id) VALUES (?, ?, ?)",
            (token, email, product_id)
        )
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


def list_processed_purchases(limit: int = 50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT purchase_token, email, product_id, created_at FROM processed_purchases ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def hide_history(email: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET history_hidden = 1 WHERE email = ?", (email,))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


def unhide_history(email: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET history_hidden = 0 WHERE email = ?", (email,))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


def is_history_hidden(email: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COALESCE(history_hidden,0) FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return bool(row and row[0])
    except Exception:
        return False
    finally:
        conn.close()
