"""
Abbas Lawal
AC40001 Honours Project
BSc (Hons) Computing Science
University of Dundee 2019/20
Supervisor: Dr Craig Ramsay
All CODE IS ORIGINAL UNLESS STATED SO.
"""
# Necessary library imports
import binascii
import csv
import sqlite3
from sqlite3 import Error
import datetime
from datetime import timedelta
import hashlib
import logging
import os
import random
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

# Necessary set up so that the application can run properly and be deployed etc.
app = Flask(__name__)
app.secret_key = "supersecretkey"
# Setting
UPLOAD_FOLDER = os.path.dirname(os.path.realpath(__file__)) + "/Uploads"
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Wiping the log file every time the application is started.
if path.exists('logger.log'):
    os.remove('logger.log')
    print("Log file rotated.")

# Sourced and modified from stack overflow.
# https://stackoverflow.com/questions/8467978/python-want-logging-with-log-rotation-and-compression/41029671

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

file_path = os.path.abspath(os.path.dirname(__file__))
conn = sqlite3.connect(file_path + '/Database/database.db', check_same_thread=False, timeout=10)
cursor = conn.cursor()

# Used to make sure lecturers must be signed in before accessing certain pages for security.
@app.before_request
def before_request():

    g. user = None

    if 'user' in session:
        g.user = session['user']


@app.route("/")
@app.route("/Home")
def index():
    """ endpoint for displaying lecturer homepage, no POST requests needed. """

    # returning a response to the get request with a web page.
    return render_template('homepage.html')


@app.route("/lecturer_home")
def lecturer_home():
    """ endpoint for lecturer homepage, no POST requests needed. """

    if g.user:
        # getting the current week.
        set_week()
        # getting the upcoming lectures for the current week.
        lectures = get_next_lecture(get_week())
        # Getting notifications regarding individual student attendance.
        messages = attendance_flagging()
        # If there are no notifications then this is conveyed to the signed in lecturer.
        if len(messages) == 0:

            show_messages = False
            too_many_messages = False

        else:

            show_messages = True

            if len(messages) > 10:

                too_many_messages = True

            else:

                too_many_messages = False

        # Returning a response to the get request. Dynamic for every lecturer.
        return render_template('lecturer_home.html',
                               next_lecture=lectures, timetabled_days=check_timetabled_days(lectures),
                               lectures=lectures, show_messages=show_messages,
                               student_messages=messages, too_many_messages=too_many_messages)

    # returning user to homepage if they are not signed in.
    return redirect(url_for('lecturer_sign_in'))


def attendance_flagging():

    """ function used for flagging students with less than 50% attendance. """
    messages = []

    for item in session['supervised_modules']:

        lectures = get_lectures(item['ModuleID'])

        # Updating the current attendance to make sure the flagging is accurate.
        update_module_attendance(item['ModuleID'], retrieve_class_list(item['ModuleID']))
        # Retrieving the updated class list.
        students = retrieve_class_list(item['ModuleID'])

        for student in students:
            # checking the state of each students attendance and flagging if necessary.
            if int(float(student['Attendance'])) < int(float(50)):

                logger.info(student['FirstName'] + " " + student['LastName'] +
                            " Has less than 50% attendance for " + item['ModuleID'])

                messages.append(tuple((student['FirstName'] + " " + student['LastName'] +
                                       " Has less than 50% attendance for " + item['ModuleID'],
                                       student['MatricNum'], item['ModuleID'])))

            if int(float(student['Attendance'])) >= int(float(80)):

                logger.info(student['FirstName'] + " " + student['LastName'] + " Has more than 80% attendance for " +
                            item['ModuleID'])

            if int(float(student['Attendance'])) == int(float(100)):

                logger.info(student['FirstName'] + " " + student['LastName'] +
                            " Has 100% attendance for " + item['ModuleID'])

            else:

                logger.info(
                    student['FirstName'] + " " + student['LastName'] + " Has less than 80% attendance for "
                    + item['ModuleID'])

    # returning info on any students that have been flagged.
    return messages


@app.route("/redirect_to_student", methods=['POST'])
def redirect_to_student():

    """ Used as an intermediate to redirect lecturers from notifications to student stat pages."""
    # Setting a required session variable for the student stats page.
    session['moduleid'] = request.form['module_id']
    # Redirecting the lecturer to the students stat page.
    return redirect(url_for('student_stats', Student=request.form['student'], from_home=True))


