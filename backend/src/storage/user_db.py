import email
import sqlite3
import os
import bcrypt


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
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()
    
def create_user(email: str, age: int, sex: str, password: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    cursor.execute("""
        INSERT INTO users (email, age, sex, password_hash, usage_count, chats)
        VALUES (?, ?, ?, ?, 0, 2)
    """, (email, age, sex, hashed))

    conn.commit()
    conn.close()
    print(f"✅ User created: {email} with 5 chats")

def get_user(email: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT email, age, sex, password_hash, usage_count, chats FROM users WHERE email = ?",
        (email,)
    )
    row = cursor.fetchone()

    conn.close()
    return row




def save_message(email: str, role: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (email, role, content)
        VALUES (?, ?, ?);
    """, (email, role, content))
    conn.commit()
    conn.close()



def get_messages(email: str, limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content, timestamp
        FROM messages
        WHERE email = ?
        ORDER BY id DESC
        LIMIT ?;
    """, (email, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows[::-1]

def increment_usage(email):
    print("DEBUG: increment_usage param =", email, type(email))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET usage_count = usage_count + 1 WHERE email = ?",
        (email,)
    )
    conn.commit()
    conn.close()

def get_usage(email):
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
    print(f"✅ Adding {chats} chats to {email}")
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
    print(f"✅ Chats updated! User {email} now has {result[0] if result else 0} chats")
    conn.close()
