import email
import sqlite3
import os
import bcrypt
import logging

logger = logging.getLogger("backend")


from .db_config import DB_PATH

# Safety net: ensure deployment is using the expected path
# assert DB_PATH == "/var/data/user_data.db", f"Unexpected DB_PATH: {DB_PATH}"

print("DB PATH:", DB_PATH)
print("DIR EXISTS:", os.path.exists(os.path.dirname(DB_PATH)))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

print("DIR EXISTS (after):", os.path.exists(os.path.dirname(DB_PATH)))


def normalize_username(value: str) -> str:
    """Normalize usernames/emails to a canonical form for storage and lookup.

    Uses `str.casefold()` for better Unicode case handling and strips whitespace.
    Defensive: returns the original value if it's not a string.
    """
    if not isinstance(value, str):
        return value
    return value.strip().casefold()

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_cleared_at TIMESTAMP DEFAULT NULL 
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

    # Table to store processed purchase tokens for idempotency ss
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
        if 'last_cleared_at' not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN last_cleared_at TIMESTAMP")
        conn.commit()
    except Exception:
        logger.exception("Failed to migrate users table columns (non-fatal)")
    finally:
        try:
            conn.close()
        except Exception:
            pass

def create_user(email: str, age: int, sex: str, password: str):
    # Normalize email - DB must store normalized email only
    email = normalize_username(email)
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
    # Normalize email for lookup — DB stores normalized emails only
    email = normalize_username(email)
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
    # Normalize email so messages.email is stored normalized
    email = normalize_username(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (email, session_id, role, content, timestamp)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, (email, session_id, role, content))

    conn.commit()
    # Note: do NOT automatically unhide history when a new message arrives.
    # History visibility is controlled by `hide_history` / `unhide_history` and
    # by the `last_cleared_at` timestamp used when fetching messages.
    conn.close()
    # print(f"[DEBUG] save_message completed - Email: {email}, Session: {session_id}") 



def get_messages(email: str, limit: int = 20, session_id: int = 1):
    # Normalize email for lookup
    email = normalize_username(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Return only messages newer than the user's last_cleared_at (if any).
    # Uses COALESCE to treat NULL as epoch (0) so the subquery always returns a value.
    cursor.execute(
        """
        SELECT role, content, timestamp
        FROM messages
        WHERE email = ? AND session_id = ?
        AND (
            (SELECT last_cleared_at FROM users WHERE email = ?) IS NULL
            OR timestamp >= datetime((SELECT last_cleared_at FROM users WHERE email = ?))
        )
        ORDER BY id DESC
        LIMIT ?
        """,
        (email, session_id, email, email, limit)  # 5 bindings
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
    email = normalize_username(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET usage_count = usage_count + 1 WHERE email = ?",
        (email,)
    )
    conn.commit()
    conn.close()

def get_usage(email):
    # Normalize email for lookup
    email = normalize_username(email)
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
    # Normalize email for lookup
    email = normalize_username(email)
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
    # Normalize email for lookup/storage
    email = normalize_username(email)
    logger.info("Adding %s chats to %s", chats, email)
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
    if email:
        email = normalize_username(email)
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
    email = normalize_username(email)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Mark history as hidden and record the time so older messages remain hidden
        cursor.execute("UPDATE users SET history_hidden = 1, last_cleared_at = CURRENT_TIMESTAMP WHERE email = ?", (email,))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


# def unhide_history(email: str):
#     email = normalize_username(email)
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     try:
#         # Unhide history and clear the last_cleared_at marker so older messages show again
#         cursor.execute("UPDATE users SET history_hidden = 0, last_cleared_at = NULL WHERE email = ?", (email,))
#         conn.commit()
#     except Exception:
#         conn.rollback()
#     finally:
#         conn.close()


def is_history_hidden(email: str) -> bool:
    email = normalize_username(email)
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
