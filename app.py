from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import traceback

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "supersecret1234567890changeit2026"

# Supabase connection (works with your existing DATABASE_URL on Render)
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"poolclass": "sqlalchemy.pool.NullPool"}

db = SQLAlchemy(app)

# ====================== MODELS ======================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # ← change to 'users.id'
    task = db.Column(db.Text, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # ← change to 'users.id'
    name = db.Column(db.String(255))
    product = db.Column(db.String(255))
    price = db.Column(db.Numeric(10,2))

# ====================== ERROR PAGES ======================
@app.errorhandler(500)
def server_error(e):
    tb = traceback.format_exc()
    return render_template('error.html', error=str(e), traceback=tb), 500

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error="Page not found", traceback=None), 404

# ====================== ROUTES ======================
@app.route("/init")  # Run this once after deploy
def init_db():
    db.create_all()
    return "✅ Tables created! Now delete this route if you want."

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("Please fill all fields", "danger")
            return redirect(url_for("signup"))
        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "danger")
            return redirect(url_for("signup"))
        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! Now login.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username")).first()
        if user and check_password_hash(user.password, request.form.get("password")):
            session['user_id'] = user.id
            session['username'] = user.username
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Wrong username or password", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    tasks_count = Task.query.filter_by(user_id=session['user_id']).count()
    orders = Order.query.filter_by(user_id=session['user_id']).all()
    total_revenue = sum(float(o.price or 0) for o in orders)
    return render_template("dashboard.html", tasks_count=tasks_count, total_revenue=total_revenue)

@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    if 'user_id' not in session: return redirect(url_for("login"))
    if request.method == "POST":
        new_task = Task(user_id=session['user_id'], task=request.form.get("task"))
        db.session.add(new_task)
        db.session.commit()
        flash("Task added!", "success")
    all_tasks = Task.query.filter_by(user_id=session['user_id']).all()
    return render_template("tasks.html", tasks=all_tasks)

@app.route("/orders", methods=["GET", "POST"])
def orders():
    if 'user_id' not in session: return redirect(url_for("login"))
    if request.method == "POST":
        new_order = Order(
            user_id=session['user_id'],
            name=request.form.get("name"),
            product=request.form.get("product"),
            price=float(request.form.get("price") or 0)
        )
        db.session.add(new_order)
        db.session.commit()
        flash("Order added!", "success")
    all_orders = Order.query.filter_by(user_id=session['user_id']).all()
    total = sum(float(o.price or 0) for o in all_orders)
    return render_template("orders.html", orders=all_orders, total=total)

if __name__ == "__main__":
    app.run(debug=True)
