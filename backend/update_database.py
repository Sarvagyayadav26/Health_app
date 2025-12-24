import sqlite3, sys
from pathlib import Path

DB = Path(__file__).resolve().parents[0] / "src" / "storage" / "user_data.db"

def main():
    if not DB.exists():
        print("DB not found:", DB); sys.exit(1)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # abort if normalization would create duplicates
    cur.execute("SELECT lower(trim(email)) AS norm, COUNT(*) FROM users GROUP BY norm HAVING COUNT(*)>1;")
    dupes = cur.fetchall()
    if dupes:
        print("Duplicate normalized emails found; resolve before running:")
        for norm, cnt in dupes:
            print(f"  {norm} ({cnt})")
        conn.close()
        sys.exit(2)

    try:
        cur.execute("BEGIN")
        cur.execute("UPDATE users SET email = lower(trim(email));")
        cur.execute("UPDATE messages SET email = lower(trim(email));")
        cur.execute("UPDATE processed_purchases SET email = lower(trim(email));")
        conn.commit()
        print("Normalization complete.")
        cur.execute("VACUUM;")
    except Exception as e:
        conn.rollback()
        print("Failed:", e)
        sys.exit(3)
    finally:
        conn.close()

if __name__ == '__main__':
    main()