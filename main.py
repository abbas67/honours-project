import datetime,sys, json, string, random
from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_heroku import Heroku

app = Flask(__name__)
Bootstrap(app)


@app.route("/")
@app.route("/home")
def index():
    date = datetime.datetime.now()
    return render_template('home.html', date=date)


@app.route("/genCode")
def codedisplay():

    return render_template('genCode.html', code=generatenewcode())


def generatenewcode():

    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))


