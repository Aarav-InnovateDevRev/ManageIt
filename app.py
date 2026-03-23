from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests
from database import get_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "supersecret1234567890changeit2026"

# ERROR HANDLERS
@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error=str(e)), 500

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error="Page not found"), 404

# DEBUG ROUTES (kept)
@app.route("/health")
def health():
    return "OK - App is running (raw psycopg2 mode)", 200

@app.route("/test-db")
def test_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        cur.close()
        conn.close()
        return f"Database connected! PostgreSQL version: {version[0]}"
    except Exception as e:
        return f"DB Connection Failed: {str(e)}", 500

@app.route("/init")
def init_db():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(80) UNIQUE NOT NULL, password VARCHAR(255) NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, task TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, name VARCHAR(255), product VARCHAR(255), price NUMERIC(10,2));
        """)
        conn.commit()
        return "Tables created or already exist!"
    except Exception as e:
        conn.rollback()
        return f"Init failed: {str(e)}", 500
    finally:
        cur.close()
        conn.close()

# AI CHAT PAGE
@app.route("/ai-chat")
def ai_chat_page():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    return render_template("ai_chat.html")

# AI CHAT API
@app.route("/chat", methods=["POST"])
def chat():
    if 'user_id' not in session:
        return jsonify({"error": "Please login first"}), 401
    
    message = request.json.get("message")
    if not message:
        return jsonify({"error": "No message provided"}), 400

    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return jsonify({"error": "AI API key not set in Render"}), 500

    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "grok-beta",
                "messages": [{"role": "user", "content": message}],
                "temperature": 0.7,
                "max_tokens": 300
            }
        )
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# SIGNUP, LOGIN, DASHBOARD, TASKS, ORDERS (same as previous stable version)
# (Copy-paste your working signup, login, dashboard, tasks, orders routes here from the last stable app.py I gave you)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
