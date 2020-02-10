import csv
import datetime
import fileinput
import re

import requests
from werkzeug.utils import secure_filename
import isodate
import random
import pandas as pd
import pyodbc
import string
import logging
from os import path
from datetime import date

import sys
import os
from logging import handlers

from flask import Flask, render_template, request, redirect, url_for, flash, session, g, json
import hashlib, binascii, os

app = Flask(__name__)

app.secret_key = "supersecretkey"
UPLOAD_FOLDER = os.path.dirname(os.path.realpath(__file__)) + "/Uploads"
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
formatter = logging.Formatter("%(asctime)s:%(levelname)s: %(message)s", "%Y-%m-%d %H:%M")
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

        set_week()
        lectures = get_next_lecture(get_week())

        return render_template('lecturerhome.html',

                               next_lecture=lectures, timetabled_days=check_timetabled_days(lectures), lectures=lectures)

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

            logger.info("Successfully Signed Into Lecturer Account")
            return redirect(url_for('lecturerhomepage'))

        else:

            error = "LecturerID or password is incorrect"
            logger.info("LecturerID or password is incorrect")

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

            logger.info("Student uploaded to database")

            json_string = str('{ "MatricNum" : ' + str(idnum) + ', "FirstName" : "' + str(fname) + '", "LastName" : "' + str(lname) + '" }')
            logger.info("attempting to add " + json_string + " to SOC file.")

            with open("SOC_Students.txt", "a") as f:
                if os.stat("SOC_Students.txt").st_size == 0:
                    f.write(json_string)
                    logger.info("Student added to SOC file")
                else:

                    f.write('\n' + json_string)
                    logger.info("Student added to SOC file")

            notification = "account successfully created"
            logger.info("Student account successfully created")

        return render_template('signup.html', notification=notification)

    return render_template('signup.html')


@app.route("/select_module_lecture", methods=['GET', 'POST'])
def select_module_lecture():

    if request.method == 'POST':

        session['selected_module_lecture'] = request.form['module']

        return render_template('createlecture.html', modules=session['supervisedmodules'], moduleselected=True)


@app.route("/createlecture", methods=['GET', 'POST'])
def createlecture():

    if request.method == 'POST':


        time = request.form['time']
        duration = request.form['duration']
        name = request.form['name']
        location = request.form['location']
        module = session['selected_module_lecture']
        weekday = request.form['weekday']
        first = request.form['first']
        first = int(first)
        last = request.form['last']
        last = int(last)

        for x in range(first, last + 1):

            query = "INSERT INTO Lectures (LectureID, ModuleID, LectureName, LectureLocation, LectureDuration, Week, Day, Time ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"

            cursor.execute(query, (generatenewcode(), module, name, location, duration, x, weekday, time))
            conn.commit()

        logger.info("Lecture set: " + weekday + " from week " + str(first) + " to " + str(last) + " at " + location + " at " + time +" successfully created.")
        updatemanagedmodules()
        flash("Lecture successfully timetabled.")

        return redirect(url_for('createlecture'))

    else:

        if g.user:

            return render_template('createlecture.html', modules=session['supervisedmodules'], moduleselected=False)

        return redirect(url_for('lecturersignin'))


@app.route("/module_options", methods=['GET', 'POST'])
def module_options():

    if request.method == 'POST':
        lecture_id = request.form['Lecture']
        logger.info("Lecture deleted")
        delete_lecture(lecture_id)
        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = get_lectures(session['moduleid'])

        return render_template('module_options.html', moduleid=session['moduleid'], lectures=modulelectures,
                               timetabled_days=check_timetabled_days(modulelectures))

    else:

        if g.user:

            module_id = request.args['module']
            session['moduleid'] = module_id
            getmoduleinfo(session['moduleid'])
            updatemanagedmodules()
            modulelectures = sort_lectures(get_week(), get_lectures(module_id), "Weekly")
            logger.info("Retrieving module lectures from " + str(module_id) + " for the current week...")

            return render_template('module_options.html', moduleid=module_id, lectures=modulelectures,
                                   timetabled_days=check_timetabled_days(modulelectures))

        return redirect(url_for('lecturersignin'))


