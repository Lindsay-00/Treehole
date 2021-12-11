from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta

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

# create a table for all the user information if doesn't exist yet
db.execute("CREATE TABLE IF NOT EXISTS user (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)")

# another table to keep track of posts, if doesn't exist yet
db.execute("CREATE TABLE IF NOT EXISTS post (id INTEGER PRIMARY KEY AUTOINCREMENT, author_id INTEGER NOT NULL, created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, title TEXT NOT NULL, body TEXT NOT NULL, FOREIGN KEY (author_id) REFERENCES user (id))")

# another table to keep track of comments, if doesn't exist yet
db.execute("CREATE TABLE IF NOT EXISTS comment (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, author_id INTEGER NOT NULL, post_id INTEGER NOT NULL)")

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


@app.route("/index", methods=["GET", "POST"])
# @login_required
def index():
    # prompt for login if haven't done so
    if len(session) == 0:
        return redirect("/login")
    # if already logged in
    else:
        """Show posts & comments"""
        post = db.execute("SELECT post_id, created, title, body FROM post")
        comment = db.execute("SELECT post_id, content FROM comment")

        # below is the timer function to delete posts automatically after designated time
        timestamps = db.execute("SELECT created, post_id FROM post")
        for each in timestamps:
            timestamp = each["created"]
            post_id = each["post_id"]
            # seems like something could be simplified here
            # from python manual https://docs.python.org/3/library/datetime.html
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            start = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S')
            difference = end - start
            if difference > timedelta(hours=100):
                db.execute("DELETE FROM post WHERE post_id = ?", post_id)
                db.execute("DELETE FROM comment WHERE post_id = ?", post_id)

        return render_template("index.html", post=post, comment=comment)



@app.route("/comment", methods=["GET", "POST"])
@login_required
def comment():
    # bring user to this page via GET
    if request.method == "GET":
        return render_template("index.html")
    # get info from POST
    elif request.method == "POST":
        # get info to be added to database; credit to TA Kelly Chen '23 for help on getting the specific post id's using multidict key selector
        post_id = list(request.form.keys())[1]
        user_id = session["user_id"]
        content = request.form.get("reply")
        db.execute("INSERT INTO comment (author_id, content, post_id) VALUES (?, ?, ?)", user_id, content, post_id)
    return redirect("/index")


@app.route("/history")
@login_required
def history():
    # pass in info from post
    user_id = session["user_id"]
    post = db.execute("SELECT created, title, body, post_id FROM post WHERE author_id = ?", user_id)
    return render_template("history.html", post=post)


# added delete post function
@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    # bring user to this page via GET
    if request.method == "GET":
        return render_template("history.html")
    # get info from POST
    elif request.method == "POST":
        print(list(request.values.keys()))
        post_id = list(request.form.keys())[1]
        db.execute("DELETE FROM post WHERE post_id = ?", post_id)
        db.execute("DELETE FROM comment WHERE post_id = ?", post_id)
    return redirect("/history")


# edit post function
@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    # bring user to this page via GET
    post_id = 0
    if request.method == "GET":
        print(list(request.values.keys()))
        # post_id = list(request.args.keys())[1]
        return render_template("edit.html")
    # get info from POST
    elif request.method == "POST":
        # post = db.execute("SELECT created, title, body FROM post WHERE post_id = ?", post_id)
        # render_template("edit.html", post=post)
        body = request.form.get("body")
        title = request.form.get("title")
        db.execute("UPDATE post SET title = ?, body = ? WHERE post_id = ?", title, body, post_id)

    return redirect("/history")


@app.route("/seekhelp")
@login_required
def seekhelp():
    # show seekhelp page
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
        # return apology if title or post body is empty
        if not request.form.get("title") or not request.form.get("body"):
            return apology("Empty title or body", 403)
        # else insert the info into the post table
        else:
            title = request.form.get("title")
            body = request.form.get("body")
            db.execute("INSERT INTO post (author_id, title, body) VALUES (?, ?, ?)", user_id, title, body)
            # store users' posts in a list
            # user_posts = []
            # user_post = request.form.get("post")
            # user_title = request.form.get("title")
            # user_posts = user_posts.append(user_post)
        return redirect("/index")


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

