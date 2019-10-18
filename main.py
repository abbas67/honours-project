import datetime
import random
import urllib
import pyodbc
import string
import sqlalchemy as db
from sqlalchemy import select, MetaData, Table
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

metadata = MetaData(bind=None)

params = urllib.parse.quote_plus("Driver={ODBC Driver 13 for SQL Server};Server=tcp:honoursdbserver.database.windows.net,1433;Database=HonoursProjectDB;Uid=alawal98;Pwd=Hazard1998;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;")
engine = db.create_engine("mssql+pyodbc:///?odbc_connect=%s" % params)

metadata = MetaData(bind=None)

table = Table('Students', metadata, autoload=True, autoload_with=engine)
print("this is a problem")
stmt = select([table]).where(table.columns.FirstName == 'JOHN')

connection = engine.connect()

results = connection.execute(stmt).fetchall()


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


@app.route("/signedin")
def confirmsignin():

    return render_template('signedin.html')


@app.route("/login", methods=['POST'])
def login():

    matriculationnumber = request.form['MatriculationNumber']
    password = request.form['Password']
    lecturecode = request.form['LectureCode']

    engine = db.create_engine("mssql+pyodbc:///?odbc_connect=%s" % params)
    table = Table('Students', metadata, autoload=True, autoload_with=engine)
    stmt = select([table]).where(table.columns.MatricNum == matriculationnumber)

    connection = engine.connect()
    rows = connection.execute(stmt).fetchall()
    print("please")

    list_of_dicts = [{key: value for (key, value) in row.items()} for row in rows]

    error = None

    if len(list_of_dicts) != 1:
        error = "Matriculation Number or password is incorrect"
        print("yaaaas")
        return render_template('lecturesignin.html', error=error)


    if checkpass(list_of_dicts[0], password) and checklecturecode(lecturecode):
        print("yaaaas")
        return render_template('signedin.html')

    else:
        error = "Wrong Password or Lecture Code"
        return render_template('lecturesignin.html', error=error)


def checkpass(user, possiblepassword):

    if user['Password'] == possiblepassword:
        return True
    else:
        return False


def checklecturecode(lecturecode):

    table = Table('Lectures', metadata, autoload=True, autoload_with=engine)
    stmt = select([table]).where(table.columns.LectureID == lecturecode)

    connection = engine.connect()
    rows = connection.execute(stmt).fetchall()

    list_of_dicts = [{key: value for (key, value) in row.items()} for row in rows]

    print(list_of_dicts)

    if len(list_of_dicts) != 1 :
        return False
    else:
        return True


if __name__ == "__main__":
    app.run(host='0.0.0.0', threaded=True)
