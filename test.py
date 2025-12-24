import sqlite3
conn = sqlite3.connect("/var/data/user_data.db")
cur = conn.cursor()

for row in cur.execute("SELECT id, timestamp FROM messages ORDER BY id DESC LIMIT 5"):
    print(row)

print("Last cleared:", cur.execute("SELECT last_cleared_at FROM users WHERE email='z'").fetchone())
conn.close()
