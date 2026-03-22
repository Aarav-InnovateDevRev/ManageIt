from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
from database import get_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "supersecret1234567890changeit2026"

# ── DEBUG ROUTES (kept as requested) ──
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
        return f"Database connected! Version: {version[0]}"
    except Exception as e:
        return f"DB Connection Failed: {str(e)}", 500

@app.route("/init")
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    return "Tables ready!"

# ── SIGNUP WITH FULL ERROR SHOWING ──
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            flash("Please fill all fields", "danger")
            return redirect(url_for("signup"))
        
        conn = get_db()
        cur = conn.cursor()
        try:
            # Check if username exists
            cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                flash("Username already exists! Try another one.", "danger")
                return redirect(url_for("signup"))
            
            hashed = generate_password_hash(password)
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
            conn.commit()
            flash("Account created successfully! Login now.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            conn.rollback()
            flash(f"Signup failed: {str(e)}", "danger")   # ← This will show the real error
            print("SIGNUP REAL ERROR:", str(e))  # also prints in Render logs
        finally:
            cur.close()
            conn.close()
    
    return render_template("signup.html")

# Login, dashboard, tasks, orders routes (same as before - keep your existing ones)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
