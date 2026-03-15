from flask import Flask, render_template, request, redirect, session
import database

app = Flask(__name__)
app.secret_key = "supersecretkey"


def get_db():
    return database.connect()


@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
        "SELECT id FROM users WHERE username=%s AND password=%s",
        (username, password)
        )

        user = cur.fetchone()

        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect("/home")

    return render_template("login.html")


@app.route("/signup", methods=["GET","POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
        "INSERT INTO users(username,password) VALUES(%s,%s)",
        (username,password)
        )

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("signup.html")


@app.route("/home")
def home():

    if "user_id" not in session:
        return redirect("/")

    return render_template("home.html")


@app.route("/tasks", methods=["GET","POST"])
def tasks():

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    user = session["user_id"]

    if request.method == "POST":

        task = request.form["task"]

        cur.execute(
        "INSERT INTO tasks(user_id,task) VALUES(%s,%s)",
        (user,task)
        )

        conn.commit()

    cur.execute(
    "SELECT task FROM tasks WHERE user_id=%s",
    (user,)
    )

    tasks = cur.fetchall()

    conn.close()

    return render_template("tasks.html", tasks=tasks)


@app.route("/orders", methods=["GET","POST"])
def orders():

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    user = session["user_id"]

    if request.method == "POST":

        name = request.form["name"]
        product = request.form["product"]
        price = request.form["price"]

        cur.execute(
        "INSERT INTO orders(user_id,name,product,price) VALUES(%s,%s,%s,%s)",
        (user,name,product,price)
        )

        conn.commit()

    cur.execute(
    "SELECT name,product,price FROM orders WHERE user_id=%s",
    (user,)
    )

    orders = cur.fetchall()

    conn.close()

    return render_template("orders.html", orders=orders)


@app.route("/logout")
def logout():

    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)