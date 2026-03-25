from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests
from database import get_db
from datetime import date

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
    return "OK - App is running", 200

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
        return f"DB Failed: {str(e)}", 500

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
                task TEXT NOT NULL,
                deadline DATE,
                goal TEXT
            );
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255),
                product VARCHAR(255),
                price NUMERIC(10,2),
                capital_invested NUMERIC(10,2) DEFAULT 0,
                order_date DATE DEFAULT CURRENT_DATE
            );
        """)
        conn.commit()
        return "Tables ready!"
    except Exception as e:
        conn.rollback()
        return f"Init failed: {str(e)}", 500
    finally:
        cur.close()
        conn.close()

# AI Helper
def get_ai_response(prompt):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "AI not available right now."
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300
            }
        )
        return response.json()["choices"][0]["message"]["content"].strip()
    except:
        return "Keep going!"

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
                flash("Username already exists!", "danger")
                return redirect(url_for("signup"))
            
            hashed = generate_password_hash(password)
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
            conn.commit()
            flash("Account created! Please login.", "success")
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

# DASHBOARD with AI Habit & Marketing Analysis
@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Basic stats
        cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s", (session['user_id'],))
        tasks_count = cur.fetchone()[0]
        
        cur.execute("SELECT SUM(price - COALESCE(capital_invested, 0)) FROM orders WHERE user_id = %s", (session['user_id'],))
        net_profit = cur.fetchone()[0] or 0
        
        # Recent data for AI
        cur.execute("SELECT task FROM tasks WHERE user_id = %s ORDER BY id DESC LIMIT 5", (session['user_id'],))
        recent_tasks = [row[0] for row in cur.fetchall()]
        
        cur.execute("SELECT product FROM orders WHERE user_id = %s GROUP BY product ORDER BY COUNT(*) DESC LIMIT 3", (session['user_id'],))
        top_products = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
    except Exception as e:
        flash(f"Database error: {str(e)}", "danger")
        tasks_count = 0
        net_profit = 0
        recent_tasks = []
        top_products = []

    # Safe AI calls with fallback
    habit_tip = "Keep going! Small consistent actions lead to big results."
    marketing_tip = "Focus on your top products — consistency wins."

    try:
        habit_tip = get_ai_response(f"User has {tasks_count} tasks and net profit ₹{net_profit}. Recent tasks: {recent_tasks}. Give 1 short practical tip.")
        marketing_tip = get_ai_response(f"Top products: {top_products}. Give 1 short marketing tip based on order patterns.")
    except Exception as ai_e:
        print("AI tip failed:", str(ai_e))  # visible in Render logs

    return render_template("dashboard.html", 
                           username=session['username'], 
                           tasks_count=tasks_count, 
                           net_profit=net_profit, 
                           habit_tip=habit_tip,
                           marketing_tip=marketing_tip)

# ORDERS with delete, capital invested
@app.route("/orders", methods=["GET", "POST"])
def orders():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    cur = conn.cursor()
    
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            name = request.form.get("name")
            product = request.form.get("product")
            price = float(request.form.get("price") or 0)
            capital = float(request.form.get("capital") or 0)
            cur.execute("INSERT INTO orders (user_id, name, product, price, capital_invested) VALUES (%s, %s, %s, %s, %s)",
                        (session['user_id'], name, product, price, capital))
            conn.commit()
            flash("Order added!", "success")
        elif action == "delete":
            order_id = request.form.get("order_id")
            cur.execute("DELETE FROM orders WHERE id = %s AND user_id = %s", (order_id, session['user_id']))
            conn.commit()
            flash("Order deleted!", "success")
    
    cur.execute("SELECT id, name, product, price, capital_invested, order_date FROM orders WHERE user_id = %s ORDER BY order_date DESC", (session['user_id'],))
    orders_list = cur.fetchall()
    total_revenue = sum(row[3] for row in orders_list)
    total_capital = sum(row[4] for row in orders_list)
    net_profit = total_revenue - total_capital
    cur.close()
    conn.close()
    
    return render_template("orders.html", orders=orders_list, total_revenue=total_revenue, net_profit=net_profit)

# Q/A SURVEY PAGE
@app.route("/survey", methods=["GET", "POST"])
def survey():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        answers = request.form.to_dict()
        prompt = f"User answers: {answers}. Analyse why their business might not be growing and give 3 practical tips."
        analysis = get_ai_response(prompt)
        return render_template("survey_result.html", analysis=analysis)
    
    return render_template("survey.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
