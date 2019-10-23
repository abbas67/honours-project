import datetime
import random
import pandas as pd
import pyodbc
import string
from sqlalchemy import select, MetaData, Table
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)

app.secret_key = "supersecretkey"

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



@app.route("/lecturersigninpage")
def lecturersigninpage():

    return render_template('lecturersignin.html')


@app.route("/lecturersignin", methods=['POST'])
def lecturersignin():

    lecturerid = request.form['lecturerid']
    password = request.form['Password']

    query = "SELECT * FROM Lecturers WHERE LecturerID=?"

    result = pd.read_sql(query, conn, params=(lecturerid,))
    lecturerinfo = result.to_dict('records')
    print(lecturerinfo)

    error = None

    if len(lecturerinfo) != 1:
        error = "LecturerID or password is incorrect"
        return render_template('lecturersignin.html', error=error)

    if checkpass(lecturerinfo[0], password) is True:

        return redirect(url_for('lectureman'))

    else:
        error = "LecturerID or password is incorrect"
        return render_template('lecturersignin.html', error=error)





@app.route("/lecturemanagement")
def lectureman():

    query = "SELECT * FROM Modules"

    result = pd.read_sql(query, conn)
    moduleinfo = result.to_dict('records')
    print(moduleinfo)


    return render_template('createlecture.html', modules=moduleinfo)


@app.route("/lecturesignin")
def lecturesignin():
    date = datetime.datetime.now()

    #uses template from https://bootsnipp.com/snippets/vl4R7
    return render_template('lecturesignin.html', date=date)


@app.route("/createlecture", methods=['GET', 'POST'])
def createlecture():

    time = request.form['time']
    duration = request.form['duration']
    name = request.form['name']
    location = request.form['location']
    module = request.form['module']
    weekday = request.form['weekday']
    first = request.form['first']
    first = int(first)
    last = request.form['last']
    last = int(last)

    for x in range (first, last + 1):

        query = "INSERT INTO Lectures (LectureID, ModuleID, LectureName, LectureLocation, LectureDuration, Week, Day, Time ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"

        cursor.execute(query, (generatenewcode(), module, name, location, duration, x, weekday, time))
        conn.commit()

    flash("Lecture successfully created timetabled." )
    return redirect(url_for('lectureman'))

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
    app.run(host='0.0.0.0', threaded=True, debug=True)
