import binascii
import csv
import datetime
from datetime import timedelta
import hashlib
import logging
import os
import random
import re
import string
import collections
from collections import Counter
from os import path
import pandas as pd
import pyodbc
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, json
from werkzeug.utils import secure_filename
import ssl
import smtplib

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

# drivers = [item for item in pyodbc.drivers()]
# driver = drivers[-1]
# server = 'tcp:abbaslawal.database.windows.net,1433'
# database = 'abbaslawal-db'
# uid = 'alawal98'
# pwd = 'Hazard1998'
#
# params = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}'
# conn = pyodbc.connect(params)
# Dynamically selecting a driver based on the machine.
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


@app.route("/lecturer_home")
def lecturer_home():
    """ endpoint for lecturer homepage, no POST requests needed. """
    if g.user:
        # getting required lecturer info.
        set_week()
        lectures = get_next_lecture(get_week())
        messages = attendance_flagging()

        if len(messages) == 0:

            show_messages = False

        else:

            show_messages = True
        # Returning a response to the get request.
        return render_template('lecturer_home.html',
                               next_lecture=lectures, timetabled_days=check_timetabled_days(lectures), lectures=lectures, show_messages=show_messages, student_messages=messages)

    return redirect(url_for('lecturersignin'))


def attendance_flagging():

    """ method used for flagging students with less than 50% attendance. """
    messages = []

    for item in session['supervised_modules']:

        lectures = get_lectures(item['ModuleID'])

        if lectures:
            # Currently skipping first semester as it is not currently of concern!
            if lectures[0]['Week'] <= 12:
                logger.info("Skipping first semester classes")
                continue
        # Updating the current attendance to make sure the flagging is accurate.
        update_module_attendance(item['ModuleID'], retrieve_class_list(item['ModuleID']))
        # Retrieving the updated class list.
        students = retrieve_class_list(item['ModuleID'])

        for student in students:
            # checking if
            if int(float(student['Attendance'])) < int(float(50)):

                logger.info(student['FirstName'] + " " + student['LastName'] + " Has less than 50% attendance for " + item['ModuleID'])

                messages.append(tuple((student['FirstName'] + " " + student['LastName'] + " Has less than 50% attendance for " + item['ModuleID'], student['MatricNum'], item['ModuleID'])))

            if int(float(student['Attendance'])) >= int(float(80)):

                logger.info(student['FirstName'] + " " + student['LastName'] + " Has more than 80% attendance for " + item['ModuleID'])

            if int(float(student['Attendance'])) == int(float(100)):

                logger.info(student['FirstName'] + " " + student['LastName'] + " Has 100% attendance for " + item['ModuleID'])

            else:

                logger.info(
                    student['FirstName'] + " " + student['LastName'] + " Has less than 80% attendance for " + item['ModuleID'])



    # returning info on any students that have been flagged.
    return messages


@app.route("/redirect_to_student", methods=['POST'])
def redirect_to_student():

    session['moduleid'] = request.form['module_id']

    return redirect(url_for('student_stats', Student=request.form['student'], from_home=True))


@app.route("/send_email", methods=['POST'])
def send_email():

    # https://realpython.com/python-send-email/
    student = get_student_info(request.form['student'])
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = "abbas.uod.honours@gmail.com"  # Enter your address

    if student['Email'] == 'abc123@dundee.ac.uk':
        receiver_email = 'spam.dundee.testing@gmail.com'

    password = 'thisismypassword123'

    query = 'SELECT * FROM {} WHERE MatricNum={}'.format(session['moduleid'], student['MatricNum'])
    result = pd.read_sql(query, conn)
    attendance = result.to_dict('records')[0]['Attendance']

    if 80 > attendance > 50:
        message = 'Subject:\n Hi there ' \
                  '\n This is a message to let you know that your attendance is below the university policy for {}.' \
                  ' \n Please contact the lecturer if you have any issues.'.format(session['moduleid'])

        logger.info("An email has been sent to " + student['FirstName'] + " " + student['LastName'] + " Regarding poor attendance.")
        flash("An email has been sent to " + student['FirstName'] + " " + student['LastName'] + " Regarding poor attendance.")

    if attendance < 50:
        message = 'Subject:\n Hi there ' \
                  '\n This is a message to let you know that your attendance is extremely low for {}.' \
                  ' \n Please contact the lecturer if you have any issues.'.format(session['moduleid'])

        logger.info("An email has been sent to " + student['FirstName'] + " " + student['LastName'] + " Regarding worrying attendance.")
        flash("An email has been sent to " + student['FirstName'] + " " + student['LastName'] + " Regarding worrying attendance.")
    if attendance >= 80:
        message = 'Subject:\n Hi there ' \
                  '\n This is a message to let you know that your attendance is whithin the university policy for {}!.' \
                  ' \n Please contact the lecturer if you have any issues/questions.'.format(session['moduleid'])

        logger.info("An email has been sent to " + student['FirstName'] + " " + student['LastName'] + " Regarding good attendance.")
        flash("An email has been sent to " + student['FirstName'] + " " + student['LastName'] + " Regarding good attendance.")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)

    return redirect(url_for('student_stats', Student=request.form['student'], from_home=False))


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
            return redirect(url_for('lecturer_home'))

        else:

            error = "LecturerID or password is incorrect"
            logger.info("LecturerID or password is incorrect")

            return render_template('lecturersignin.html', error=error)

    else:

        if g.user:
            return redirect(url_for('lecturer_home'))

        return render_template('lecturersignin.html')


