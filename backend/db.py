import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DEMO_USER_ID = 1


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing in .env")

    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            xp INTEGER DEFAULT 240,
            level INTEGER DEFAULT 3,
            streak INTEGER DEFAULT 5
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS learning_contents (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            subject TEXT,
            summary TEXT,
            topics JSONB,
            quiz JSONB,
            flashcards JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            score INTEGER,
            total INTEGER,
            xp_earned INTEGER,
            total_xp INTEGER,
            level INTEGER,
            next_level_xp INTEGER,
            weak_topics JSONB,
            recommended_groups JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        INSERT INTO users (id, name, xp, level, streak)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING;
    """, (DEMO_USER_ID, "Demo Student", 240, 3, 5))

    conn.commit()
    cur.close()
    conn.close()


def save_learning_content(content):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO learning_contents
        (user_id, subject, summary, topics, quiz, flashcards)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        DEMO_USER_ID,
        content.get("subject", "General"),
        content.get("summary", ""),
        json.dumps(content.get("topics", [])),
        json.dumps(content.get("quiz", [])),
        json.dumps(content.get("flashcards", []))
    ))

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return row["id"]


def get_latest_learning_content():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM learning_contents
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1;
    """, (DEMO_USER_ID,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row


def get_user():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id = %s;", (DEMO_USER_ID,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row


def update_user_xp(total_xp, level):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET xp = %s, level = %s
        WHERE id = %s;
    """, (total_xp, level, DEMO_USER_ID))

    conn.commit()
    cur.close()
    conn.close()


def save_quiz_result(result):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO quiz_results
        (user_id, score, total, xp_earned, total_xp, level, next_level_xp, weak_topics, recommended_groups)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        DEMO_USER_ID,
        result.get("score", 0),
        result.get("total", 0),
        result.get("xp_earned", 0),
        result.get("total_xp", 0),
        result.get("level", 1),
        result.get("next_level_xp", 100),
        json.dumps(result.get("weak_topics", [])),
        json.dumps(result.get("recommended_groups", []))
    ))

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return row["id"]


def get_latest_quiz_result():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM quiz_results
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1;
    """, (DEMO_USER_ID,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row