@app.route("/sort_timetable", methods=['POST'])
def sort_timetable():

    if "semester1" in request.form:

        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = sort_lectures(12, get_lectures(session['moduleid']), "Semester1")

        logger.info("Sorting lectures in " + str(session['moduleid']) + " by Semester 1")
        return render_template('module_options.html', moduleid=session['moduleid'], lectures=modulelectures,
                               timetabled_days=check_timetabled_days(modulelectures))

    if "semester2" in request.form:

        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = sort_lectures(13, get_lectures(session['moduleid']), "Semester2")
        logger.info("Sorting lectures in " + str(session['moduleid']) + " by Semester 2")

        return render_template('module_options.html', moduleid=session['moduleid'], lectures=modulelectures,
                               timetabled_days=check_timetabled_days(modulelectures))

    if "currentweek" in request.form:

        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = sort_lectures(get_week(), get_lectures(session['moduleid']), "Weekly")
        logger.info("Sorting lectures in " + str(session['moduleid']) + " by current week")

        return render_template('module_options.html', moduleid=session['moduleid'], lectures=modulelectures,
                               timetabled_days=check_timetabled_days(modulelectures))


def sort_lectures(week, lectures, type):

    if type == "Weekly":

        week = int(week)
        filtered_lectures = []
        for item in lectures:

            if item['Week'] == week:

                filtered_lectures.append(item)

    if type == "Semester1":

        week = int(week)
        filtered_lectures = []
        for item in lectures:

            if item['Week'] <= week:
                filtered_lectures.append(item)

    if type == "Semester2":

        week = int(week)
        filtered_lectures = []
        for item in lectures:

            if item['Week'] >= week:
                filtered_lectures.append(item)

    return filtered_lectures


def delete_lecture(lecture_id):

    cursor.execute("DELETE FROM Lectures WHERE LectureID=?", (lecture_id,))
    cursor.commit()


@app.route("/student_stats", methods=['GET', 'POST'])
def student_stats():

    if request.method == 'POST':

        pass

    else:
        print("okay")
        matric_num = request.args['Student']
        session['Student'] = get_student_info_doc(matric_num)
        session['labels'] = [1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24]

        student = get_student_info_doc(matric_num)

        logger.info("Student Total attendance is: " + str(get_class_attendance(student, 24, get_lectures(session['moduleid']))))
        session['graph_data'] = get_graph_info(matric_num)
        return render_template('student_stats.html')


def get_graph_info(matric_num):

    student = get_student_info_doc(matric_num)

    graph_data = []

    lectures = get_lectures(session['moduleid'])

    for x in range(min(get_lectures(session['moduleid']), key=lambda d: d.get("Week", float('inf')))["Week"], max(get_lectures(session['moduleid']), key=lambda d: d.get("Week", float('inf')))["Week"]):

        graph_data.append(get_class_attendance(student, x, lectures ))

    return graph_data


def get_class_attendance(student, week, module_lectures):

    sorted_lectures = []

    lectures = []


    for item in module_lectures:

        if item['Week'] <= week:

            lectures.append(item)



    for item in lectures:

        if item['LectureID'] not in student:
            continue

        else:
            sorted_lectures.append(item)

    attended_classes = 0

    for item in sorted_lectures:

        if student[item['LectureID']] == "Present":

            attended_classes = attended_classes + 1

    percentage = attended_classes/(len(sorted_lectures)) * 100

    return percentage


@app.route("/delete_module", methods=['POST'])
def delete_module():

    module_id = request.form['Module']

    cursor.execute("DELETE FROM Modules WHERE ModuleID=?", (module_id,))
    cursor.commit()

    cursor.execute("DELETE FROM Lectures WHERE ModuleID=?", (module_id,))
    cursor.commit()

    module_id = request.args['module']
    session['moduleid'] = module_id
    getmoduleinfo(module_id)
    updatemanagedmodules()
    modulelectures = get_lectures(module_id)
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

        if x['Day'] == 'Tuesday':
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


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload_file', methods=['POST'])
def upload_file():

    # check if the post request has the file part
    if "file" not in request.files:
        flash('No file part')

        return redirect(url_for('class_list_management', module_id=session['moduleid']))

    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        flash('No selected file')


        return redirect(url_for('class_list_management', module_id=session['moduleid']))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        students = []

        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename),'r') as csvfile, open(os.path.join(app.config['UPLOAD_FOLDER'], 'temp_file.json'), 'w') as jsonfile:
            fieldnames = ("MatricNum", "FirstName", "LastName")
            reader = csv.DictReader(csvfile, fieldnames)
            for row in reader:
                json.dump(row, jsonfile)
                jsonfile.write('\n')

        with open(os.path.join(app.config['UPLOAD_FOLDER'], 'temp_file.json'), 'r') as jsonfile:

            for line in jsonfile:
                students.append(json.loads(line))

        students.pop(0)

        for item in students:

            if path.exists(create_path('class_list', session['moduleid'])) is True and check_if_in_file(item['MatricNum'], create_path('class_list', session['moduleid'])) is True:
                logger.info("Error, this student is already in the class list, skipping")
                continue

            else:

                create_class_list(item['MatricNum'], session['moduleid'])

    return redirect(url_for('class_list_management', module_id=session['moduleid']))