@app.route("/signup", methods=['POST', 'GET'])
def signup():

    if request.method == 'POST':

        notification = None

        idnum = request.form['idnum']
        password = hash_password(request.form['password'])
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
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

            if len(idnum) != 9:
                notification = "Please enter a valid matriculation number"
                logger.info("Invalid Matriculation Number")
                return render_template('signup.html', notification=notification)

            query = "SELECT * FROM Students WHERE MatricNum=?"
            result = pd.read_sql(query, conn, params=(idnum,))
            resultdict = result.to_dict('records')

            if len(resultdict) > 0:
                notification = "The ID already exists"
                logger.info("Error, ID already exists")
                return render_template('signup.html', notification=notification)

            query = "INSERT INTO Students (MatricNum, FirstName, LastName, Password, Email, ModuleString) VALUES (?, ?, ? ,?, ?, ?);"
            cursor.execute(query, (idnum, fname, lname, password,email,''))
            conn.commit()

            logger.info("Student uploaded to database")

            notification = "account successfully created"
            logger.info("Student account successfully created")

        return render_template('signup.html', notification=notification)

    return render_template('signup.html')


@app.route("/select_module_lecture", methods=['GET', 'POST'])
def select_module_lecture():

    if request.method == 'POST':

        session['selected_module_lecture'] = request.form['module']

        return render_template('createlecture.html', modules=session['supervised_modules'], moduleselected=True)


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

            hour = convert_time(time, weekday, x)

            query = "INSERT INTO Lectures (LectureID, ModuleID, LectureName, LectureLocation, LectureDuration, Week, Day, Time) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"

            cursor.execute(query, (generatenewcode(), module, name, location, duration, x, weekday, hour))
            conn.commit()

        logger.info("Lecture set: " + weekday + " from week " + str(first) + " to " + str(last) + " at " + location + " at " + str(hour) +" successfully created.")

        updatemanagedmodules()

        # update_soc_students_lectures(module)
        flash("Lecture successfully timetabled.")

        return redirect(url_for('createlecture'))

    else:

        if g.user:

            return render_template('createlecture.html', modules=session['supervised_modules'], moduleselected=False)

        return redirect(url_for('lecturersignin'))


def convert_time(hour, day, week):

    x = hour


    actual_day = 0
    updated_week = None

    if day == 'Monday':

        actual_day = 0

    if day == 'Tuesday':

        actual_day = 1

    if day == 'Wednesday':

        actual_day = 2

    if day == 'Thursday':

        actual_day = 3

    if day == 'Friday':

        actual_day = 4

    updated_week = return_week(week)

    lecture_time = str(hour)

    updated_week = updated_week + timedelta(actual_day)

    updated_week = updated_week + timedelta(hours=int((lecture_time[:2])))

    return updated_week


def return_week(week):

    dict_of_weeks = {}

    dict_of_weeks[1] = datetime.datetime.strptime("16-09-2019", "%d-%m-%Y")

    for i in range(2, 13):
        dict_of_weeks[i] = dict_of_weeks[i - 1] + datetime.timedelta(days=7)

    dict_of_weeks[13] = datetime.datetime.strptime("20-01-2020", "%d-%m-%Y")
    for x in range(14, 25):
        dict_of_weeks[x] = dict_of_weeks[x - 1] + datetime.timedelta(days=7)

    return dict_of_weeks[week]


