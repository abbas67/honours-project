import datetime
import random
import pandas as pd
import pyodbc
import string
import logging
from os import path
import os
from logging import handlers

from flask import Flask, render_template, request, redirect, url_for, flash, session, g, json
import hashlib, binascii, os

app = Flask(__name__)

app.secret_key = "supersecretkey"

logger = logging

drivers = [item for item in pyodbc.drivers()]
driver = drivers[-1]
server = 'Zeno.computing.dundee.ac.uk'
database = 'abbaslawaldb'
uid = 'abbaslawal'
pwd = 'abc2019ABL123..'

params = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}'
conn = pyodbc.connect(params)
cursor = conn.cursor()


@app.before_request
def before_request():

    g. user = None

    if 'user' in session:
        g.user = session['user']


@app.route("/")
@app.route("/Home")
def index():
    return render_template('homepage.html')


@app.route("/lecturerhome")
def lecturerhomepage():

    if g.user:
        return render_template('lecturerhome.html')

    return redirect(url_for('lecturersignin'))


@app.route("/lecturersignin", methods=['POST', 'GET'])
def lecturersignin():

    if request.method == 'POST':
        session.pop('user', None)
        lecturerid = request.form['lecturerid']
        password = request.form['Password']
        query = "SELECT * FROM Lecturers WHERE LecturerID=?"
        result = pd.read_sql(query, conn, params=(lecturerid,))
        lecturerinfo = result.to_dict('records')
        error = None
        if len(lecturerinfo) != 1:
            error = "Account does not exist"
            logger.info("Account does not exist")
            print("failing")
            return render_template('lecturersignin.html', error=error)

        actualpass = lecturerinfo[0]['Password']
        if checkpass(actualpass, password) is True:

            session['user'] = lecturerid
            session['moduleinfo'] = []
            session['lectureinfo'] = []

            query = "SELECT * FROM Modules WHERE LecturerID=?"
            result = pd.read_sql(query, conn, params=(lecturerid,))
            lectureinfo = result.to_dict('records')

            for x in lectureinfo:

                if x['LecturerID'].strip() == session['user']:
                    session['moduleinfo'].append(x['ModuleID'])
                    print("passing")
            logger.info("Successfully Signed In")
            return redirect(url_for('lecturerhomepage'))

        else:
            error = "LecturerID or password is incorrect"
            logger.info("LecturerID or password is incorrect")
            print("failing because password")
            return render_template('lecturersignin.html', error=error)

    else:

        if g.user:
            return redirect(url_for('lecturerhomepage'))

        return render_template('lecturersignin.html')


@app.route("/signup", methods=['POST', 'GET'])
def signup():

    if request.method == 'POST':

        notification = None

        idnum = request.form['idnum']
        password = hash_password(request.form['password'])
        fname = request.form['fname']
        lname = request.form['lname']
        type = request.form['lecturercheck']
        print(idnum, password, fname, lname, type)

        if type == 'Lecturer':

            query = "SELECT * FROM Lecturers WHERE LecturerID=?"
            result = pd.read_sql(query, conn, params=(idnum,))
            resultdict = result.to_dict('records')

            if len(resultdict) > 0:
                notification = "The ID already exists"
                logger.info("The ID already exists, Account Creation failed")
                return render_template('signup.html', notification=notification)

            query = "INSERT INTO Lecturers (LecturerID, FirstName, LastName, Password) VALUES (?, ?, ? ,?);"
            cursor.execute(query, (idnum, fname, lname, password))
            conn.commit()

        notification = "account successfully created"
        logger.info("lecturer account successfully created")

        if type == 'Student':

            query = "SELECT * FROM Students WHERE MatricNum=?"
            result = pd.read_sql(query, conn, params=(idnum,))
            resultdict = result.to_dict('records')

            if len(resultdict) > 0:
                notification = "The ID already exists"
                logger.info("Error, ID already exists")
                return render_template('signup.html', notification=notification)

            if len(idnum) != 9:
                notification = "Please enter a valid matriculation number"
                logger.info("Invalid Matriculation Number")
                return render_template('signup.html', notification=notification)

            query = "INSERT INTO Students (MatricNum, FirstName, LastName, Password) VALUES (?, ?, ? ,?);"
            cursor.execute(query, (idnum, fname, lname, password))
            conn.commit()

        notification = "account successfully created"
        logger.info("Student account successfully created")

        return render_template('signup.html', notification=notification)

    return render_template('signup.html')


@app.route("/createlecture", methods=['GET', 'POST'])
def createlecture():

    if request.method == 'POST':

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

        for x in range(first, last + 1):
            query = "INSERT INTO Lectures (LectureID, ModuleID, LectureName, LectureLocation, LectureDuration, Week, Day, Time ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"

            cursor.execute(query, (generatenewcode(), module, name, location, duration, x, weekday, time))
            conn.commit()

        flash("Lecture successfully timetabled.")
        return redirect(url_for('createlecture'))

    else:

        if g.user:

            query = "SELECT * FROM Modules"

            result = pd.read_sql(query, conn)
            moduleinfo = result.to_dict('records')
            print(moduleinfo)

            return render_template('createlecture.html', modules=moduleinfo)

        return redirect(url_for('lecturersignin'))


