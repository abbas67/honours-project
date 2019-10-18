import datetime
import random
import pandas as pd
import urllib
import itertools
import pyodbc
import string
import sqlalchemy as db
from sqlalchemy import select, MetaData, Table
from flask import Flask, render_template, request, redirect, url_for
import platform

from sqlalchemy.dialects.mssql.information_schema import columns

app = Flask(__name__)

metadata = MetaData(bind=None)

drivers = [item for item in pyodbc.drivers()]
driver = drivers[-1]
server = 'tcp:honoursdbserver.database.windows.net,1433'
database = 'HonoursProjectDB'
uid = 'alawal98'
pwd = 'Hazard1998'

params = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}'
conn = pyodbc.connect(params)
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


@app.route("/signedin")
def confirmsignin():

    return render_template('signedin.html')


@app.route("/login", methods=['POST'])
def login():

    matriculationnumber = request.form['MatriculationNumber']
    password = request.form['Password']
    lecturecode = request.form['LectureCode']

    query = "SELECT * FROM Students WHERE MatricNum=?"

    result = pd.read_sql(query, conn, params=(matriculationnumber,))
    studentinfo = result.to_dict('records')
    print(studentinfo)

    error = None

    if len(studentinfo) != 1:
        error = "Matriculation Number or password is incorrect"
        return render_template('lecturesignin.html', error=error)

    query = "SELECT * FROM Lectures WHERE LectureID=?"
    result = pd.read_sql(query, conn, params=(lecturecode,))
    lectureinfo = result.to_dict('records')
    print(lectureinfo[0])

    if checkpass(studentinfo[0], password) is True and len(lectureinfo) is 1:

        return render_template('signedin.html', lecturedata=lectureinfo[0])

    else:
        error = "Wrong Password or Lecture Code"
        return render_template('lecturesignin.html', error=error)


def checkpass(user, possiblepassword):

    if user['Password'] == possiblepassword:
        return True
    else:
        return False


if __name__ == "__main__":
    app.run(host='0.0.0.0', threaded=True)
