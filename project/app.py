import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from project.helpers import apology, login_required, lookup, usd

from datetime import datetime

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# create a table for all the stocks information if doesn't exist yet
db.execute("CREATE TABLE IF NOT EXISTS stocks(user_id INTEGER, symbol TEXT NOT NULL, name TEXT NOT NULL, shares INTEGER, price INTEGER, total INTEGER)")

# another table to keep track of transactions for history, if doesn't exist yet
db.execute("CREATE TABLE IF NOT EXISTS transactions(user_id INTEGER, symbol TEXT NOT NULL, shares INTEGER, price INTEGER, transacted TEXT NOT NULL)")


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
    """Show portfolio of stocks"""
    # get info from session and tables
    user_id = session["user_id"]
    stocks = db.execute("SELECT * FROM stocks WHERE user_id = ?", user_id)
    users = db.execute("SELECT * FROM users WHERE id = ?", user_id)
    # this is to account for the situation where the table is empty (there is no information from any user)
    if len(stocks) == 0:
        total = 0
    # else we can get everything we need to display from the database, and turn them into the right format (two decimals)
    else:
        total = float(db.execute("SELECT total FROM stocks WHERE user_id = ?", user_id)[0]["total"])
    cash = float(db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"])
    displayed_total = ("%.2f" % total)
    net_total = ("%.2f" % (total + cash))
    cash = ("%.2f" % cash)
    return render_template("index.html", stocks=stocks, net_total=net_total, cash=cash, displayed_total=displayed_total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # getting it just directs them to this page
    if request.method == "GET":
        return render_template("buy.html")
    # get the information the user put in from the POST request
    elif request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        # render error if nothing is typed in
        if symbol == None or shares == None:
            return apology("Please don't leave an area blank", 400)
        # get only integers, render apology if not (this didn't work for some reason T.T)
        # source: https://www.kite.com/python/answers/how-to-check-if-a-variable-is-a-certain-type-in-python#:~:text=Use%20isinstance()%20to%20check,instance%20of%20the%20class%20type%20.
        elif shares.isdigit() == False:
            return apology("Please enter integer for shares", 400)
        # get the stock information from lookup function
        else:
            quote = lookup(symbol)
            if quote != None:
                user_id = session["user_id"]
                price = quote["price"]
                companyname = quote["name"]
                # calculate the total that they want to buy and compare it with cash
                total = price * float(shares)
                cash = float(db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"])
                # if they don't have enough money to buy desired shares, render apology
                if total > cash:
                    return apology("Insufficient funds", 400)
                # this situaion is for where the user don't have this company's shares yet
                elif len(db.execute("SELECT * FROM stocks WHERE name = ? AND user_id = ?", companyname, user_id)) == 0:
                    db.execute("INSERT INTO stocks (user_id, symbol, name, shares, price, total) VALUES (?, ?, ?, ?, ?, ?)",
                               user_id, symbol, companyname, shares, price, total)
                    cash = cash - total
                    db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, user_id)
                    # this is for history
                    # source:https://thispointer.com/python-how-to-get-current-date-and-time-or-timestamp/
                    timestamp = str(datetime.now())
                    shares_count = str("+" + str(shares))
                    db.execute("INSERT INTO transactions (user_id, symbol, shares, price, transacted) VALUES (?, ?, ?, ?, ?)",
                               user_id, symbol, shares_count, price, timestamp)
                # this situation is for if the row for that company's shares already exists for that user
                else:
                    db.execute("UPDATE stocks SET shares = shares + ?, total = total + ? WHERE name = ? AND user_id = ?",
                               shares, total, companyname, user_id)
                    cash = cash - total
                    db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, user_id)
                    # this is for history
                    timestamp = str(datetime.now())
                    shares_count = str("+" + str(shares))
                    db.execute("INSERT INTO transactions (user_id, symbol, shares, price, transacted) VALUES (?, ?, ?, ?, ?)",
                               user_id, symbol, shares_count, price, timestamp)
            # if quote is none
            else:
                return apology("Invalid symbol", 400)
    return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # we just pass in the transactions table. It is already updated everywhere else
    user_id = session["user_id"]
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = ?", user_id)
    return render_template("history.html", transactions=transactions)


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # bring the user to the page via GET
    if request.method == "GET":
        return render_template("quote.html")
    # get all the info that we need from POST
    elif request.method == "POST":
        symbol = request.form.get("symbol")
        # use the lookup function to look up info we need
        quote_dict = lookup(symbol)
        if quote_dict != None:
            print("A share of " + quote_dict["name"] + " (" + quote_dict["symbol"] + ") " +
                  "costs $" + str(quote_dict["price"]) + ".")
            return render_template("quote_result.html", quote_dict=quote_dict)
        else:
            return apology("invalid symbol", 400)


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
            rows = db.execute("SELECT * FROM users WHERE username = ?", username)
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
                db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)
    return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # bring the user to the page via GET, and get user_id from session
    user_id = session["user_id"]
    if request.method == "GET":
        stocks = db.execute("SELECT symbol FROM stocks WHERE user_id = ?", user_id)
        return render_template("sell.html", stocks=stocks)
    # get all the info we need from POST
    elif request.method == "POST":
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        # render apology if symbol isn't chosen
        if symbol == "Symbol":
            return apology("Please choose a stock", 400)
        else:
            # then get info we need from the table
            stocks = db.execute("SELECT * FROM stocks WHERE user_id = ?", user_id)
            cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
            owned_shares = int(
                (db.execute("SELECT shares FROM stocks WHERE user_id = ? AND symbol = ?", user_id, symbol))[0]["shares"])
            # render apology if owned shares is less than shares
            if owned_shares < shares:
                return apology("You don't have enough shares to sell", 400)
            # otherwise update owned shares
            else:
                owned_shares = owned_shares - shares
                # if user doesn't have shares for that company anymore, delete row altogether
                if owned_shares == 0:
                    db.execute("DELETE FROM stocks WHERE symbol = ? AND user_id = ?", symbol, user_id)
                # otherwise update info in table
                else:
                    db.execute("UPDATE stocks SET shares = ? WHERE symbol = ? AND user_id = ?", owned_shares, symbol, user_id)
                quote = lookup(symbol)
                price = quote["price"]
                # this is for history
                timestamp = str(datetime.now())
                shares_count = str("-" + str(shares))
                db.execute("INSERT INTO transactions (user_id, symbol, shares, price, transacted) VALUES (?, ?, ?, ?, ?)",
                           user_id, symbol, shares_count, price, timestamp)
                # calculate total and cash and pass them into table
                total = owned_shares * float(price)
                cash = float(db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"])
                db.execute("UPDATE stocks SET total = ? WHERE user_id = ? AND symbol = ?", total, user_id, symbol)
                cash = ("%.2f" % (cash + total))
                db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, user_id)
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
        rows = db.execute("SELECT * FROM users WHERE id = ?", user_id)
        if not check_password_hash(rows[0]["hash"], original_password):
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
            db.execute("UPDATE users SET hash = ? WHERE id = ?", hash, user_id)
            return render_template("reset_password_success.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
