from flask import Flask,render_template,session,redirect,request
from flask_debug import Debug
from livereload import Server
from functools import wraps
from datetime import timedelta
import pymongo
app = Flask(__name__)
app.secret_key = b'~\x15\xcc-,\xa8:`\xa7IQ\xcc\xaa\xdbA?'
app.permanent_session_lifetime = timedelta(days=7)
#decorators
# @app.before_request
# def before_request():
#     print("I am before_request")
#     for key,value in session.items():
#         print(key,value)
def login_required(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            return redirect("/")
    return wrap
#database
client = pymongo.MongoClient('localhost',27017)
db = client.user_login_system
#routes
from user import routes
@app.route("/")
def home():
    return render_template('home.html')
@app.route("/dashboard/")
@login_required
def dashboard():
    return render_template('dashboard.html')

app.run()
