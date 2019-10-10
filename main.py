import datetime
from flask import Flask, render_template
from flask_bootstrap import Bootstrap

app = Flask(__name__)
Bootstrap(app)

@app.route("/")
@app.route("/home")
def index():
    date = datetime.datetime.now()
    return render_template('home.html', date=date)


@app.route("/about")
def about():

    return "about"



