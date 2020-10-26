import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_data_rows=db.execute("SELECT symbol,price,name,shares,price,total From user_data where user_id =:id",id=session['user_id'])
    user = db.execute("SELECT cash FROM users WHERE id = :id",id=session["user_id"])
    total = user[0]['cash']
    for data in user_data_rows:
        total += data['total']

    data=[user[0],user_data_rows,total]
    # flash(total)

    return render_template('index.html',data= data)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        if symbol == None:
            flash("Symbol is not defined")
            return redirect(url_for('buy'))
        if shares == None or int(shares) < 0 or (not shares.isdigit()):
            flash("Shares field blank or shares is not a positive integer")
            return redirect(url_for('buy'))
        stock = lookup(symbol)
        if stock == None:
            flash("Stock is not valid one!")
            return redirect(url_for('buy'))
        rows_user = db.execute("SELECT cash FROM users WHERE id = :id",id=session["user_id"])
        cash = rows_user[0]['cash']
        updated_cash = cash - int(shares)*stock["price"]
        if updated_cash < 0 :
            flash("You can not afford")
            return redirect(url_for('buy'))
        user_old_shares =db.execute("Select id,symbol,shares From user_data Where user_id= :id",id=session['user_id'])
        user_data_id = None
        for usr_old_share in user_old_shares:
            if usr_old_share['symbol'] == symbol:
                user_data_id = usr_old_share["id"]
                user_data_old_shares = usr_old_share["shares"]
                break

        if  user_data_id == None:
            prim_key = db.execute("Insert into user_data (user_id,symbol, name,shares,price,total) VALUES(:user_id, :symbol,:name,:shares,:price,:total)",user_id= session["user_id"],symbol=stock["symbol"],name=stock['name'],shares=int(shares),price=stock['price'],total=stock['price']*int(shares))
        else:
            price = stock["price"]
            total_share = user_data_old_shares + int(shares)
            new_total = price*total_share
            prim_key=db.execute("Update user_data set shares = :shares,price=:price,total=:total Where id = :id",shares=total_share,price= price,total= new_total,id=user_data_id)

        if prim_key  == None:
            flash(f"Error in buying  shares of {stock['name']}  and price of shares {stock['price']}")
            return redirect(url_for('buy'))
        db.execute("Update users set cash= :cash where id = :id ",cash=updated_cash,id=session["user_id"])
        
        #save data history
        db.execute("Insert into history (user_id,symbol,shares,price) VALUES(:user_id, :symbol,:shares,:price)",user_id= session["user_id"],symbol=stock["symbol"],shares=int(shares),price=stock['price'])

        flash(f"Shares bought successfully")

        return redirect(url_for('index'))


    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("Select * From history Where user_id=:id",id=session['user_id'])
    return render_template('history.html',history=history)


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

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
    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("symbol")
        if not  symbol:
            flash("Symbol is blink!")
            return redirect(url_for('quote'))
        stock = lookup(symbol.upper())
        if stock == None:
            flash("Symbol is invalid!")
            return redirect(url_for('quote'))

        #else return stock
        return render_template("quoted.html",stock=stock)



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if password != confirmation :
            flash('Password are not same!!!')
            return redirect(url_for('register'))
        if len(username) <= 0 or len(password)<=0 or len(confirmation) <=0:
            flash("Input field is empty")
            return redirect(url_for('register'))
        # Query database for username
        prim_key = db.execute("Insert into users(username,hash) VALUES( :username, :hash)", username =username, hash=generate_password_hash(password))
        if prim_key == None:
            flash("Registration error , Check if username is already exists")
            return redirect(url_for('register'))
        session["user_id"] = prim_key
        flash("Account is created successfully!")
        return redirect(url_for('login'))

    return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        try:
            share_num = int(request.form.get("shares"))

        except:
            flash("Share is not defined")
            return redirect(url_for('sell'))
        if symbol == None :
            flash("Symbol is not defined")
            return redirect(url_for('sell'))
        # pair =[symbol, share]

        stock = lookup(symbol)
        present_price = stock['price']
        my_share = db.execute("Select id ,shares,symbol From user_data Where user_id=:id",id =session["user_id"])
        user = db.execute("Select cash From users where id = :id",id=session['user_id'])
        cash = user[0]['cash']


        for share in my_share:
            if share['symbol'] == symbol: # symbol which user want to sell
                sell_id = share["id"]
                usr_share = share['shares']
                if share_num > share["shares"]:
                    flash("Your share is less than You wanted to sell")
                    return redirect(url_for('sell'))
                break
        #share selled
        remaining_share = usr_share - share_num

        updated_cash = cash + present_price*share_num

        #upadate cash in db
        db.execute("Update users set cash= :cash where id = :id ",cash=updated_cash,id=session["user_id"])
        #update in user_data after sell of share
        if remaining_share > 0:
            db.execute("Update user_data set shares = :shares,price=:price,total=:total Where id = :id",shares=remaining_share,price= present_price,total= remaining_share*present_price,id=sell_id)
        else:
            db.execute("Delete From user_data Where id=:id",id= sell_id)
        db.execute("Insert into history (user_id,symbol,shares,price) VALUES(:user_id, :symbol,:shares,:price)",user_id= session["user_id"],symbol=stock["symbol"],shares=-share_num,price=stock['price'])

        flash(f"{share_num} share is successfully sold")
        return redirect(url_for('index'))
    user_data =db.execute("Select symbol From user_data where user_id= :id",id =session["user_id"])


    return render_template("sell.html", user_data=user_data)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