@app.route("/modulemanagement", methods=['GET', 'POST'])
def modulemanagement():

    if request.method == 'POST':

        moduleid = request.form['moduleid']
        modulename = request.form['modulename']

        print(moduleid, modulename)
        query = "INSERT INTO Modules(ModuleID, ModuleName, LecturerID) VALUES (?, ?, ?);"
        cursor.execute(query, (moduleid, modulename, session['user']))
        conn.commit()
        updatemanagedmodules()
        return render_template('modulemanager.html', modules=session['supervisedmodules'])

    else:

        if g.user:

            updatemanagedmodules()
            return render_template('modulemanager.html', modules=session['supervisedmodules'])

        return redirect(url_for('lecturersignin'))


def updatemanagedmodules():

    query = "SELECT * FROM Modules WHERE LecturerID=?"
    result = pd.read_sql(query, conn, params=(session['user'],))
    session['supervisedmodules'] = result.to_dict('records')


@app.route("/lecturesignin", methods=['GET', 'POST'])
def lecturesignin():

    if request.method == 'POST':

        matriculationnumber = request.form['MatriculationNumber']
        password = request.form['Password']
        lecturecode = request.form['LectureCode']

        query = "SELECT * FROM Students WHERE MatricNum=?"

        result = pd.read_sql(query, conn, params=(matriculationnumber,))
        studentinfo = result.to_dict('records')
        actualpassword = studentinfo[0]['Password']
        error = None

        if len(studentinfo) != 1:
            error = "Matriculation Number or password is incorrect"
            return render_template('lecturesignin.html', error=error)

        query = "SELECT * FROM Lectures WHERE LectureID=?"
        result = pd.read_sql(query, conn, params=(lecturecode,))
        lectureinfo = result.to_dict('records')

        if len(lectureinfo) != 1:
            error = "Incorrect lecture code, please try again"
            return render_template('lecturesignin.html', error=error)

        if checkpass(actualpassword, password) is True and len(lectureinfo) is 1:

            filename = ('Attendance_Docs/%s.txt' % lecturecode)

            if path.exists(filename):
                with open(filename, 'a') as file:
                    file.write("file does exist bitch")
                    print(studentinfo['MatricNum'] + ' ,' + studentinfo['FirstName'] + studentinfo['LastName'])

            else:

                file = open(filename, 'w')
                file.write("file does not exist yet.")
                #file.write(studentinfo['MatricNum'] + ' ,' + studentinfo['FirstName'] + studentinfo['LastName'])
                file.write(studentinfo['MatricNum'] + ' ,' + studentinfo['FirstName'] + studentinfo['LastName'])
                file.close()

            print(test)
            logger.info("Successfully signed into lecture")
            return render_template('signedin.html', lecturedata=lectureinfo[0])

        else:
            error = "Wrong Password or Lecture Code"
            return render_template('lecturesignin.html', error=error)
    else:

        date = datetime.datetime.now()

        return render_template('lecturesignin.html', date=date)


@app.route("/gencode", methods=['GET', 'POST'])
def gencode():

    if request.method == 'POST':
        modulecode = request.form['module']
        return render_template('gencode.html', moduleselected=False, lectureselected=False )

    else:
        if g.user:
            updatemanagedmodules()
            return render_template('gencode.html', moduleselected=False, lectureselected=False)

        return redirect(url_for('lecturersignin'))


@app.route("/selectmodule", methods=['GET', 'POST'])
def selectmodule():

    module = request.form['module']

    query = "SELECT * FROM Lectures WHERE ModuleID=?"

    result = pd.read_sql(query, conn, params=(module,))
    lectureinfo = result.to_dict('records')
    print(lectureinfo)

    return render_template('gencode.html', lectures=lectureinfo, moduleselected=True, lectureselected=False)


@app.route("/selectlecture", methods=['GET', 'POST'])
def selectlecture():

    lecture = request.form['lecture']
    flash(lecture)
    return render_template('gencode.html', moduleselected=True, code=lecture, lectureselected=True)


def generatenewcode():

    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))


def checkpass(stored_password, provided_password):
    """Verify a stored password against one provided by user"""
    salt = stored_password[:64]
    stored_password = stored_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha512',
                                  provided_password.encode('utf-8'),
                                  salt.encode('ascii'),
                                  100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == stored_password


def hash_password(password):
    """Hash a password for storing."""
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


@app.route('/sign_out')
def sign_out():
    session.pop('user', None)
    logger.info("Successfully Signed In")
    return redirect(url_for('Home'))


if __name__ == "__main__":

    app.run(host='0.0.0.0', threaded=True, debug=True, port=5000)

