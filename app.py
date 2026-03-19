import os
import sys
import logging
import traceback
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# ── Force logging from the very beginning ──
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
logging.debug("=== APP.PY STARTING ===")
logging.debug(f"Python version: {sys.version}")
logging.debug(f"Current working dir: {os.getcwd()}")

app = Flask(__name__)

# Secret key
app.secret_key = os.environ.get("SECRET_KEY") or "supersecret1234567890changeit2026"
logging.debug("Secret key loaded")

# Database URL fix for Supabase
DATABASE_URL = os.environ.get("DATABASE_URL")
logging.debug(f"DATABASE_URL exists: {'yes' if DATABASE_URL else 'NO'}")
if DATABASE_URL:
    logging.debug(f"DATABASE_URL starts with: {DATABASE_URL[:30]}...")
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        logging.debug("Converted postgres:// to postgresql://")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"poolclass": "sqlalchemy.pool.NullPool"}

logging.debug("SQLAlchemy config set")

try:
    db = SQLAlchemy(app)
    logging.debug("SQLAlchemy initialized successfully")
except Exception as e:
    logging.error("SQLAlchemy init failed!")
    logging.error(traceback.format_exc())
    raise

# ── MODELS ──
logging.debug("Defining models...")
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    task = db.Column(db.Text, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    name = db.Column(db.String(255))
    product = db.Column(db.String(255))
    price = db.Column(db.Numeric(10,2))

logging.debug("Models defined")

# ── ERROR HANDLERS ──
@app.errorhandler(500)
def server_error(e):
    tb = traceback.format_exc()
    logging.error("500 Error: " + str(e))
    logging.error(tb)
    return render_template('error.html', error=str(e), traceback=tb), 500

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error="Page not found", traceback=None), 404

# ── HEALTH CHECK ROUTE (very important for debugging) ──
@app.route("/health")
def health():
    logging.info("Health check requested")
    try:
        with db.engine.connect() as connection:
            connection.execute("SELECT 1")
        return "OK - App running and DB connected", 200
    except Exception as e:
        logging.error("Health check DB fail: " + str(e))
        return f"ERROR - {str(e)}", 500

# ── INIT ROUTE ──
@app.route("/init")
def init_db():
    logging.info("Init route called")
    try:
        db.create_all()
        logging.info("Tables created")
        return "✅ Tables created successfully!"
    except Exception as e:
        logging.error("Init failed: " + str(e))
        return f"Error: {str(e)}", 500

# ── Other routes (same as before) ──
@app.route("/")
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    logging.debug("Signup route accessed")
    # ... your existing signup code ...
    # (keep your current implementation)

@app.route("/login", methods=["GET", "POST"])
def login():
    logging.debug("Login route accessed")
    # ... your existing login code ...

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
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
    # ... your existing tasks code ...

@app.route("/orders", methods=["GET", "POST"])
def orders():
    # ... your existing orders code ...

logging.debug("All routes registered")
logging.debug("=== APP.PY LOADING COMPLETE ===")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
