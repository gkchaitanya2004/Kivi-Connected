import datetime
import sqlite3
import bcrypt
import streamlit as st
import re
import uuid


@st.cache_resource
def get_connection():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            sarvam_api_key TEXT
        )
    """)
    conn.commit()


def add_user(email, password):
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(email, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()
    if result is None:
        return False
    return bcrypt.checkpw(password.encode(), result[0].encode())


def update_sarvam_key(email, api_key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET sarvam_api_key = ? WHERE email = ?", (api_key, email))
    conn.commit()

def get_sarvam_key(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT sarvam_api_key FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()
    return result[0] if result else None

def is_valid_email(email):
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(pattern, email) is not None

def is_valid_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r'[A-Z]', password):
        return "Password must contain an uppercase letter."
    if not re.search(r'[a-z]', password):
        return "Password must contain a lowercase letter."
    if not re.search(r'[0-9]', password):
        return "Password must contain a digit."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return "Password must contain a special character."
    return None  


def create_history_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT  NOT NULL,
            history_data TEXT
        )
    """)
    conn.commit()


def add_history(email, history_data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (email, history_data) VALUES (?, ?)", (email, history_data))
    conn.commit()


def get_history(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id,history_data FROM history WHERE email = ? ORDER BY id DESC", (email,))
    results = cursor.fetchall()
    return [(row[0], row[1]) for row in results]  # Return both id and history_data



def create_memory_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            email TEXT NOT NULL,
            entry TEXT NOT NULL,
            history_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (history_id) REFERENCES history(id)
        )
    """)
    conn.commit()



def add_memory_entry(entry_type, email, entry, history_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO memory (type, email, entry, history_id) VALUES (?, ?, ?, ?)",
        (entry_type, email, entry, history_id)
    )
    conn.commit()

    return cursor.lastrowid  


def voice_history_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()

def add_voice_history(session_id, question, answer):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO voice_history (session_id, question, answer, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, question, answer, datetime.now().isoformat(timespec="seconds"))
    )
    conn.commit()

def get_voice_history(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT question, answer, timestamp FROM voice_history WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    )
    results = cursor.fetchall()
    return [{"question": row[0], "answer": row[1], "timestamp": row[2]} for row in results]

def new_session_id() -> str:
    return str(uuid.uuid4())

def get_voice_sessions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id,
               MIN(timestamp) AS started_at,
               MAX(timestamp) AS last_at,
               COUNT(*) AS turn_count,
               (SELECT question FROM voice_history v2
                WHERE v2.session_id = v1.session_id
                ORDER BY v2.id ASC LIMIT 1) AS first_question
        FROM voice_history v1
        GROUP BY session_id
        ORDER BY last_at DESC
    """)
    results = cursor.fetchall()
    return [
        {
            "session_id": row[0],
            "started_at": row[1],
            "last_at": row[2],
            "turn_count": row[3],
            "first_question": row[4],
        }
        for row in results
    ]