@app.route("/class_list_management", methods=['GET', 'POST'])
def class_list_management():

    if request.method == 'POST':

        f_name = request.form['f_name']
        l_name = request.form['l_name']
        matric_num = request.form['matric_num']
        logger.info("Attempting to add " + f_name + ' ' + l_name + ' to class list: ' + session['moduleid'])

        if check_if_in_file(matric_num, 'SOC_Students.txt') is False:

            flash("Error, this student does not seem to exist.")
            logger.info("Error, this student does not seem to exist.")

            return redirect(url_for('class_list_management', module_id=session['moduleid']))

        if path.exists(create_path('class_list', session['moduleid'])) is True and check_if_in_file(matric_num, create_path('class_list', session['moduleid'])) is True:

            logger.info("Abandoning... student is already in the class list")
            flash("Error, this student is already in the class list!")
            session['class_list'] = retrieve_class_list(session['moduleid'])
            return redirect(url_for('class_list_management', module_id=session['moduleid']))

        else:

            create_class_list(matric_num, session['moduleid'])
            return redirect(url_for('class_list_management', module_id=session['moduleid']))

    else:

        if g.user:

            if 'class_list' in session:
                session.pop('class_list')
            module_id = request.args['module_id']
            session['moduleid'] = module_id

            if check_path_exists(create_path('class_list', module_id)):

                exists = True
                class_list = retrieve_class_list(module_id)
                session['class_list'] = class_list
            else:

                exists = False
                class_list = None

            return render_template('class_list_management.html', exists=exists, class_list=class_list)

        return redirect(url_for('lecturersignin'))


@app.route("/remove_from_class_list", methods=['POST'])
def remove_from_class_list():

    student_id = request.form['Student']

    logger.info("attempting to remove " + str(student_id) + " from class list...")

    temp_list = pull_soc_list()

    for item in temp_list:

        if str(item['MatricNum']) == str(student_id):

            student = item
            temp_list.remove(item)
            break

    get_lectures(session['moduleid'])

    logger.info("removing expected lectures for module...")

    logger.info(str(student_id) + " currently has " + str(len(get_student_info_doc(student_id)) - 3) + " expected lectures")

    for x in get_lectures(session['moduleid']):

        if x['LectureID'] in student:

            student.pop(x['LectureID'])

    logger.info(str(student_id) + " now has " + str(len(student) - 3) + " expected lectures")

    logger.info("updating SOC document")

    temp_list.append(student)

    push_to_soc(temp_list)

    logger.info("removing from class list document...")

    file_contents = []

    with open(create_path('class_list', session['moduleid']), 'r') as f:

        for line in f:

            file_contents.append(json.loads(line))

    for item in file_contents:

        if str(item).strip() == str(student_id):

            file_contents.remove(item)

    with open(create_path('class_list', session['moduleid']), 'w') as f:

        f.write(str(file_contents[0]))

        for item in file_contents[1:(len(file_contents) + 1)]:

            f.write('\n' + str(item))

    logger.info("student removed from class list document.")

    return redirect(url_for('class_list_management', module_id=session['moduleid']))


def pull_soc_list():

    school_list = []

    with open('SOC_Students.txt', 'r') as file:

        for line in file:
            line = line.replace("\'", "\"")
            school_list.append(json.loads(line))

    return school_list


def push_to_soc(school_list):

    with open('SOC_Students.txt', 'w') as f:

        for item in school_list:
            f.write("%s\n" % item)


def retrieve_class_list(module_id):

    class_list = []
    attendance = []
    with open(create_path('class_list', module_id), "r") as f:

        for line in f:

            class_list.append(get_student_info(line))


    return class_list


