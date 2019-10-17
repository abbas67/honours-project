import datetime, string, random, urllib.parse, pyodbc
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import urllib.parse

app = Flask(__name__)

conn = pyodbc.connect("DRIVER={SQL Server};Server=tcp:honoursdbserver.database.windows.net,1433;Database=HonoursProjectDB;Uid=alawal98;Pwd=Hazard1998;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;")
cursor = conn.cursor()

@app.route("/")
@app.route("/Home")
def index():
    return render_template('homepage.html')


@app.route("/lecturesignin")
def lecturesignin():
    date = datetime.datetime.now()

    #uses template from https://bootsnipp.com/snippets/vl4R7
    return render_template('lecturesignin.html', date=date)


@app.route("/genCode")
def codedisplay():

    return render_template('genCode.html', code=generatenewcode())


def generatenewcode():

    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))


if __name__ == "__main__":
    app.run(host='0.0.0.0', threaded=True)
