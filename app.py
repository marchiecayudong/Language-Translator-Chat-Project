from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from googletrans import Translator
import psycopg2
import os
from datetime import datetime
from urllib.parse import urlparse

# -----------------------
# APP CONFIG
# -----------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# Required for Render PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set!")

# Render sometimes gives postgres:// instead of postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

translator = Translator()


# -----------------------
# DATABASE CONNECTION
# -----------------------

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# -----------------------
# INITIALIZE TABLES
# -----------------------

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS translations (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        original TEXT,
        translated TEXT,
        detected TEXT,
        target TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


# -----------------------
# AUTH ROUTES
# -----------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            return f"Error creating user: {str(e)}"

        return redirect("/login")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, password FROM users WHERE username = %s",
            (username,)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            return redirect("/")

        return "Invalid login credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# -----------------------
# MAIN TRANSLATOR ROUTE
# -----------------------

@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Clear chat history
    if request.method == "POST" and request.form.get("action") == "clear":
        cur.execute(
            "DELETE FROM translations WHERE user_id = %s",
            (user_id,)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/")

    # New translation
    if request.method == "POST" and request.form.get("text"):
        text = request.form["text"]
        target_lang = request.form["language"]

        try:
            translation = translator.translate(text, dest=target_lang)
            detected_lang = translation.src
            translated_text = translation.text
        except Exception as e:
            cur.close()
            conn.close()
            return f"Translation error: {str(e)}"

        cur.execute("""
            INSERT INTO translations
            (user_id, original, translated, detected, target)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            user_id,
            text,
            translated_text,
            detected_lang,
            target_lang
        ))

        conn.commit()

    # Load history
    cur.execute("""
        SELECT original, translated, detected, target, created_at
        FROM translations
        WHERE user_id = %s
        ORDER BY created_at ASC
    """, (user_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "original": row[0],
            "translated": row[1],
            "detected": row[2],
            "target": row[3],
            "time": row[4].strftime("%Y-%m-%d %H:%M")
        })

    return render_template("index.html", history=history)


# -----------------------
# STARTUP
# -----------------------

# Ensure tables exist in production
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