def create_class_list(matric_num, module_id):

    file_path = create_path('class_list', module_id)

    if check_path_exists(file_path):

        logger.info("File exists, attempting to updating student info then attempting to append to file...")
        student = update_student_info(get_student_info_doc(matric_num), module_id)

        with open(create_path('class_list', module_id), 'a') as f:

            if os.stat(create_path('class_list', module_id)).st_size == 0:

                f.write(str(student['MatricNum']))

            else:

                f.write('\n' + str(student['MatricNum']))

    else:

        logger.info("File does not exist, creating file...")
        logger.info("File created, updating student info...")
        student = update_student_info(get_student_info_doc(matric_num), module_id)
        file = open(file_path, 'w+')
        file.write(str(student['MatricNum']))
        file.close()


def update_student_info(student, module_id):

    for x in get_lectures(session['moduleid']):

        if x['LectureID'] in student:
            print("okay")
            pass

        else:

            student.update({x['LectureID']: "Absent"})

    update_soc_data(student)

    return student


def update_soc_data(student):

    school_list = []

    with open('SOC_Students.txt', 'r') as file:

        for line in file:

            line = line.replace("\'", "\"")
            school_list.append(json.loads(line))

    for item in school_list:

        if item.get('MatricNum') == student['MatricNum']:

            school_list.remove(item)

    school_list.append(student)

    with open('SOC_Students.txt', 'w') as f:

        for item in school_list:

            f.write("%s\n" % item)

    logger.info(student['FirstName'] + " " + student['LastName'] + " SOC data updated along with class list" )


def get_student_info(matric_num):

    query = "SELECT * FROM Students WHERE MatricNum=?"
    result = pd.read_sql(query, conn, params=(int(matric_num),))
    student = result.to_dict('records')

    return student[0]


def get_student_info_doc(matric_num):

    with open('SOC_Students.txt', 'r') as f:
        student_list = []
        for line in f:

            line = line.replace("\'", "\"")
            student_list.append(json.loads(line))

    for item in student_list:

        if str(item['MatricNum']) == str(matric_num):

            return item


def create_path(type, filename):

    if type == "class_list":

        filename = ('/Class_Lists/%s.txt' % filename)
        current_path = os.path.abspath(os.path.dirname(__file__))
        return current_path + filename


def check_path_exists(path):

    if os.path.exists(path):

        return True

    else:

        return False


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

        if check_duplicate('Modules', 'ModuleName', modulename):
            error = "Error, module ID already exists, please choose another."
            logger.info("Error, module names cannot be duplicated...")
            flash("Error, module name already exists, please choose another")
            return render_template('modulemanager.html', modules=session['supervisedmodules'], Notification=error)

        query = "INSERT INTO Modules(ModuleID, ModuleName, LecturerID) VALUES (?, ?, ?);"
        cursor.execute(query, (moduleid, modulename, session['user']))
        conn.commit()
        updatemanagedmodules()

        logger.info(str(moduleid) + " : " + str(modulename) + " successfully created.")

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


@app.route("/update_managed_modules", methods=['POST'])
def update_managed_modules():

    user_id = request.form['user_id']

    query = "SELECT * FROM Modules WHERE LecturerID=?"
    result = pd.read_sql(query, conn, params=(user_id,))
    session['supervisedmodules'] = result.to_dict('records')

    return json.dumps(True)