def get_graph_info(module_id):

    graph_data = []

    lectures = get_lectures(module_id)

    week = int(get_week())

    if week < 13:

        session['labels'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        for x in range(0, 12):

            pass

        return graph_data

    if week >= 13:

        session['labels'] = [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
        for x in range(13, 25):

            pass

        return graph_data


def get_lecture_attendance(lecture_id, class_list, module_id):

    students_present = 0

    lecture_id = lecture_id + '-1'
    for student in class_list:

        if lecture_id in student['ModuleString']:

            students_present = students_present + 1

    return int((students_present / len(class_list)) * 100)


@app.route("/update_office_docs", methods=['POST'])
def update_office_docs():

    """ Method used to update documents for the school office.
     This is ideally done automatically after each lecture but as a proof of concept
     This is done manually."""

    module_id = request.form['module_id']
    class_list = retrieve_class_list(module_id)
    expected_lectures = get_expected_lectures(get_student_info(class_list[0]['MatricNum']), module_id)

    # Finding the missing students for each student in the lecture.
    for lecture in expected_lectures:

        lecture['absentees'] = []

    for student in class_list:

        for lecture in expected_lectures:

            if lecture['LectureID'] + '-0' in student['ModuleString']:

                lecture['absentees'].append(student)

    # Writing the data for each lecture to a document.
    filename = ('/School_Office_Docs/%s.txt' % module_id)
    current_path = os.path.abspath(os.path.dirname(__file__))
    path = current_path + filename

    with open(path, 'w') as file:

        for lecture in expected_lectures:

            file.write('\n' + lecture['LectureName'] + ": " + lecture['Day'] + " week: " + str(lecture['Week']) + " - " + str(lecture['Time']))
            file.write('\n')
            for absentee in lecture['absentees']:
                file.write('\n' + absentee['FirstName'] + " " + absentee['LastName'] + " " + str(absentee['MatricNum']) + " - Overall Attendance: " + str(absentee['Attendance']) + "%" )
            file.write('\n')

    return redirect(url_for('module_options', module=session['moduleid']))


@app.route("/module_options", methods=['GET', 'POST'])
def module_options():

    if request.method == 'POST':
        lecture_id = request.form['Lecture']
        logger.info("Lecture deleted")
        delete_lecture(lecture_id)
        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = get_lectures(session['moduleid'])

        return redirect(url_for('module_options', module=session['moduleid']))
    else:

        if g.user:

            module_id = request.args['module']
            session['moduleid'] = module_id
            getmoduleinfo(session['moduleid'])
            updatemanagedmodules()
            modulelectures = []

            if 'sorted_lectures' in request.args:

                if request.args['sorted_lectures'] == 'Wrong_Semester':

                    modulelectures = []

                else:

                    lectures = request.args.getlist('sorted_lectures')

                    for item in lectures:

                        item = item.replace("\'", "\"")
                        item = item.replace('Timestamp(','')
                        item = item.replace(')', '')
                        modulelectures.append(json.loads(item))

            else:

                lectures = get_lectures(module_id)

                modulelectures = sort_lectures(get_week(), lectures, "Weekly")

            logger.info("Retrieving module lectures from " + str(module_id) + " for the current week...")
            session['graph_datasets'] = []
            session['labels'] = []
            session['lecture_details'] = []

            if int(get_week()) >= 13:

                for item in modulelectures:

                    if item['Week'] > 12:

                        item['Week'] = item['Week'] - 12

                session['labels'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

            update_module_attendance(module_id, retrieve_class_list(module_id))

            if retrieve_class_list(module_id) != [] and get_lectures(module_id) != []:

                overall_attendance = calculate_overall_attendance(module_id)
                get_graph_data(module_id)


            else:

                overall_attendance = 0
                session['graph_datasets'] = 0

            if session['graph_datasets'] == 0:

                show_graph = False

            else:

                show_graph = True

            return render_template('module_options.html', moduleid=module_id, lectures=modulelectures,
                                   timetabled_days=check_timetabled_days(modulelectures), attendance=overall_attendance, show_graph=show_graph)

        return redirect(url_for('lecturersignin'))


def calculate_overall_attendance(module_id):


    attendance = 0
    attendance_list = []
    student_sum = 0

    class_list = retrieve_class_list(module_id)

    for student in class_list:

        student_sum = student['Attendance'] + student_sum


    attendance = int(student_sum/len(class_list))

    return attendance


def get_graph_data(module_id):

    # https://stackoverflow.com/questions/4091680/splitting-a-list-of-dictionaries-into-several-lists-of-dictionaries

    lectures = get_lectures(module_id)

    class_list = retrieve_class_list(module_id)

    session['graph_datasets'] = []

    result = collections.defaultdict(list)

    for d in lectures:
        result[d['Day']].append(d)

    result_list = list(result.values())

    for item in result_list:

        temp_dict = {}
        temp_dict['graph_data'] = []

        for lecture in item:

            temp_dict['graph_data'].append(get_lecture_attendance(lecture['LectureID'], class_list, module_id))

        temp_dict['Day'] = item[0]['Day']
        session['graph_datasets'].append(temp_dict)


@app.route("/sort_timetable", methods=['POST'])
def sort_timetable():

    if "semester1" in request.form:

        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = sort_lectures(12, get_lectures(session['moduleid']), "Semester1")
        logger.info("Sorting lectures in " + str(session['moduleid']) + " by Semester 1")

        if len(modulelectures) == 0:

            modulelectures = "Wrong_Semester"

        return redirect(url_for('module_options', module=session['moduleid'], sorted_lectures=modulelectures))

    if "semester2" in request.form:

        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = sort_lectures(13, get_lectures(session['moduleid']), "Semester2")
        logger.info("Sorting lectures in " + str(session['moduleid']) + " by Semester 2")

        if len(modulelectures) == 0:

            modulelectures = "Wrong_Semester"

        return redirect(url_for('module_options', module=session['moduleid'], sorted_lectures=modulelectures))

    if "currentweek" in request.form:

        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = sort_lectures(get_week(), get_lectures(session['moduleid']), "Weekly")
        logger.info("Sorting lectures in " + str(session['moduleid']) + " by current week")

        return redirect(url_for('module_options', module=session['moduleid'], sorted_lectures=modulelectures))


def sort_lectures(week, lectures, type):

    filtered_lectures = []

    if type == "Weekly":

        week = int(week)
        filtered_lectures = []
        for item in lectures:

            if item['Week'] == week:

                filtered_lectures.append(item)

    if type == "Semester1":

        week = int(week)

        for item in lectures:

            if int(item['Week']) <= week:
                filtered_lectures.append(item)

    if type == "Semester2":

        week = int(week)

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

        if g.user:

                matric_num = request.args['Student']
                session['Student'] = get_student_info(matric_num)

                if 'from_home' in request.args:

                    from_home = True

                else:

                    from_home = False

                session['module_lectures'] = get_lectures(session['moduleid'])

                expected_lectures = get_expected_lectures(session['Student'], session['moduleid'])

                if len(expected_lectures) == 0:

                    return render_template('student_stats.html', show_stats=False)

                attendance = get_class_attendance(expected_lectures)

                if attendance >= 80:

                    note = "This students attendance is " + str(attendance) + " and is no cause for concern."

                else:

                    note = "This students attendance is " + str(attendance) + " and is cause for concern."

                return render_template('student_stats.html', show_stats=True, attendance_info=expected_lectures, student_statement=note, from_home=from_home)
        else:

            return redirect(url_for('lecturersignin'))


def get_expected_lectures(student, module_id):

    print(session['module_lectures'])
    lectures = get_lectures(module_id)
    expected_lectures = []
    sorted_list = []

    sub_strings = [x.strip() for x in student['ModuleString'].split(';')]

    for sub_string in sub_strings:

        if module_id in sub_string:

            module_lectures = sub_string

    module_lectures = module_lectures[8:]

    module_sub_strings = [x.strip() for x in module_lectures.split(',')]

    for lecture in module_sub_strings:

        if '-1' in lecture:

            expected_lectures.append([(lecture.replace('-1', '')), True])

        else:

            expected_lectures.append([(lecture.replace('-0', '')), False])

    for expected_lecture in expected_lectures:

        for lecture in session['module_lectures']:

            time = lecture['Time']

            if str(lecture['LectureID']) == str(expected_lecture[0]) and has_happened(time) is True:

                new_dict = lecture
                new_dict['Attendance'] = expected_lecture[1]
                sorted_list.append(new_dict)

    return sorted_list


def has_happened(date):

    past = date
    present = datetime.datetime.now()

    return past < present


def get_class_attendance(expected_lectures):

    count = Counter(x['Attendance'] for x in expected_lectures)

    percentage = count[True]/(len(expected_lectures)) * 100

    return int(percentage)


@app.route("/delete_module", methods=['POST'])
def delete_module():

    module_id = request.form['Module']

    cursor.execute("DELETE FROM Modules WHERE ModuleID=?", (module_id,))
    cursor.commit()

    cursor.execute("DELETE FROM Lectures WHERE ModuleID=?", (module_id,))
    cursor.commit()

    #module_id = request.args['module']
    session['moduleid'] = module_id
    getmoduleinfo(module_id)
    updatemanagedmodules()
    logger.info("Module Deleted")

    return render_template('modulemanager.html', modules=session['supervised_modules'])


def get_lectures(module):

    query = "SELECT * FROM Lectures WHERE ModuleID=? ORDER BY Time ASC"

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


def return_module_info(module_id):

    query = "SELECT * FROM Modules WHERE ModuleID=?"
    result = pd.read_sql(query, conn, params=(module_id,))

    return result.to_dict('records')[0]


def getmoduleinfo(module_id):

    query = "SELECT * FROM Modules WHERE ModuleID=?"
    result = pd.read_sql(query, conn, params=(module_id,))

    session['moduleinfo'] = result.to_dict('records')[0]


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload_file', methods=['POST'])
def upload_file():
    """ Endpoint used to generate for uploading of a csv file to add to students to a class list. """

    # check if the post request has the file part
    if "file" not in request.files:

        flash('No file part')
        logger.info("no file found")
        return redirect(url_for('class_list_management', module_id=session['moduleid']))

    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        flash('No selected file')
        logger.info('No selected file')
        return redirect(url_for('class_list_management', module_id=session['moduleid']))

    logger.info("File successfully received")
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        students = []
        try:
            # Converting the csv file to json format so it can be easily handled as a dictionary.
            with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'r') as csvfile, open(os.path.join(app.config['UPLOAD_FOLDER'], 'temp_file.json'), 'w') as jsonfile:
                fieldnames = ("MatricNum", "FirstName", "LastName")
                reader = csv.DictReader(csvfile, fieldnames)
                for row in reader:
                    json.dump(row, jsonfile)
                    jsonfile.write('\n')

        except Exception as e:
            # abandoning the process if there is a problem with the file to avoid crashing the server.
            logger.info("Error, abandoning file upload")
            flash("something went wrong when trying to load the data, are you sure the data is in the right format?")
            logger.info(e)
            return redirect(url_for('class_list_management', module_id=session['moduleid']))

        try:
            # loading the json file in as a list of dictionaries.
            with open(os.path.join(app.config['UPLOAD_FOLDER'], 'temp_file.json'), 'r') as jsonfile:

                for line in jsonfile:
                    students.append(json.loads(line))

            students.pop(0)

        except Exception as e:
            # abandoning the process if there is a problem with the file to avoid crashing the server.
            logger.info("Error, abandoning file upload")
            flash("something went wrong when trying to load the data, are you sure the data is in the right format?")
            logger.info(e)
            return redirect(url_for('class_list_management', module_id=session['moduleid']))

        try:

            for item in students:
                # checking to see that each potential student is eligible to be added to the class list.
                # If they are not then they're skipped.
                if check_if_in_class_list(session['moduleid'], item['MatricNum']) is True:
                    logger.info("Error, this student is already in the class list, skipping")
                    continue

                if get_student_info(item['MatricNum']) is None:

                    logger.info("Error, student, does not exist, skipping")
                    continue

                logger.info("adding " + item['FirstName'] + " " + item['LastName'] + "to " + session['moduleid'])
                # adding the student to the class list.
                create_class_list(item['MatricNum'], session['moduleid'])

            logger.info("all students successfully added to class list.")

        except Exception as e:
            # abandoning the process if there is a problem with a student to avoid crashing the server.
            logger.info("Error, abandoning file upload, problem with student.")
            flash("something went wrong with a student, are you sure all of the students are registered?")
            logger.info(e)
            return redirect(url_for('class_list_management', module_id=session['moduleid']))

    return redirect(url_for('class_list_management', module_id=session['moduleid']))


def check_if_in_class_list(module_id, matric_num):

    query = 'SELECT * FROM {} WHERE MatricNum={}'.format(module_id, int(matric_num))
    result = pd.read_sql(query, conn)
    student = result.to_dict('records')

    return len(student) == 1


@app.route("/search_class_list", methods=['POST'])
def search_class_list():

    keyword = request.form['keyword']
    students = []

    if str.isdigit(keyword):

        query = "SELECT * FROM Students WHERE MatricNum=?"
        result = pd.read_sql(query, conn, params=(int(keyword),))
        students = result.to_dict('records')

    else:
        query = "SELECT * FROM Students WHERE FirstName=? OR LastName=? "
        result = pd.read_sql(query, conn, params=(keyword, keyword,))
        students = result.to_dict('records')

    if len(students) == 0:

        flash("No Student Found")
        return redirect(url_for('class_list_management', module_id=session['moduleid']))
    else:

        class_list = []

        for item in students:

            class_list.append(get_student_info(item['MatricNum']))

    return render_template('class_list_management.html', exists=True, class_list=class_list)


@app.route("/class_list_management", methods=['GET', 'POST'])
def class_list_management():

    if request.method == 'POST':

        f_name = request.form['f_name']
        l_name = request.form['l_name']
        matric_num = request.form['matric_num']
        logger.info("Attempting to add " + f_name + ' ' + l_name + ' to class list: ' + session['moduleid'])

        if get_student_info(matric_num) is None:

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

            module_id = request.args['module_id']
            session['moduleid'] = module_id

            class_list = retrieve_class_list(module_id)
            exists = True
            if len(class_list) == 0:

                exists = False
                class_list = None

            else:

                update_module_attendance(module_id, class_list)

                for student in class_list:

                    student['Attendance'] = get_student_attendance(student['MatricNum'], module_id)


            if get_lectures(module_id) == []:

                lectures_exist = False

            else:

                lectures_exist = True

            return render_template('class_list_management.html', exists=exists, class_list=class_list, lectures_exist=lectures_exist)

        return redirect(url_for('lecturersignin'))


def get_student_attendance(matric_num, module_id):

    query = 'SELECT Attendance FROM {} WHERE MatricNum={}'.format(module_id, matric_num)
    result = pd.read_sql(query, conn)
    student = result.to_dict('records')

    return student[0]['Attendance']


def update_module_attendance(module_id, class_list):

    session['module_lectures'] = get_lectures(module_id)

    expected_lectures = []

    for lecture in session['module_lectures']:

        time = lecture['Time']

        if has_happened(time) is True:
            expected_lectures.append(lecture)

    for student in class_list:

        expected_lectures = get_expected_lectures(student, module_id)

        student_expected_lectures = expected_lectures
        for lecture in student_expected_lectures:

            if lecture['LectureID'] + '-1' in student['ModuleString']:
                lecture['Attendance'] = True

            else:

                lecture['Attendance'] = False
        query = 'UPDATE {} set Attendance={} WHERE MatricNum={}'\
            .format(module_id, get_class_attendance(student_expected_lectures), student['MatricNum'])

        cursor.execute(query)
        conn.commit()


def get_student_info_basic(matric_num):

    query = "SELECT FirstName, LastName FROM Students WHERE MatricNum=?"
    result = pd.read_sql(query, conn, params=(int(matric_num),))
    student = result.to_dict('records')

    if student == []:

        return None

    else:

        return student[0]


@app.route("/remove_from_class_list", methods=['POST'])
def remove_from_class_list():

    student_id = request.form['Student']

    logger.info("attempting to remove " + str(student_id) + " from class list...")

    query = 'DELETE FROM {} WHERE MatricNum={};'.format(session['moduleid'], student_id)

    cursor.execute(query)
    conn.commit()

    # pull_student_modules()

    sub_strings = [x.strip() for x in get_student_info(student_id)['ModuleString'].split(';')]

    for sub_string in sub_strings:

        if sub_string == '':

            sub_strings.remove(sub_string)

    for sub_string in sub_strings:

        if session['moduleid'] in sub_string:
            sub_strings.remove(sub_string)

    module_string = ';' + ';'.join(sub_strings)

    query = 'UPDATE Students SET ModuleString={} WHERE MatricNum={};'.format("'" + module_string + "'", "'" + str(student_id) + "'")
    cursor.execute(query)
    cursor.commit()

    student = get_student_info(student_id)
    logger.info(student['FirstName'] + " " + student['LastName'] + " Removed From " + session['moduleid'])
    return redirect(url_for('class_list_management', module_id=session['moduleid']))


def retrieve_class_list(module_id):

    class_list = []

    query = 'SELECT {}.MatricNum, {}.Attendance, Students.FirstName,Students.LastName, Students.ModuleString FROM {} INNER JOIN Students ON {}.MatricNum=Students.MatricNum;'.format(module_id, module_id, module_id, module_id)

    result = pd.read_sql(query, conn)

    students = result.to_dict('records')

    return students


def create_class_list(matric_num, module_id):

    student = get_student_info(matric_num)
    lectures = get_lectures(module_id)

    if check_if_in_class_list(module_id, matric_num) is False:

        query = 'INSERT INTO {}(MatricNum, Attendance) VALUES (?, ?);'.format(module_id)

        cursor.execute(query, (matric_num, 0))
        conn.commit()

        student_string = str(student['ModuleString']) + ";" + str(module_id) + ":"

        for lecture in lectures:

            student_string = student_string + lecture['LectureID'] + "-" + str(0) + ','

        student_string = student_string[:-1]

        query = 'UPDATE Students SET ModuleString={} WHERE MatricNum={};'.format("'" + student_string + "'", "'" + str(matric_num) + "'")

        logger.info(student['FirstName'] + " " + student['LastName'] + " Added To Class list")

        cursor.execute(query)
        conn.commit()

    else:

        logger.info(student['FirstName'] + " " + student['LastName'] + " is already in the class list.")


def get_student_info(matric_num):

    query = "SELECT * FROM Students WHERE MatricNum=?"
    result = pd.read_sql(query, conn, params=(int(matric_num),))
    student = result.to_dict('records')

    if len(student) == 0:

        return None

    else:

        return student[0]


def create_path(type, filename):

    if type == "class_list":

        filename = ('/Class_Lists/%s.txt' % filename)
        current_path = os.path.abspath(os.path.dirname(__file__))
        return current_path + filename

    if type == "attendance_docs":

        filename = ('/Attendance_Docs/%s.txt' % filename)
        current_path = os.path.abspath(os.path.dirname(__file__))
        return current_path + filename


@app.route("/modulemanagement", methods=['GET', 'POST'])
def modulemanagement():

    if request.method == 'POST':

        moduleid = request.form['moduleid']
        modulename = request.form['modulename']

        if check_duplicate('Modules', 'ModuleID', moduleid):
            error = "Error, module ID already exists, please choose another."
            logger.info("Error, module ID already exists, please choose another.")
            flash("Error, module ID already exists, please choose another.")
            return render_template('modulemanager.html', modules=session['supervised_modules'], Notification=error)

        if check_duplicate('Modules', 'ModuleName', modulename):
            error = "Error, module ID already exists, please choose another."
            logger.info("Error, module names cannot be duplicated...")
            flash("Error, module name already exists, please choose another")
            return render_template('modulemanager.html', modules=session['supervised_modules'], Notification=error)

        if len(moduleid) != 7:

            error = "Error, module ID is the wrong length."
            logger.info("Error, module ID is the wrong length")
            flash("Error, module ID is the wrong length ")
            return render_template('modulemanager.html', modules=session['supervised_modules'], Notification=error)


        query = "INSERT INTO Modules(ModuleID, ModuleName, LecturerID) VALUES (?, ?, ?);"
        cursor.execute(query, (moduleid, modulename, session['user']))
        conn.commit()

        query = 'CREATE TABLE {} (MatricNum char(9), Attendance int);'.format(moduleid)

        cursor.execute(query)
        conn.commit()

        updatemanagedmodules()
        logger.info(str(moduleid) + " : " + str(modulename) + " successfully created.")

        return redirect(url_for('modulemanagement'))

    else:

        if g.user:

            updatemanagedmodules()
            if len(session['supervised_modules']) == 0:

                modules_display = False

            else:

                modules_display = True

            return render_template('modulemanager.html', modules=session['supervised_modules'], modules_display=modules_display)

        return redirect(url_for('lecturersignin'))


def updatemanagedmodules():

    query = "SELECT * FROM Modules WHERE LecturerID=?"
    result = pd.read_sql(query, conn, params=(session['user'],))
    session['supervised_modules'] = result.to_dict('records')


@app.route("/update_managed_modules", methods=['POST'])
def update_managed_modules():

    user_id = request.form['user_id']

    query = "SELECT * FROM Modules WHERE LecturerID=?"
    result = pd.read_sql(query, conn, params=(user_id,))
    session['supervised_modules'] = result.to_dict('records')

    return json.dumps(True)


@app.route("/lecturesignin", methods=['GET', 'POST'])
def lecturesignin():
    """ Endpoint used to generate a web page containing all the module lectures after a module is selected. """
    if request.method == 'POST':

        # Retrieving the data from the POST request.
        matriculationnumber = request.form['MatriculationNumber']
        password = request.form['Password']
        lecturecode = request.form['LectureCode']
        # Checking to see if the student actually exists, if not, throwing back an error, and returning the web page.
        query = "SELECT * FROM Students WHERE MatricNum=?"

        result = pd.read_sql(query, conn, params=(matriculationnumber,))
        studentinfo = result.to_dict('records')

        if len(studentinfo) != 1:

            error = "Matriculation Number or password is incorrect"
            logger.info("Matriculation Number or password is incorrect")

            return render_template('lecturesignin.html', error=error)

        actualpassword = studentinfo[0]['Password']
        error = None
        # Checking to see if the lecture actually exists, if not, throwing back an error, and returning the web page.

        query = "SELECT * FROM Lectures WHERE LectureID=?"
        result = pd.read_sql(query, conn, params=(lecturecode,))
        lectureinfo = result.to_dict('records')

        if len(lectureinfo) != 1:

            error = "Incorrect lecture code, please try again"
            logger.info("Incorrect lecture code, attempt made by: " + str(matriculationnumber))
            return render_template('lecturesignin.html', error=error)

        else:

            lecture = lectureinfo[0]
        # Checking to see if the password exists, if not, throwing back an error, and returning the web page.
        if checkpass(actualpassword, password) is True and len(lectureinfo) is 1:
            # Parsing the students 'module_string' to get the expected lectures for the student.
            sub_strings = [x.strip() for x in get_student_info(matriculationnumber)['ModuleString'].split(';')]
            temp_string = ''
            # Checking to see if the student is actually supposed to be in attendance of the lecture.
            for sub_string in sub_strings:
                if sub_string == '':
                    sub_strings.remove(sub_string)

            for sub_string in sub_strings:

                if sub_string != '' and lecture['ModuleID'] in sub_string:

                    temp_string = sub_string
                    sub_strings.remove(sub_string)

            if temp_string == '':

                error = "Wrong lecture code, or you are not in the class list, speak to your lecturer."
                return render_template('lecturesignin.html', error=error)

            # checking to see if the student has already been signed in...
            module_lectures = temp_string[8:]

            module_sub_strings = [x.strip() for x in module_lectures.split(',')]
            # if the lecture code has a '-1' in it rather than -0 then we know the student has already been signed in.
            if lecture['LectureID'] + '-1' in module_sub_strings:

                logger.info("Error, Student has already been signed in.")
                error = "You are already signed into the lecture! Nothing else is required."
                return render_template('lecturesignin.html', error=error)

            for lecture_string in module_sub_strings:
                # if the lecture code has a '-0' in it rather than -1 then we know the student has not been signed in.
                if lecture['LectureID'] in lecture_string and "-0" in lecture_string:
                    # Marking the student as present in the lecture.
                    module_sub_strings.append(lecture['LectureID'] + "-1")
                    module_sub_strings.remove(lecture_string)

                    new_module_string = lecture['ModuleID'] + ":" + ','.join(module_sub_strings)

                    sub_strings.append(new_module_string)
                    sub_strings = ";" + ';'.join(sub_strings)
                    # Updating the student in the database using a simple SQL statement.
                    query = 'UPDATE Students SET ModuleString={} WHERE MatricNum={};'.format("'" + sub_strings + "'", "'" + str(matriculationnumber) + "'")
                    cursor.execute(query)
                    conn.commit()
                    logger.info(studentinfo[0]['FirstName'] + " " + studentinfo[0]['LastName'] + " Updated ")
                    logger.info(studentinfo[0]['FirstName'] + " " + studentinfo[0]['LastName'] + " Successfully Signed into " + lecturecode)
                    # Providing a HTTP 200 response to the post request.
                    return render_template('signedin.html', lecturedata=lectureinfo[0])

        else:

            error = "Wrong Password or Lecture Code"
            # Providing a HTTP 200 response to the post request.
            return render_template('lecturesignin.html', error=error)
    else:

        date = datetime.datetime.now()
        # Providing a HTTP 200 response to the get request.
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
        return render_template('gencode.html', moduleselected=False, lectureselected=False)

    else:
        if g.user:
            updatemanagedmodules()
            return render_template('gencode.html', moduleselected=False, lectureselected=False)

        return redirect(url_for('lecturersignin'))


@app.route("/selectmodule", methods=['GET', 'POST'])
def selectmodule():
    """ Endpoint used to generate a web page containing all the module lectures after a module is selected. """
    # Receiving data from the post request.
    module = request.form['module']
    # Retrieving the lectures for the week for the selected module...
    lectures = sort_lectures(get_week(), get_lectures(module), "Weekly")
    # Sanitising the lecture data so it is in a readable format.
    for lecture in lectures:

        lecture['Time'] = lecture['Time'].to_pydatetime()
        lecture['Time'] = lecture['Time'].time()
    # Providing a HTTP 200 response to the post request.
    return render_template('gencode.html', lectures=lectures, moduleselected=True, lectureselected=False)


@app.route("/selectlecture", methods=['GET', 'POST'])
def selectlecture():
    """ Endpoint used to generate a web page containing the lecture code for a lecture for students."""
    # Receiving data from the post request.
    lecture = request.form['lecture']
    # sending the lecture code to the web page.
    flash(lecture)
    # Providing a HTTP 200 response to the post request.
    return render_template('gencode.html', moduleselected=True, code=lecture, lectureselected=True)


def generatenewcode():
    """ Returns a six digit unique code. No parameters required. """
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))


