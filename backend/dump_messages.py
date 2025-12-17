import sqlite3
c = sqlite3.connect("src/storage/user_data.db")
for r in c.execute("SELECT id, role, content, timestamp FROM messages WHERE email=? ORDER BY id", ("debug@example.com",)):
    print(r)
c.close()