@app.route("/send_email", methods=['POST'])
def send_email():

    """ function/endpoint used for sending students automated updates about their attendance. """

    # code sourced and modified from https://realpython.com/python-send-email/
    student = get_student_info(request.form['student'])
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = "abbas.uod.honours@gmail.com"  # sender email address.
    # If the student only exists for demonstration purposes then the email is sent to a spam page.
    if student['Email'] == 'abc123@dundee.ac.uk':
        receiver_email = 'spam.dundee.testing@gmail.com'
    # Password for email account, security is irrelevant as all email accounts in the function are not important.
    password = 'thisismypassword123'
    # Finding the students information using an SQL query.
    query = 'SELECT * FROM {} WHERE MatricNum={}'.format(session['moduleid'], student['MatricNum'])
    result = pd.read_sql(query, conn)
    attendance = result.to_dict('records')[0]['Attendance']

    # Finding the appropriate message to send to the student based on their attendance.
    # Note each flash is used to send a message to the UI...
    if 80 > attendance > 50:
        message = 'Subject:\n Hi there ' \
                  '\n This is a message to let you know that your attendance is below the university policy for {}.' \
                  ' \n Please contact the lecturer if you have any issues.'.format(session['moduleid'])

        logger.info("An email has been sent to " + student['FirstName'] + " " + student['LastName']
                    + " Regarding poor attendance.")
        flash("An email has been sent to " + student['FirstName'] + " " + student['LastName']
              + " Regarding poor attendance.")

    if attendance < 50:
        message = 'Subject:\n Hi there ' \
                  '\n This is a message to let you know that your attendance is extremely low for {}.' \
                  ' \n Please contact the lecturer if you have any issues.'.format(session['moduleid'])

        logger.info("An email has been sent to " + student['FirstName'] + " " + student['LastName'] +
                    " Regarding worrying attendance.")
        flash("An email has been sent to " + student['FirstName'] + " " + student['LastName'] +
              " Regarding worrying attendance.")
    if attendance >= 80:
        message = 'Subject:\n Hi there ' \
                  '\n Just a message to let you know that your attendance is whithin the university policy for {}!.' \
                  ' \n Please contact the lecturer if you have any issues/questions.'.format(session['moduleid'])

        logger.info("An email has been sent to " + student['FirstName'] + " " + student['LastName'] +
                    " Regarding good attendance.")
        flash("An email has been sent to " + student['FirstName'] + " " + student['LastName'] +
              " Regarding good attendance.")

    # Sending the email...
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)
    # redirecting to the class list management page.
    return redirect(url_for('student_stats', Student=request.form['student'], from_home=False))


@app.route("/lecturer_sign_in", methods=['POST', 'GET'])
def lecturer_sign_in():

    """ endpoint used to allow lecturers to sign into their accounts. """
    # Dealing with the POST request when lecturers attempt to sign in.
    if request.method == 'POST':

        # Signing out any currently signed in lecturers.
        session.pop('user', None)

        # Recieving the data from the POST request and checking to see if the account exists.

        lecturerid = request.form['lecturerid']
        password = request.form['Password']
        query = "SELECT * FROM Lecturers WHERE LecturerID=?"
        result = pd.read_sql(query, conn, params=(lecturerid,))
        lecturerinfo = result.to_dict('records')
        error = None
        if len(lecturerinfo) != 1:
            error = "Account does not exist"
            logger.info("Account does not exist")

            # returning the web page with an error if the account does not exist.
            return render_template('lecturer_sign_in.html', error=error)

        # Now checking if the password is correct...
        actual_pass = lecturerinfo[0]['Password']
        if checkpass(actual_pass, password) is True:
            # resetting any possible previous session data...
            session['user'] = lecturerid
            session['moduleinfo'] = []
            session['lectureinfo'] = []

            query = "SELECT * FROM Modules WHERE LecturerID=?"
            result = pd.read_sql(query, conn, params=(lecturerid,))
            lectureinfo = result.to_dict('records')

            for x in lectureinfo:

                if x['LecturerID'].strip() == session['user']:
                    session['moduleinfo'].append(x['ModuleID'])
            # Signing the lecturer into their account and redirecting them to their homepage.
            updatemanagedmodules()
            logger.info("Successfully Signed Into Lecturer Account")
            return redirect(url_for('lecturer_home'))

        else:

            error = "LecturerID or password is incorrect"
            logger.info("LecturerID or password is incorrect")
            # informing the lecturer that their password or ID is incorrect and that they should try again.
            return render_template('lecturer_sign_in.html', error=error)

    # Handling GET requests...
    else:

        if g.user:
            # return the lecturer to their homepage if they're already signed in.
            updatemanagedmodules()
            return redirect(url_for('lecturer_home'))
        # returning a reponse to the GET request with the lecturer sign in page.
        return render_template('lecturer_sign_in.html')


@app.route("/signup", methods=['POST', 'GET'])
def signup():

    """ endpoint used to allow lecturers to sign into their accounts. """

    # Handling POST requests involving users trying to sign in.
    if request.method == 'POST':

        notification = None
        # Recieving data from the POST Request.
        idnum = request.form['idnum']
        password = hash_password(request.form['password'])
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        type = request.form['lecturercheck']

        # Handling lecturers trying to sign up.
        if type == 'Lecturer':

            # Checking to see if the account already exists.
            query = "SELECT * FROM Lecturers WHERE LecturerID=?"
            result = pd.read_sql(query, conn, params=(idnum,))
            resultdict = result.to_dict('records')

            if len(resultdict) > 0:
                notification = "The ID already exists"
                logger.info("The ID already exists, Account Creation failed")
                # Throwing back an error if the accoiunt already exists and prompting users to try again.
                return render_template('signup.html', notification=notification)

            # creating the account if all requirements are satisfied...
            query = "INSERT INTO Lecturers (LecturerID, FirstName, LastName, Password) VALUES (?, ?, ? ,?);"
            cursor.execute(query, (idnum, fname, lname, password))
            conn.commit()
            notification = "account successfully created"
            logger.info("Lecturer account successfully created")

        # Handing students trying to sign up.
        else:
            # making sure the matriculation number meets all required requiremnts i.e. length.
            if len(idnum) != 9:
                notification = "Please enter a valid matriculation number"
                logger.info("Invalid Matriculation Number")
                # Throwing back an error if the matriculation number is not exactly 9 digits.
                return render_template('signup.html', notification=notification)

            # Checking to see if the account already exists.
            query = "SELECT * FROM Students WHERE MatricNum=?"
            result = pd.read_sql(query, conn, params=(idnum,))
            resultdict = result.to_dict('records')

            if len(resultdict) > 0:
                notification = "The ID already exists"
                print(resultdict)
                logger.info("Error, ID already exists")
                # Throwing back an error if the accoiunt already exists and prompting users to try again.
                return render_template('signup.html', notification=notification)

            # creating the account if all requirements are satisfied...
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

    """ intermediate endpoint used to allow lecturers to select a module lecture they wish to dislpay to a class."""

    if request.method == 'POST':
        # setting required session variables before redirecting.
        session['selected_module_lecture'] = request.form['module']
        # redirecting back to create lecture page.
        return render_template('create_lecture.html', modules=session['supervised_modules'], moduleselected=True)


