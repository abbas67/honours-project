import datetime
import random
import pandas as pd
import pyodbc
import string
import logging
from os import path
import sys
import os
from logging import handlers

from flask import Flask, render_template, request, redirect, url_for, flash, session, g, json
import hashlib, binascii, os

app = Flask(__name__)

app.secret_key = "supersecretkey"

if path.exists('logger.log'):
    os.remove('logger.log')
    print("Log file rotated.")


logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('logger.log')
fh.setLevel(logging.INFO)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s")
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

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
            logger.info("Successfully Signed Into Lecturer Account")
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
            logger.info("Lecturer account successfully created")

        else:

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



@app.route("/module_options", methods=['GET', 'POST'])
def module_options():

    if request.method == 'POST':

        module_id = request.form['Module']
        getmoduleinfo(module_id)
        print(session['moduleinfo'])
        updatemanagedmodules()
        modulelectures = get_lectures(module_id)

        return render_template('module_options.html', moduleid=module_id, lectures=modulelectures,
                               timetabled_days=check_timetabled_days(modulelectures))

    else:
        if g.user:

            module_id = request.form['Module']
            updatemanagedmodules()
            return render_template('module_options.html', ID=module_id, lectures=get_lectures(module_id))

        return redirect(url_for('lecturersignin'))


@app.route("/delete_module", methods=['POST'])
def delete_module():

    module_id = request.form['Module']

    cursor.execute("DELETE FROM Modules WHERE ModuleID=?", (module_id,))
    cursor.commit()

    cursor.execute("DELETE FROM Lectures WHERE ModuleID=?", (module_id,))
    cursor.commit()

    updatemanagedmodules()
    logger.info("Module Deleted")
    return render_template('modulemanager.html', modules=session['supervisedmodules'])


def get_lectures(module):

    query = "SELECT * FROM Lectures WHERE ModuleID=? ORDER BY Week ASC"

    result = pd.read_sql(query, conn, params=(module,))
    return result.to_dict('records')


def check_timetabled_days(modulelectures):
    timetabled_days = {'Monday': False, 'Tuesday': False, 'Wednesday': False, 'Thursday': False, 'Friday': False}

    for x in modulelectures:

        if x['Day'] == 'Monday':
            timetabled_days['Monday'] = True

        if x['Day'] == 'Tueday':
            timetabled_days['Tuesday'] = True

        if x['Day'] == 'Wednesday':
            timetabled_days['Wednesday'] = True

        if x['Day'] == 'Thursday':
            timetabled_days['Thursday'] = True

        if x['Day'] == 'Friday':
            timetabled_days['Friday'] = True

    return timetabled_days


def getmoduleinfo(module_id):

    query = "SELECT * FROM Modules WHERE ModuleID=?"
    result = pd.read_sql(query, conn, params=(module_id,))
    #result.sort_values(by=3, ascending=True)
    session['moduleinfo'] = result.to_dict('records')[0]


@app.route("/modulemanagement", methods=['GET', 'POST'])
def modulemanagement():

    if request.method == 'POST':

        moduleid = request.form['moduleid']
        modulename = request.form['modulename']

        if check_duplicate('Modules', 'ModuleID', moduleid):
            error = "Error, module ID already exists, please choose another."
            logger.info("Error, module ID already exists, please choose another.")
            flash("Error, module ID already exists, please choose another.")
            return render_template('modulemanager.html', modules=session['supervisedmodules'], Notification=error)

        query = "INSERT INTO Modules(ModuleID, ModuleName, LecturerID) VALUES (?, ?, ?);"
        cursor.execute(query, (moduleid, modulename, session['user']))
        conn.commit()
        updatemanagedmodules()
        logger.info("Module Created")
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

            filename = ('/Attendance_Docs/%s.txt' % lecturecode)
            current_path = os.path.abspath(os.path.dirname(__file__))
            path = current_path + filename
            attendance_info = ('Matriculation_Number: '+ studentinfo[0]['MatricNum'] + ', First_Name: ' + studentinfo[0]['FirstName'] + ', Last_Name: '+ studentinfo[0]['LastName'] + ';' )

            if os.path.exists(path):

                if check_if_signed_in(matriculationnumber, path):
                    error = "Your attendance has already been recorded for this lecture."
                    logger.info("Error, student attendance has already been recorded")
                    return render_template('lecturesignin.html', error=error)

                logger.info("Lecture attendance file exists, appending to file...")
                with open(path, 'a') as file:
                    file.write('\n' + attendance_info)
            else:

                logger.info("Lecture attendance file does not exist yet, creating new file...")
                file = open(path, 'w+')
                file.write(attendance_info)
                file.close()

            logger.info("Successfully signed into lecture")
            return render_template('signedin.html', lecturedata=lectureinfo[0])

        else:
            error = "Wrong Password or Lecture Code"
            return render_template('lecturesignin.html', error=error)
    else:

        date = datetime.datetime.now()

        return render_template('lecturesignin.html', date=date)


def check_if_signed_in(matriculation_number, path):

    with open(path) as f:
        if matriculation_number in f.read():
            return True
        else:
            return False


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

    return render_template('gencode.html', lectures=get_lectures(module), moduleselected=True, lectureselected=False)


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


def check_duplicate(table_name, field, unique_key):

    query = ("SELECT * FROM %s WHERE %s=?" % (table_name, field))
    print(query)
    # filename = ('/Attendance_Docs/%s.txt' % lecturecode)
    result = pd.read_sql(query, conn, params=(unique_key,))
    tableinfo = result.to_dict('records')
    print(tableinfo)

    if len(tableinfo) > 0:

        return True

    else:

        return False


@app.route('/sign_out')
def sign_out():
    session.pop('user', None)
    logger.info("Successfully Signed Out")
    return redirect(url_for('Home'))


if __name__ == "__main__":

    app.run(host='0.0.0.0', threaded=True, debug=True, port=5000)

