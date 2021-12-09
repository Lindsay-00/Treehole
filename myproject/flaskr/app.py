import os

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from myproject.flaskr.helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# # Custom filter
# app.jinja_env.filters["usd"] = usd

# Configure session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///treehole.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show posts"""
    # get info from session and tables
    user_id = session["user_id"]
    title = db.execute("SELECT title FROM post WHERE user_id = ?", user_id)
    body = db.execute("SELECT body FROM post WHERE user_id = ?", user_id)
    created = db.execute("SELECT created FROM users WHERE id = ?", user_id)

    # Render portfolio
    return render_template("index.html", title=title, body=body, created=created)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM user WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # bring the user to the page via GET
    if request.method == "GET":
        return render_template("register.html")
    # get all the info that we need from POST
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # render apology if nothing is typed in for username
        if username == '':
            return apology("Please enter a username", 400)
        # check if username already exists
        else:
            rows = db.execute("SELECT * FROM user WHERE username = ?", username)
            if len(rows) != 0:
                return apology("Username already exists", 400)
            # check if passwords match
            elif password != confirmation:
                return apology("Passwords don't match", 400)
            # render apology if nothing is typed in for username
            elif password == '' or confirmation == '':
                return apology("Please enter password", 400)
            # store user info into table if nothing is wrong
            else:
                hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
                db.execute("INSERT INTO user (username, password) VALUES (?, ?)", username, hash)
    return redirect("/")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

#to make posts
@app.route("/saysomething", methods=["GET", "POST"])
def saysomething():
    # store users' posts in a list
    user_posts = []
    user_post = request.form.get("post")
    user_posts = user_posts.append(user_post)

    return redirect("/")