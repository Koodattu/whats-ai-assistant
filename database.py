import sqlite3
from config import CONV_DB_PATH, MAX_MESSAGES
from neonize.utils import log

def init_db():
    """Initialize the SQLite database with a unique constraint."""
    conn = sqlite3.connect(CONV_DB_PATH)
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

def save_message(user_id, message_content, timestamp, from_me):
    """Insert a message into the DB if it doesn't already exist."""
    conn = sqlite3.connect(CONV_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO messages (user_id, message_content, timestamp, from_me)
            VALUES (?, ?, ?, ?)
        """, (user_id, message_content, timestamp, from_me))
        conn.commit()
    except sqlite3.IntegrityError:
        log.debug(f"Message already exists for user {user_id}: {message_content}")
    except Exception as e:
        log.error(f"Failed to save message for user {user_id}: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_messages(user_id):
    """Retrieve all messages for a particular user_id."""
    conn = sqlite3.connect(CONV_DB_PATH)
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

def get_recent_messages(user_id):
    """
    Retrieve the most recent `max_messages` for a particular user_id, ordered oldest to newest.
    """
    conn = sqlite3.connect(CONV_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT message_content, timestamp, from_me
        FROM messages
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (user_id, MAX_MESSAGES))
    results = cursor.fetchall()
    conn.close()
    return results[::-1]

def delete_messages(user_id):
    """Delete all messages for the specified user_id from the database."""
    conn = sqlite3.connect(CONV_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_recent_messages_formatted(user_id):
    conversation_history = get_recent_messages(user_id)
    lines = []
    for msg_content, msg_timestamp, from_me in conversation_history:
        if from_me:
            speaker = "ASSISTANT"
        else:
            speaker = "USER"
        lines.append(f"{speaker}: {msg_content}")
    return "\n".join(lines)