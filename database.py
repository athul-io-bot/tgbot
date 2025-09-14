import sqlite3
from main import app, ADMINS, SPONSOR_CHANNEL

conn = sqlite3.connect("files.db", check_same_thread=False)
cursor = conn.cursor()

# Table for files
cursor.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_name TEXT,
    resolution TEXT,
    file_id TEXT,
    caption TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()
