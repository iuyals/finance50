import os
from datetime import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import sys
from sqlalchemy import Column, ForeignKey, Integer, String,Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base=declarative_base()
class User(Base):
    __tablename__="users"
    id=Column(Integer,primary_key=True,autoincrement=True)
    username=Column(String(250),nullable=False)
    hash=Column(String(250),nullable=False)
    cash=Column(Float,default=10000)

class Shares(Base):
   __tablename__="shares"
   name=Column(String(250),nullable=False)
   number=Column(Integer,default=0)
   owerid=Column(Integer)
   id=Column(Integer,primary_key=True,autoincrement=True)
   price=Column(Float,default=0)

class History(Base):
    __tablename__="history"
    symbol=Column(String(250),nullable=False)
    owener_id=Column(Integer)
    price=Column(Float)
    shares=Column(Integer)
    transacted=Column(String(250),default=str(datetime.now()))
    id=Column(Integer,primary_key=True,autoincrement=True)

engine = create_engine('sqlite:///finance.db')
Base.metadata.bind=engine
DBSession = sessionmaker(bind = engine)
dbsession = DBSession()

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
    user=dbsession.query(User).filter_by(id=session["user_id"])
    cash=user[0].cash
    cash=usd(cash)
    usershares = dbsession.query(Shares).filter_by(owerid=session["user_id"])

    tableContent=[]
    for ashare in usershares:
        tableContent.append( [ashare.name,ashare.name,str(ashare.number),usd(ashare.price),usd(ashare.price*ashare.number)] )
    return render_template("index.html",tableContent=tableContent,cash=cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method=="GET":
        return render_template("buy.html")
    symbol=request.form.get("symbol")
    shares=request.form.get("shares")
    if not symbol or not shares:
        return apology("please input correct share symbol and number")
    try:
        shares=int(shares)
    except:
        return apology("input corect shares")
    if shares<=0:
        return apology("please input positive number")
    info=lookup(symbol)
    if not info:
        return apology("no such symbol")
    user=dbsession.query(User).filter_by(id=session["user_id"])[0]
    usershares=dbsession.query(Shares).filter_by(owerid=session["user_id"])

    #check if enough cash
    leftcash=user.cash-info["price"]*shares
    if leftcash<0:
        return apology("u need more cash to buy these")
    user.cash=leftcash
    dbsession.commit()
    history=History()
    history.owener_id=session["user_id"]
    history.shares=shares
    history.price=info["price"]
    history.symbol=info["symbol"]
    dbsession.add(history)
    dbsession.commit()
    for ashare in usershares:
        print("*****two name***",ashare.name,symbol)

        if ashare.name.lower()==symbol.lower():
            print("****not new share*****")
            ashare.number+=shares
            dbsession.add(user)
            dbsession.add(ashare)
            dbsession.commit()
            return redirect("/")
    print("****new cash****")
    newshare=Shares()
    newshare.name=info["symbol"]
    newshare.price=info["price"]
    newshare.owerid=session["user_id"]
    newshare.number=shares
    dbsession.add(newshare)
    dbsession.commit()

    return redirect("/")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    username=request.args.get("username")
    print("****username:**",username)
    try:
        auser=dbsession.query(User).filter_by(username=username)[0]
        return "false"
    except:
        return "true"


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    tableContent=[]
    history=dbsession.query(History).filter_by(owener_id=session["user_id"])
    print("****history: ",history[0])
    for row in history:
        tableContent.append([ row.symbol,row.shares,row.price,row.transacted ])
        print("***row:",row,type(row))
    return render_template("history.html",tableContent=tableContent)


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
            print("***WrongpassWWWWDDDD")
            return apology("invalid username and/or password", 403)
        print("*****NNNNIIIICCCCDEEEEE")
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        print("***rows***",rows)
        type(rows)
        rows

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
    companyName=''
    money=''
    if request.method=="GET":
        sendMethod="get"
    else:
        sendMethod="post"
        if not request.form.get("symbol"):
            return apology("input symbol")
        symbol=request.form.get("symbol")
        info=lookup(symbol)
        if info is None:
            return apology("invalid symbol")
        companyName=info["name"]
        money=usd(info["price"])

    """Get stock quote."""
    return render_template("quote.html",companyName=companyName,money=money,sendMethod=sendMethod)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method=="GET":
        return render_template("register.html")
    print("****1")
    username=request.form.get("username")
    password=request.form.get("password")
    confirmation=request.form.get("confirmation")
    if not username or not password or not confirmation:
        return apology("wrong name or pw")

    if not password==confirmation:
        return apology("input password again")
    print("***2")
    try:
        auser=dbsession.query(User).filter_by(username=username)[0]
        return apology("the name used,select another")
    except:
        print("****name pass confo***",username,password,confirmation)
        newuser=User(username=username,hash=generate_password_hash(password))
        dbsession.add(newuser)
        dbsession.commit()
        return apology("you have registered :>",code=200)



@app.route("/sell", methods=["GET", "POST"])
#@login_required
def sell():
    """Sell shares of stock"""
    symbols=[]
    usershares = dbsession.query(Shares).filter_by(owerid=session["user_id"])
    for ashare in usershares:
        symbols.append(ashare.name)
    if request.method=="GET":
        return render_template("sell.html",symbols=symbols)

    symbol=request.form.get("symbol")
    shares=request.form.get("shares")
    if not symbol or not shares:
        return apology("please input correct value")

    shares=int(shares)
    if shares<=0:
        return apology("please input positive number")
    info=lookup(symbol)
    user=dbsession.query(User).filter_by(id=session["user_id"])[0]
    leftcash=user.cash+info["price"]*shares
    if leftcash<0:
        return apology("u need more cash to buy these")
    user.cash=leftcash
    dbsession.commit()
    info=lookup(symbol)
    history=History()
    history.owener_id=session["user_id"]
    history.shares=-shares
    history.price=info["price"]
    history.symbol=info["symbol"]
    dbsession.add(history)
    dbsession.commit()
    for ashare in usershares:
        if ashare.name==symbol:
            ashare.number-=shares
            if ashare.number<0:
                return apology("you dont have enought share to sell")
            elif ashare.number==0:
                dbsession.delete(ashare)
                dbsession.commit()
            else:
                dbsession.add(ashare)
                dbsession.commit()
    return redirect("/")
    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


Base.metadata.create_all(engine)