@app.route("/create_lecture", methods=['GET', 'POST'])
def create_lecture():

    """ Endpoint/Page used to allow lecturers to create lecture sets for their modules."""
    # Handing post requests...
    if request.method == 'POST':

        # Retrieving and sanitising POST request data if required...
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

        # Creating a lecture in the database for each lecture requested by the lecturer...
        for x in range(first, last + 1):
            # converting the hour variable received from the POST request into a date/time object.
            hour = convert_time(time, weekday, x)

            query = "INSERT INTO Lectures (LectureID, ModuleID, LectureName, LectureLocation, " \
                    "LectureDuration, Week, Day, Time) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
            # executing and committing query.
            cursor.execute(query, (generatenewcode(), module, name, location, duration, x, weekday, hour))
            conn.commit()

        logger.info("Lecture set: " + weekday + " from week " + str(first) + " to " + str(last) + " at " +
                    location + " at " + str(hour) + " successfully created.")
        updatemanagedmodules()
        # Sending message to UI for lecturer...
        flash("Lecture successfully timetabled.")
        # returning response to POST request in form of a web page...
        return redirect(url_for('create_lecture'))

    # Handling get requests.

    else:
        # making sure that the web page can only be accessed if a lecturer is logged in,
        # otherwise redirecting to a sign in page.
        if g.user:

            return render_template('create_lecture.html', modules=session['supervised_modules'], moduleselected=False)

        return redirect(url_for('lecturer_sign_in'))


def convert_time(hour, day, week):

    """ Function used to convert time in string format to datetime obejects."""

    x = hour
    actual_day = 0
    updated_week = None
    # Keeping track of days using corresponding numbers...
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

    # Converting the time and day to a datetime object...
    updated_week = return_week(week)

    lecture_time = str(hour)

    updated_week = updated_week + timedelta(actual_day)

    updated_week = updated_week + timedelta(hours=int((lecture_time[:2])))
    # returning the new object...

    return updated_week


def return_week(week):

    """ Function used to return a dictionary of weeks corresponding to the Dundee University Semester. """

    dict_of_weeks = {}
    # adding key value pairs for the first semester.
    dict_of_weeks[1] = datetime.datetime.strptime("16-09-2019", "%d-%m-%Y")

    for i in range(2, 13):
        dict_of_weeks[i] = dict_of_weeks[i - 1] + datetime.timedelta(days=7)
    # adding key value pairs for the second semester.
    dict_of_weeks[13] = datetime.datetime.strptime("20-01-2020", "%d-%m-%Y")
    for x in range(14, 25):
        dict_of_weeks[x] = dict_of_weeks[x - 1] + datetime.timedelta(days=7)
    # returning the dictinoary of weeks.
    return dict_of_weeks[week]