@app.route("/lecturesignin", methods=['GET', 'POST'])
def lecturesignin():

    if request.method == 'POST':

        matriculationnumber = request.form['MatriculationNumber']
        password = request.form['Password']
        lecturecode = request.form['LectureCode']

        query = "SELECT * FROM Students WHERE MatricNum=?"

        result = pd.read_sql(query, conn, params=(matriculationnumber,))
        studentinfo = result.to_dict('records')

        if len(studentinfo) != 1:

            error = "Matriculation Number or password is incorrect"
            logger.info("Matriculation Number or password is incorrect")

            return render_template('lecturesignin.html', error=error)

        actualpassword = studentinfo[0]['Password']
        error = None

        query = "SELECT * FROM Lectures WHERE LectureID=?"
        result = pd.read_sql(query, conn, params=(lecturecode,))
        lectureinfo = result.to_dict('records')

        if len(lectureinfo) != 1:
            error = "Incorrect lecture code, please try again"
            logger.info("Incorrect lecture code, attempt made by: " + str(matriculationnumber))

            return render_template('lecturesignin.html', error=error)

        if checkpass(actualpassword, password) is True and len(lectureinfo) is 1:

            filename = ('/Attendance_Docs/%s.txt' % lecturecode)
            current_path = os.path.abspath(os.path.dirname(__file__))
            path = current_path + filename
            attendance_info = ('Matriculation_Number: ' + studentinfo[0]['MatricNum'] + ', First_Name: ' + studentinfo[0]['FirstName'] + ', Last_Name: '+ studentinfo[0]['LastName'] + ';' )

            with open('SOC_Students.txt', 'r') as f:

                student_list = []
                for line in f:
                    line = line.replace("\'", "\"")
                    student_list.append(json.loads(line))

            for item in student_list:

                if str(item['MatricNum']) == str(matriculationnumber):

                    if item[lecturecode] == "Present":

                        logger.info(studentinfo[0]['FirstName'] + ' ' + studentinfo[0]['LastName'] + " has already been signed in.")
                        error = studentinfo[0]['FirstName'] + ' ' + studentinfo[0]['LastName'] + " has already been signed in."
                        return render_template('lecturesignin.html', error=error)

                    else:

                        item[lecturecode] = "Present"

                    update_soc_data(item)

                    logger.info(studentinfo[0]['FirstName'] + ' ' + studentinfo[0]['LastName'] + " has been successfully signed into lecture")
                    return render_template('signedin.html', lecturedata=lectureinfo[0])

            error = "Wrong lecture code, or you are not in the class list, speak to your lecturer."
            return render_template('lecturesignin.html', error=error)

        else:
            error = "Wrong Password or Lecture Code"
            return render_template('lecturesignin.html', error=error)
    else:

        date = datetime.datetime.now()

        return render_template('lecturesignin.html', date=date)


def check_if_in_file(matriculation_number, path):

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

    return render_template('gencode.html', lectures=sort_lectures(get_week(), get_lectures(module), "Weekly"), moduleselected=True, lectureselected=False)


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
    # filename = ('/Attendance_Docs/%s.txt' % lecturecode)
    result = pd.read_sql(query, conn, params=(unique_key,))
    tableinfo = result.to_dict('records')

    if len(tableinfo) > 0:

        return True

    else:

        return False


def get_week():

    today = datetime.datetime.today()

    for key, value in session['weeks'].items():

        if value.isocalendar()[1] == today.isocalendar()[1] and value.year == today.year:

            return key


def set_week():

    dict_of_weeks = {}

    dict_of_weeks[1] = datetime.datetime.strptime("16-09-2019", "%d-%m-%Y")

    for i in range(2, 13):
        dict_of_weeks[i] = dict_of_weeks[i - 1] + datetime.timedelta(days=7)

    dict_of_weeks[13] = datetime.datetime.strptime("20-01-2020", "%d-%m-%Y")
    for i in range(14, 25):
        dict_of_weeks[i] = dict_of_weeks[i - 1] + datetime.timedelta(days=7)

    session['weeks'] = dict_of_weeks


def get_next_lecture(week):

    updatemanagedmodules()
    week_lectures = []

    for x in session['supervisedmodules']:

        week_lectures = week_lectures + get_lectures(x['ModuleID'])

    week_lectures = sort_lectures(get_week(), week_lectures, "Weekly")

    for x in week_lectures:

        if x['Day'] == 'Monday':
            x['index'] = 0

        if x['Day'] == 'Tuesday':
            x['index'] = 1

        if x['Day'] == 'Wednesday':
            x['index'] = 2

        if x['Day'] == 'Thursday':
            x['index'] = 3

        if x['Day'] == 'Friday':
            x['index'] = 4

    week_lectures = sorted(week_lectures, key=lambda k: k['index'])

    for x in week_lectures:

        x['Time '] = re.sub(':', '', x['Time '])

    week_lectures = sorted(week_lectures, key=lambda k: k['Time '])

    return week_lectures


@app.route('/sign_out')
def sign_out():
    session.pop('user', None)
    session.clear()
    logger.info("Successfully Signed Out")
    return render_template('homepage.html')


if __name__ == "__main__":

    app.run(host='0.0.0.0', threaded=True, debug=True, port=5000)
