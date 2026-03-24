from flask import Flask, render_template, request, redirect, url_for, flash, session
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

# DEBUG ROUTES
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
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                task TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255),
                product VARCHAR(255),
                price NUMERIC(10,2)
            );
        """)
        conn.commit()
        return "Tables created or already exist!"
    except Exception as e:
        conn.rollback()
        return f"Init failed: {str(e)}", 500
    finally:
        cur.close()
        conn.close()

# HELPER: AI Habit Analysis for Dashboard
def get_ai_habit_tip(recent_tasks, recent_orders, total_revenue):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "AI analysis not available right now."

    prompt = f"""
    You are a helpful business advisor for a small printing shop owner.
    User has {len(recent_tasks)} recent tasks: {recent_tasks}
    Recent orders: {recent_orders}
    Total revenue so far: ₹{total_revenue}

    Give 1-2 short, practical, encouraging tips about their habits, productivity, or business growth.
    Keep it actionable and positive. Max 2-3 sentences.
    """

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300
            },
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return "Keep going! Small consistent actions lead to big results."

# SIGNUP
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
            cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                flash("Username already exists! Try another one.", "danger")
                return redirect(url_for("signup"))
            
            hashed = generate_password_hash(password)
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
            conn.commit()
            flash("Account created successfully! Please login.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            conn.rollback()
            flash(f"Signup failed: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()
    
    return render_template("signup.html")

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Wrong username or password", "danger")
    
    return render_template("login.html")

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))

# DASHBOARD with AI Habit Tip
@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s", (session['user_id'],))
    tasks_count = cur.fetchone()[0]
    
    cur.execute("SELECT SUM(price) FROM orders WHERE user_id = %s", (session['user_id'],))
    total_revenue = cur.fetchone()[0] or 0
    
    # Get recent data for AI
    cur.execute("SELECT task FROM tasks WHERE user_id = %s ORDER BY id DESC LIMIT 5", (session['user_id'],))
    recent_tasks = [row[0] for row in cur.fetchall()]
    
    cur.execute("SELECT product, price FROM orders WHERE user_id = %s ORDER BY id DESC LIMIT 5", (session['user_id'],))
    recent_orders = cur.fetchall()
    
    cur.close()
    conn.close()

    ai_tip = get_ai_habit_tip(recent_tasks, recent_orders, total_revenue)

    return render_template("dashboard.html", 
                           username=session['username'], 
                           tasks_count=tasks_count, 
                           total_revenue=total_revenue,
                           ai_tip=ai_tip)

# TASKS
@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    cur = conn.cursor()
    
    if request.method == "POST":
        task = request.form.get("task")
        if task:
            cur.execute("INSERT INTO tasks (user_id, task) VALUES (%s, %s)", (session['user_id'], task))
            conn.commit()
            flash("Task added!", "success")
    
    cur.execute("SELECT id, task FROM tasks WHERE user_id = %s ORDER BY id DESC", (session['user_id'],))
    tasks_list = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template("tasks.html", tasks=tasks_list)

# ORDERS
@app.route("/orders", methods=["GET", "POST"])
def orders():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    cur = conn.cursor()
    
    if request.method == "POST":
        name = request.form.get("name")
        product = request.form.get("product")
        price = request.form.get("price")
        try:
            price = float(price)
            cur.execute("INSERT INTO orders (user_id, name, product, price) VALUES (%s, %s, %s, %s)",
                        (session['user_id'], name, product, price))
            conn.commit()
            flash("Order added!", "success")
        except ValueError:
            flash("Invalid price format", "danger")
    
    cur.execute("SELECT name, product, price FROM orders WHERE user_id = %s ORDER BY id DESC", (session['user_id'],))
    orders_list = cur.fetchall()
    total = sum(row[2] for row in orders_list)
    cur.close()
    conn.close()
    
    return render_template("orders.html", orders=orders_list, total=total)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
