from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///Treehole.db")

# create a table for all the stocks information if doesn't exist yet
db.execute("CREATE TABLE IF NOT EXISTS user (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)")

# another table to keep track of transactions for history, if doesn't exist yet
db.execute("CREATE TABLE IF NOT EXISTS post (id INTEGER PRIMARY KEY AUTOINCREMENT, author_id INTEGER NOT NULL, created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, title TEXT NOT NULL, body TEXT NOT NULL, FOREIGN KEY (author_id) REFERENCES user (id))")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
def hello():
    return render_template("hello.html")

@app.route("/index",methods=["GET", "POST"])
@login_required
def index():
    """Show posts"""
    post = db.execute("SELECT created, title, body FROM post")
    comments = db.execute("SELECT content FROM comment")

    # Render
    return render_template("index.html", post=post)


@app.route("/comment",methods=["GET", "POST"])
@login_required
def comment():
    # bring user to this page via GET
    if request.method == "GET":
        return render_template("index.html")
    # get info from POST
    elif request.method == "POST":
        user_id = session["user_id"]
        content = request.form.get("reply")
        # how to get post id?

        db.execute("INSERT INTO comment (author_id, content, ) VALUES (?, ?)", user_id, content,)



@app.route("/history")
@login_required
def history():
    # pass in info from post
    user_id = session["user_id"]
    title = db.execute("SELECT title FROM post WHERE author_id = ?", user_id)
    body = db.execute("SELECT body FROM post WHERE author_id = ?", user_id)
    created = db.execute("SELECT created FROM post WHERE author_id = ?", user_id)
    return render_template("history.html", title=title, body=body, created=created)

@app.route("/seekhelp")
@login_required
def seekhelp():
    return render_template("seekhelp.html")


@app.route("/post", methods=["GET", "POST"])
@login_required
def post():
    # bring user to this page via GET
    if request.method == "GET":
        return render_template("post.html")
    # get info from POST
    elif request.method == "POST":
        user_id = session["user_id"]
        title = request.form.get("title")
        body = request.form.get("body")
        db.execute("INSERT INTO post (author_id, title, body) VALUES (?, ?, ?)", user_id, title, body)
        # store users' posts in a list
        user_posts = []
        user_post = request.form.get("post")
        user_title = request.form.get("")
        user_posts = user_posts.append(user_post)

        return redirect("/")




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
        return redirect("/index")

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


# this is my personal touch


@app.route("/reset_password", methods=["GET", "POST"])
@login_required
def reset_password():
    # bring user to this page via GET
    if request.method == "GET":
        return render_template("reset_password.html")
    # get info from POST
    elif request.method == "POST":
        user_id = session["user_id"]
        original_password = request.form.get("original_password")
        new_password = request.form.get("new_password")
        new_password1 = request.form.get("new_password1")
        # get user info and check if things match
        rows = db.execute("SELECT * FROM user WHERE id = ?", user_id)
        if not check_password_hash(rows[0]["password"], original_password):
            return apology("Please enter correct original password", 400)
        # render apology if new passwords don't match
        elif new_password != new_password1:
            return apology("New passwords don't match", 400)
        # render apology if either new password inputs is empty
        elif new_password == '' or new_password1 == '':
            return apology("Please enter new password", 400)
        # otherwise generate a hash for new password and update the table
        else:
            hash = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=8)
            db.execute("UPDATE user SET password = ? WHERE id = ?", hash, user_id)
            return render_template("reset_password_success.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