# sourced from https://www.vitoshacademy.com/hashing-passwords-in-python/
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
    """ Method used to set the weeks in the Dundee University Semester, starting from the 16th of September"""
    dict_of_weeks = {}

    dict_of_weeks[1] = datetime.datetime.strptime("16-09-2019", "%d-%m-%Y")

    for i in range(2, 13):
        dict_of_weeks[i] = dict_of_weeks[i - 1] + datetime.timedelta(days=7)

    dict_of_weeks[13] = datetime.datetime.strptime("20-01-2020", "%d-%m-%Y")
    for i in range(14, 25):
        dict_of_weeks[i] = dict_of_weeks[i - 1] + datetime.timedelta(days=7)

    session['weeks'] = dict_of_weeks


def get_next_lecture(week):

    """ Method used to get all the lectures scheduled for the current week. """

    updatemanagedmodules()
    week_lectures = []
    # retrieving all the lectures for all the modules that the lecturer is supervising and sorting them by week.
    for x in session['supervised_modules']:

        week_lectures = week_lectures + get_lectures(x['ModuleID'])

    week_lectures = sort_lectures(get_week(), week_lectures, "Weekly")

    # Making sure that all the lectures are sorted by day.
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

    week_lectures = sort_lectures(get_week(), week_lectures, "Weekly")

    return week_lectures


@app.route('/sign_out')
def sign_out():
    session.pop('user', None)
    session.clear()
    logger.info("Successfully Signed Out")
    return render_template('homepage.html')


if __name__ == "__main__":

    app.run( threaded=True, debug=True)
