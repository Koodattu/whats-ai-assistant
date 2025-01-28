import os
import sqlite3

DB_PATH = "db/conversations.sqlite3"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db(db_path=DB_PATH):
    """Initialize the SQLite database with a unique constraint."""
    # create folder if it doesn't exist

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            message_content TEXT,
            timestamp INTEGER,
            from_me BOOLEAN,
            UNIQUE(user_id, message_content, timestamp, from_me)
        )
    """)
    conn.commit()
    conn.close()

def save_message(user_id, message_content, timestamp, from_me, db_path=DB_PATH):
    """Insert a message into the DB if it doesn't already exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO messages (user_id, message_content, timestamp, from_me)
            VALUES (?, ?, ?, ?)
        """, (user_id, message_content, timestamp, from_me))
        conn.commit()
    except sqlite3.IntegrityError:
        # A message with the same (user_id, message_content, timestamp, from_me) already exists
        pass
    finally:
        conn.close()

def get_messages(user_id, db_path=DB_PATH):
    """Retrieve all messages for a particular user_id."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message_content, timestamp, from_me
        FROM messages
        WHERE user_id = ?
        ORDER BY timestamp
    """, (user_id,))
    results = cursor.fetchall()
    conn.close()
    return results