def get_graph_info(module_id):

    """ Function used to return graph data for a line graph. """

    graph_data = []
    # getting every lecture for the module.
    lectures = get_lectures(module_id)
    # getting the real current week.
    week = int(get_week())

    # checking which semester it is and setting the relevant label.
    if week < 13:

        session['labels'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        for x in range(0, 12):

            pass
        # returning the graph data...
        return graph_data

    if week >= 13:

        session['labels'] = [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
        for x in range(13, 25):

            pass
        # returning the graph data...
        return graph_data


def get_lecture_attendance(lecture_id, class_list, module_id):

    """ Function used to caluclate the attendance for a lecture. """

    students_present = 0

    # Checking to see if the module string for each student indicates that they were present.

    lecture_id = lecture_id + '-1'
    for student in class_list:
        # if the student is present add 1 to the present count...
        if lecture_id in student['ModuleString']:

            students_present = students_present + 1
    # simple calculation to find percentage of students that were present...

    return int((students_present / len(class_list)) * 100)


@app.route("/update_office_docs", methods=['POST'])
def update_office_docs():

    """ Method used to update documents for the school office.
     This is ideally done automatically after each lecture but as a proof of concept
     This is done manually."""

    module_id = request.form['module_id']
    class_list = retrieve_class_list(module_id)

    if len(get_lectures(module_id)) is 0 or len(class_list) is 0:

        flash("Currently Nothing To Update The School Office, Try Again Later.")
        return redirect(url_for('module_options', module=session['moduleid']))

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
    # redirecting to the module options page.

    flash("School Office Docs Updated")
    return redirect(url_for('module_options', module=session['moduleid']))


@app.route("/module_options", methods=['GET', 'POST'])
def module_options():

    """ Endpoint used to manage module details such as class list etc."""

    # Handling post requests used to delete individual lectures.
    if request.method == 'POST':
        # retrieving data from the post request...
        lecture_id = request.form['Lecture']
        logger.info("Lecture deleted")
        # Deleting the lecture and reflecting changes this has caused...
        delete_lecture(lecture_id)
        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = get_lectures(session['moduleid'])
        # reloading the page...
        return redirect(url_for('module_options', module=session['moduleid']))

    # Handling Get requests...
    else:
        # checking if the user is signed in...
        if g.user:
            # retrieving data from the get request.
            module_id = request.args['module']
            session['moduleid'] = module_id
            getmoduleinfo(session['moduleid'])
            updatemanagedmodules()
            modulelectures = []

            # making sure that the right semester or week is displayed in the timetable...
            if 'sorted_lectures' in request.args:

                if request.args['sorted_lectures'] == 'Wrong_Semester':

                    modulelectures = []

                else:

                    lectures = request.args.getlist('sorted_lectures')
                    # sanitising datetime data so that it is displayed nicely.
                    for item in lectures:

                        item = item.replace("\'", "\"")
                        item = item.replace('Timestamp(','')
                        item = item.replace(')', '')
                        modulelectures.append(json.loads(item))

            else:

                lectures = get_lectures(module_id)
                # making sure that only the current weeks lectures are shown.
                modulelectures = sort_lectures(get_week(), lectures, "Weekly")

            logger.info("Retrieving module lectures from " + str(module_id) + " for the current week...")
            session['graph_datasets'] = []
            session['labels'] = []
            session['lecture_details'] = []
            # sorting the graph data...

            if get_week() is None:

                session['labels'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

            else:

                if int(get_week()) >= 13:

                    for item in modulelectures:

                        if item['Week'] > 12:

                            item['Week'] = item['Week'] - 12

                    session['labels'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

            # updating the modules attendance.
            update_module_attendance(module_id, retrieve_class_list(module_id))

            # checking to see if the graph should be displayed at all i.e. if no data it will not be displayed.
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
            # returning a response to the get request in the form of dynamic web page
            return render_template('module_options.html', moduleid=module_id, lectures=modulelectures,
                                   timetabled_days=check_timetabled_days(modulelectures),
                                   attendance=overall_attendance, show_graph=show_graph)
        # if the user is not signed in, they are automatically redirected to the sign in page.
        return redirect(url_for('lecturer_sign_in'))


def calculate_overall_attendance(module_id):

    """ Function used to calculate the overall average attendance of a module. """

    attendance = 0
    attendance_list = []
    student_sum = 0
    # retrieving the data of every student in the class list.
    class_list = retrieve_class_list(module_id)
    # getting a sum each students attendance.
    for student in class_list:

        student_sum = student['Attendance'] + student_sum
    # finding the attendance...
    attendance = int(student_sum/len(class_list))
    # returning the attendance.
    return attendance


def get_graph_data(module_id):

    """ Function used to  get and sort line graph data."""

    # partially sourced from stack overflow...
    # https://stackoverflow.com/questions/4091680/splitting-a-list-of-dictionaries-into-several-lists-of-dictionaries

    # getting all the lectures from the module.
    lectures = get_lectures(module_id)
    # retrieving the data of every student in the class list.
    class_list = retrieve_class_list(module_id)

    session['graph_datasets'] = []

    result = collections.defaultdict(list)
    # sorting the lectures by day.
    for d in lectures:
        result[d['Day']].append(d)

    result_list = list(result.values())

    # getting the attendance for each day the module has lectures and adding them in them to a dictionary.
    for item in result_list:

        temp_dict = {}
        temp_dict['graph_data'] = []

        for lecture in item:

            temp_dict['graph_data'].append(get_lecture_attendance(lecture['LectureID'], class_list, module_id))

        temp_dict['Day'] = item[0]['Day']
        session['graph_datasets'].append(temp_dict)


@app.route("/sort_timetable", methods=['POST'])
def sort_timetable():

    """ Endpoint used to return sorted lectures into weeks or semesters.
     Only takes POST REQUESTS."""

    # Checking the desired type of sorting.
    if "semester1" in request.form:

        # sorting the lectures to retrieve the first semester lectures.
        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = sort_lectures(12, get_lectures(session['moduleid']), "Semester1")
        logger.info("Sorting lectures in " + str(session['moduleid']) + " by Semester 1")

        if len(modulelectures) == 0:

            modulelectures = "Wrong_Semester"

        # redirecting to the module options page...
        return redirect(url_for('module_options', module=session['moduleid'], sorted_lectures=modulelectures))

    # Checking the desired type of sorting.
    if "semester2" in request.form:

        # sorting the lectures to retrieve the second semester lectures.
        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = sort_lectures(13, get_lectures(session['moduleid']), "Semester2")
        logger.info("Sorting lectures in " + str(session['moduleid']) + " by Semester 2")

        if len(modulelectures) == 0:

            modulelectures = "Wrong_Semester"

        # redirecting to the module options page...
        return redirect(url_for('module_options', module=session['moduleid'], sorted_lectures=modulelectures))

    # Checking the desired type of sorting.
    if "currentweek" in request.form:

        # sorting the lectures to retrieve the current weeks lectures.
        getmoduleinfo(session['moduleid'])
        updatemanagedmodules()
        modulelectures = sort_lectures(get_week(), get_lectures(session['moduleid']), "Weekly")
        logger.info("Sorting lectures in " + str(session['moduleid']) + " by current week")

        # redirecting to the module options page...
        return redirect(url_for('module_options', module=session['moduleid'], sorted_lectures=modulelectures))


def sort_lectures(week, lectures, type):

    """ Function used to sort lecture sets."""

    filtered_lectures = []

    if week is None:

        return filtered_lectures

    # sorting lectures by week.
    if type == "Weekly":

        week = int(week)
        filtered_lectures = []
        for item in lectures:

            if item['Week'] == week:

                filtered_lectures.append(item)

    # sorting lectures by semester 1.
    if type == "Semester1":

        week = int(week)

        for item in lectures:

            if int(item['Week']) <= week:
                filtered_lectures.append(item)

    # sorting lectures by semester 2.
    if type == "Semester2":

        week = int(week)

        for item in lectures:

            if item['Week'] >= week:
                filtered_lectures.append(item)

    # returning the sorted/filtered lectures.
    return filtered_lectures


def delete_lecture(lecture_id):

    """ Function used to delete a single lecture"""

    # deleting the lecture.
    cursor.execute("DELETE FROM Lectures WHERE LectureID=?", (lecture_id,))


@app.route("/student_stats", methods=['GET', 'POST'])
def student_stats():

    """ Endpoint/Function used to handle individual student statistics page. """

    # handling post requests.
    if request.method == 'POST':
        # no post requests are required so this is passed...
        pass

    # handling Get requests.
    else:

        # making sure users must be signed in to see the page.
        if g.user:

                # retreiving the students data and setting it to a session variable.
                matric_num = request.args['Student']
                session['Student'] = get_student_info(matric_num)

                # making sure the application knows how the page was reached so the back button redirects properly.
                if 'from_home' in request.args:

                    from_home = True

                else:

                    from_home = False

                # retrieving the modules lectures...
                session['module_lectures'] = get_lectures(session['moduleid'])
                # retrieving the students expected lectures.
                expected_lectures = get_expected_lectures(session['Student'], session['moduleid'])

                # checking whether if there is any point in showing a graph or not.
                if len(expected_lectures) == 0:
                    # displaying the page without graph data if there is no need to show it.
                    return render_template('student_stats.html', show_stats=False)
                # retrieving the students attendance for the class.
                attendance = get_class_attendance(expected_lectures)

                # retrieving pie chart data for the student.
                session['labels'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

                # sorting the absent and present lectures for the chart.
                chart_data = [0, 0]
                for lecture in expected_lectures:

                    if lecture['Attendance']:

                        chart_data[0] = chart_data[0] + 1
                    else:

                        chart_data[1] = chart_data[1] + 1

                # preparing a small message regarding the students attendance.

                if attendance >= 80:

                    note = "This students attendance is " + str(attendance) + " and is no cause for concern."

                else:

                    note = "This students attendance is " + str(attendance) + " and is cause for concern."
                # displaying the page with dynamic data...
                return render_template('student_stats.html', show_stats=True, attendance_info=expected_lectures,
                                       student_statement=note, from_home=from_home, chart_data=chart_data)
        else:
            # if the user is not signed in then they are automatically redirected to the sign in page.
            return redirect(url_for('lecturer_sign_in'))


def get_expected_lectures(student, module_id):

    """ Function used to get every lecture a student is expected to have attended. """

    # retrieving a modules lectures.
    lectures = get_lectures(module_id)
    expected_lectures = []
    sorted_list = []
    # parsing the students sub string to get individual lectures...
    sub_strings = [x.strip() for x in student['ModuleString'].split(';')]

    for sub_string in sub_strings:

        if module_id in sub_string:

            module_lectures = sub_string

    module_lectures = module_lectures[8:]

    module_sub_strings = [x.strip() for x in module_lectures.split(',')]

    # checking to see what lectures the student has went to and what lectures they have missed.

    for lecture in module_sub_strings:

        if '-1' in lecture:

            expected_lectures.append([(lecture.replace('-1', '')), True])

        else:

            expected_lectures.append([(lecture.replace('-0', '')), False])

    # discounting lectures that have not happened yet...
    for expected_lecture in expected_lectures:

        for lecture in session['module_lectures']:

            time = datetime.datetime.strptime(lecture['Time'], '%Y-%m-%d %H:%M:%S')

            if str(lecture['LectureID']) == str(expected_lecture[0]) and has_happened(time) is True:

                new_dict = lecture
                new_dict['Attendance'] = expected_lecture[1]
                sorted_list.append(new_dict)

    # returning the list of expected lectures...
    return sorted_list


def has_happened(date):

    """ Function used to check if a lecture has happened yet."""

    past = date
    present = datetime.datetime.now()

    # returning true or false regarding if the given time has passed or not.
    return past < present


def get_class_attendance(expected_lectures):

    """ Function used to return the attendance of a moodule
    given a list of lectures that have or have not been attended"""

    # list comprehension to find how many lectures were attended.
    count = Counter(x['Attendance'] for x in expected_lectures)
    # finding the percentage.
    percentage = count[True]/(len(expected_lectures)) * 100
    # cleaning up the percentage and returning it.
    return int(percentage)


@app.route("/delete_module", methods=['POST'])
def delete_module():

    """ Endpoint/Function used to delete a module. """
    # getting the POST requests data.
    module_id = request.form['Module']

    # Deleting modules details completely from the database.
    cursor.execute("DELETE FROM Modules WHERE ModuleID=?", (module_id,))

    cursor.execute("DELETE FROM Lectures WHERE ModuleID=?", (module_id,))

    # reflecting these changes across the rest of the system.
    session['moduleid'] = module_id
    getmoduleinfo(module_id)
    updatemanagedmodules()
    logger.info("Module Deleted")

    # displaying the module management page.
    return render_template('modulemanager.html', modules=session['supervised_modules'])


def get_lectures(module):

    """ Function used to get the lectures of a module. """

    # performing the query.
    query = "SELECT * FROM Lectures WHERE ModuleID=? ORDER BY Time ASC"
    # converting the results into a list of dictionaries and returning it.
    result = pd.read_sql(query, conn, params=(module,))
    return result.to_dict('records')


def check_timetabled_days(modulelectures):

    """ Function used to check what days have lectures and which do not."""
    timetabled_days = {'Monday': False, 'Tuesday': False, 'Wednesday': False, 'Thursday': False, 'Friday': False}

    # if a lecture is in a day then the keys day is set to True.
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

    # returning a dictionary highlighting which days have lectures.
    return timetabled_days


def return_module_info(module_id):
    """ Function used to retrieve the information of a module """

    query = "SELECT * FROM Modules WHERE ModuleID=?"
    result = pd.read_sql(query, conn, params=(module_id,))
    # converting the results into a list of dictionaries and returning it.
    return result.to_dict('records')[0]


def getmoduleinfo(module_id):

    """ Function used to retrieve the information of a module """

    query = "SELECT * FROM Modules WHERE ModuleID=?"
    result = pd.read_sql(query, conn, params=(module_id,))
    # converting the results into a list of dictionaries and setting it to a session variable.
    session['moduleinfo'] = result.to_dict('records')[0]


def allowed_file(filename):
    """ Function used to check if a file type is allowed or not."""

    # Returning true if allowed, false otherwise.
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

    """ Function used to check if a student is in a class list or not."""
    # perfroming a query.
    query = 'SELECT * FROM {} WHERE MatricNum={}'.format(module_id, int(matric_num))
    result = pd.read_sql(query, conn)
    student = result.to_dict('records')
    # if the query returns 1 then true is returned by the function, otherwise false.
    return len(student) == 1


@app.route("/search_class_list", methods=['POST'])
def search_class_list():

    """ Function/Endpoint used to check search for a student in class list."""

    # retrieving data from the POST request.
    keyword = request.form['keyword']
    students = []

    # automatically checking if a keyword or matriculation number should be searched...
    if str.isdigit(keyword):

        # performing the query.
        query = "SELECT * FROM Students WHERE MatricNum=?"
        result = pd.read_sql(query, conn, params=(int(keyword),))
        students = result.to_dict('records')
    else:
        students = []
        for word in keyword.split():
        # performing the query.
            query = 'SELECT * FROM Students WHERE FirstName LIKE "%{}%" OR LastName LIKE "%{}%"'.format(word, word)
            result = pd.read_sql(query, conn)
            students = students + result.to_dict('records')

    if len(students) == 0:
        # if nothing is found then an error is thrown back to the lecturer.
        flash("No Student Found")
        return redirect(url_for('class_list_management', module_id=session['moduleid']))

    # if one or more students are found, then the page is reloaded and the found students are shown...
    else:

        class_list = []

        for student in students:

            if check_if_in_class_list(session['moduleid'], student['MatricNum']):

                student['Attendance'] = get_student_attendance(student['MatricNum'], session['moduleid'])
                class_list.append(student)
        print(class_list)



        # displaying the web page.
        return render_template('class_list_management.html', exists=True, class_list=class_list, lectures_exist=True)


@app.route("/class_list_management", methods=['GET', 'POST'])
def class_list_management():

    """ Function/Endpoint used to handle class list management. """

    # Handling POST requests to add individual students to class lists.
    if request.method == 'POST':
        # retrieving data from the post requests

        f_name = request.form['f_name']
        l_name = request.form['l_name']
        matric_num = request.form['matric_num']

        logger.info("Attempting to add " + f_name + ' ' + l_name + ' to class list: ' + session['moduleid'])

        # checking that the student actually exists.
        if get_student_info(matric_num) is None:

            flash("Error, this student does not seem to exist.")
            logger.info("Error, this student does not seem to exist.")
            # if the student does not exist an error is thrown back.
            return redirect(url_for('class_list_management', module_id=session['moduleid']))

        # checking that the student isn't already in the class list.
        if check_if_in_class_list(session['moduleid'], matric_num) is True:

            logger.info("Abandoning... student is already in the class list")
            flash("Error, this student is already in the class list!")
            session['class_list'] = retrieve_class_list(session['moduleid'])
            # if the student is already in the class then an error is thrown back.
            return redirect(url_for('class_list_management', module_id=session['moduleid']))

        else:
            # if all conditions are satisfied then the student is added to the class list.
            create_class_list(matric_num, session['moduleid'])
            # reloading the page with the new student.
            return redirect(url_for('class_list_management', module_id=session['moduleid']))

    else:
        # Handling GET requests.
        if g.user:
            # retrieving data from the get request.
            module_id = request.args['module_id']
            session['moduleid'] = module_id
            # retrieving the class list.
            class_list = retrieve_class_list(module_id)
            exists = True

            # checking if the class list is empty so the page knows what to show.
            if len(class_list) == 0:

                exists = False
                class_list = None

            else:
                # updating the module attendance.
                update_module_attendance(module_id, class_list)

                # getting individual attendance for students.
                for student in class_list:

                    student['Attendance'] = get_student_attendance(student['MatricNum'], module_id)

            # checking if there are any lectures for the class yet.

            if get_lectures(module_id) == []:

                lectures_exist = False

            else:

                lectures_exist = True
            # displaying the web page/returning a response to the get request.
            return render_template('class_list_management.html', exists=exists, class_list=class_list,
                                   lectures_exist=lectures_exist)

        # redirecting to the sign in page if the lecturer is not already signed in.
        return redirect(url_for('lecturer_sign_in'))


def get_student_attendance(matric_num, module_id):

    """ Function used to calculate an individual students attendance. """

    # performing the query.
    query = 'SELECT Attendance FROM {} WHERE MatricNum={}'.format(module_id, matric_num)
    result = pd.read_sql(query, conn)
    student = result.to_dict('records')

    # returning the students attendance from their record.
    return student[0]['Attendance']


def update_module_attendance(module_id, class_list):

    """ Function used to update the attendance for every student in the module. """

    session['module_lectures'] = get_lectures(module_id)

    expected_lectures = []
    # sorting each lecture to make sure lectures that have not happened are not taken into account.
    for lecture in session['module_lectures']:

        if has_happened(datetime.datetime.strptime(lecture['Time'], '%Y-%m-%d %H:%M:%S')) is True:
            expected_lectures.append(lecture)
    # updating the attendance for every student in the module.
    for student in class_list:

        expected_lectures = get_expected_lectures(student, module_id)

        student_expected_lectures = expected_lectures
        # checking what lectures each student was present in.
        for lecture in student_expected_lectures:

            if lecture['LectureID'] + '-1' in student['ModuleString']:
                lecture['Attendance'] = True

            else:

                lecture['Attendance'] = False

        # updating each students attendance in the database.
        query = 'UPDATE {} set Attendance={} WHERE MatricNum={}'\
            .format(module_id, get_class_attendance(student_expected_lectures), student['MatricNum'])

        cursor.execute(query)
        conn.commit()


def get_student_info_basic(matric_num):

    """ Function used to retrieve only the first, last name and matriculation of a student. """

    # perfroming the query...
    query = "SELECT FirstName, LastName FROM Students WHERE MatricNum=?"
    result = pd.read_sql(query, conn, params=(int(matric_num),))
    student = result.to_dict('records')

    # if nothing is found then None is returned otherwise the students information is returned.
    if student == []:

        return None

    else:

        return student[0]


@app.route("/remove_from_class_list", methods=['POST'])
def remove_from_class_list():

    """ Function/Endpoint used to remove a student from a class list."""

    student_id = request.form['Student']

    logger.info("attempting to remove " + str(student_id) + " from class list...")
    # removing the student from the module class list table in the database.
    query = 'DELETE FROM {} WHERE MatricNum={};'.format(session['moduleid'], student_id)
    cursor.execute(query)
    conn.commit()

    # parsing the students module string to remove the expected lectures...
    sub_strings = [x.strip() for x in get_student_info(student_id)['ModuleString'].split(';')]

    for sub_string in sub_strings:

        if sub_string == '':

            sub_strings.remove(sub_string)

    for sub_string in sub_strings:

        if session['moduleid'] in sub_string:
            sub_strings.remove(sub_string)

    # joining together the new module string with unnecessary lectures removed.
    module_string = ';' + ';'.join(sub_strings)

    # updating the student in the students table in the database.
    query = 'UPDATE Students SET ModuleString={} WHERE MatricNum={};'.format("'" + module_string + "'", "'" + str(student_id) + "'")
    cursor.execute(query)

    student = get_student_info(student_id)
    logger.info(student['FirstName'] + " " + student['LastName'] + " Removed From " + session['moduleid'])
    # redirecting to the class list management web page.
    return redirect(url_for('class_list_management', module_id=session['moduleid']))


def retrieve_class_list(module_id):
    """ Function used to retrieve a class list from the database"""

    class_list = []
    # performing the query and converting it into a list of dictionaries.
    query = 'SELECT {}.MatricNum, {}.Attendance, Students.FirstName,Students.LastName, Students.ModuleString' \
            ' FROM {} INNER JOIN Students ON {}.MatricNum=Students.MatricNum;'.\
        format(module_id, module_id, module_id, module_id)
    result = pd.read_sql(query, conn)
    students = result.to_dict('records')
    # returning the list of students.
    return students


def create_class_list(matric_num, module_id):

    """ Function used to add a student to a class list."""

    student = get_student_info(matric_num)
    lectures = get_lectures(module_id)

    # checking that the student isn't already in the class list.
    if check_if_in_class_list(module_id, matric_num) is False:
        # adding the student to the module class list table in the database.
        query = 'INSERT INTO {}(MatricNum, Attendance) VALUES (?, ?);'.format(module_id)
        cursor.execute(query, (matric_num, 0))
        conn.commit()

        student_string = str(student['ModuleString']) + ";" + str(module_id) + ":"
        # adding lectures to the student module string.
        for lecture in lectures:

            student_string = student_string + lecture['LectureID'] + "-" + str(0) + ','

        student_string = student_string[:-1]
        # updating the students module string in the database.
        query = 'UPDATE Students SET ModuleString={} WHERE MatricNum={};'.format("'" + student_string + "'", "'" + str(matric_num) + "'")

        logger.info(student['FirstName'] + " " + student['LastName'] + " Added To Class list")

        cursor.execute(query)
        conn.commit()

    else:
        # logging that the student is already in the class list and doing nothing.
        logger.info(student['FirstName'] + " " + student['LastName'] + " is already in the class list.")


def get_student_info(matric_num):

    """ Function used to get all a students info"""

    # performing the query and converting it to a list of dictionaries.
    query = "SELECT * FROM Students WHERE MatricNum=?"
    result = pd.read_sql(query, conn, params=(int(matric_num),))
    student = result.to_dict('records')
    # if the query returns nothing then return none, otherwise return the student.
    if len(student) == 0:

        return None

    else:

        return student[0]


@app.route("/modulemanagement", methods=['GET', 'POST'])
def modulemanagement():

    """ Function/Endpoint used to manage module creation"""

    # Handling POST requests...
    if request.method == 'POST':
        # retrieving the data from the POST request.
        moduleid = request.form['moduleid']
        modulename = request.form['modulename']

        # checking the module ID doesnt already exist.
        if check_duplicate('Modules', 'ModuleID', moduleid):
            error = "Error, module ID already exists, please choose another."
            logger.info("Error, module ID already exists, please choose another.")
            flash("Error, module ID already exists, please choose another.")
            # throwing back an error if the ID exists.

            if len(session['supervised_modules']) == 0:

                modules_display = False

            else:

                modules_display = True

            return render_template('modulemanager.html', modules=session['supervised_modules'], Notification=error, modules_display=modules_display)

        # checking the module name doesnt already exist.
        if check_duplicate('Modules', 'ModuleName', modulename):
            error = "Error, module ID already exists, please choose another."
            logger.info("Error, module names cannot be duplicated...")
            flash("Error, module name already exists, please choose another")
            # throwing back an error if the name exists.

            if len(session['supervised_modules']) == 0:

                modules_display = False

            else:

                modules_display = True

            return render_template('modulemanager.html', modules=session['supervised_modules'], Notification=error, modules_display=modules_display)

        # checking the module ID is the correct length
        if len(moduleid) != 7:

            error = "Error, module ID is the wrong length."
            logger.info("Error, module ID is the wrong length")
            flash("Error, module ID is the wrong length ")
            # throwing back an error if the id length is not the correct length.

            if len(session['supervised_modules']) == 0:

                modules_display = False

            else:

                modules_display = True
            return render_template('modulemanager.html', modules=session['supervised_modules'], Notification=error,modules_display=modules_display)

        # creating the module table in the database along with adding the module to the modules table.
        query = "INSERT INTO Modules(ModuleID, ModuleName, LecturerID) VALUES (?, ?, ?);"
        cursor.execute(query, (moduleid, modulename, session['user']))
        conn.commit()

        query = 'CREATE TABLE {} (MatricNum char(9), Attendance int);'.format(moduleid)

        cursor.execute(query)
        conn.commit()

        updatemanagedmodules()
        logger.info(str(moduleid) + " : " + str(modulename) + " successfully created.")
        # reloading the page.
        return redirect(url_for('modulemanagement'))

    # handling GET requests.
    else:
        # making sure users are signed in otherwise redirecting to sign in page.
        if g.user:

            # checking to see if there are any modules to be displayed.
            updatemanagedmodules()
            if len(session['supervised_modules']) == 0:

                modules_display = False

            else:

                modules_display = True
            # returning a request to the get request in the from of a web page.
            return render_template('modulemanager.html', modules=session['supervised_modules'], modules_display=modules_display)

        return redirect(url_for('lecturer_sign_in'))


def updatemanagedmodules():

    """ Function used to keep track of the modules currently supervised by the user."""

    # perfroming the query and converting the results to a list of dictionaries.
    query = "SELECT * FROM Modules WHERE LecturerID=?"
    result = pd.read_sql(query, conn, params=(session['user'],))
    # setting a session variable to a list of supervised modules.
    print(result.to_dict('records'))
    session['supervised_modules'] = result.to_dict('records')


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


@app.route("/gencode", methods=['GET', 'POST'])
def gencode():

    """ Function/Endpoint used to display the code generation page."""

    if request.method == 'POST':
        modulecode = request.form['module']
        # Providing a HTTP 200 response to the get request.
        return render_template('gencode.html', moduleselected=False, lectureselected=False)

    # making sure that teh user is logged in otherwise, redirecting to the sign in page.
    else:
        if g.user:
            updatemanagedmodules()
            # Providing a HTTP 200 response to the get request.
            if len(session['supervised_modules']) is 0:

                modules_exist = False
            else:
                modules_exist = True

            return render_template('gencode.html', moduleselected=False,
                                   lectureselected=False, modules_exist=modules_exist)

        return redirect(url_for('lecturer_sign_in'))


@app.route("/selectmodule", methods=['GET', 'POST'])
def selectmodule():
    """ Endpoint used to generate a web page containing all the module lectures after a module is selected. """
    # Receiving data from the post request.
    module = request.form['module']
    # Retrieving the lectures for the week for the selected module...
    lectures = get_lectures(module)
    # Sanitising the lecture data so it is in a readable format.
    for lecture in lectures:

        lecture['Time'] = datetime.datetime.strptime(lecture['Time'], '%Y-%m-%d %H:%M:%S')
        lecture['Time'] = lecture['Time'].time()
    # Providing a HTTP 200 response to the post request.
    return render_template('gencode.html', lectures=lectures, moduleselected=True, lectureselected=False, modules_exist=True)


@app.route("/selectlecture", methods=['GET', 'POST'])
def selectlecture():
    """ Endpoint used to generate a web page containing the lecture code for a lecture for students."""
    # Receiving data from the post request.
    lecture = request.form['lecture']
    # sending the lecture code to the web page.
    flash(lecture)
    # Providing a HTTP 200 response to the post request.
    return render_template('gencode.html', moduleselected=True, code=lecture, lectureselected=True, modules_exist=True)


def generatenewcode():
    """ Returns a six digit unique code. No parameters required. """
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))


def checkpass(stored_password, provided_password):
    """Verify a stored password against one provided by user"""
    # sourced from https://www.vitoshacademy.com/hashing-passwords-in-python/
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
    # sourced from https://www.vitoshacademy.com/hashing-passwords-in-python/
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                  salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


def check_duplicate(table_name, field, unique_key):
    """Function used to check duplicate records in a table."""
    query = ("SELECT * FROM %s WHERE %s=?" % (table_name, field))
    result = pd.read_sql(query, conn, params=(unique_key,))
    tableinfo = result.to_dict('records')

    # returning True if there is a duplicate otherwise returning false.
    if len(tableinfo) > 0:

        return True

    else:

        return False


def get_week():
    """Function for getting the current week in the dundee university semester. """

    # getting the current day in real life.
    today = datetime.datetime.today()

    # getting the matching week...
    for key, value in session['weeks'].items():

        if value.isocalendar()[1] == today.isocalendar()[1] and value.year == today.year:
            # returning the week.
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

    if get_week() is None:
        logging.info("Semester Is Over")


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

    """Function for signing out lecturers."""
    # Deleting all session data.
    session.pop('user', None)
    session.clear()
    logger.info("Successfully Signed Out")
    return render_template('homepage.html')


if __name__ == "__main__":

    app.run(host="0.0.0.0", threaded=True, port=5000)
