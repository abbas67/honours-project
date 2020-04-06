"""
Abbas Lawal
AC40001 Honours Project
BSc (Hons) Computing Science
University of Dundee 2019/20
Supervisor: Dr Craig Ramsay
All CODE IS ORIGINAL UNLESS STATED SO.

The Purpose of this script is to load sample data into the system.
"""


import csv
import json
import hashlib, binascii, os
import datetime
from datetime import timedelta
import random,string
from random import randint
from os import path
from dbconn import connect
import pandas as pd
import pyodbc
import shutil

drivers = [item for item in pyodbc.drivers()]
driver = drivers[-1]
server = 'Zeno.computing.dundee.ac.uk'
database = 'abbaslawaldb'
uid = 'abbaslawal'
pwd = 'abc2019ABL123..'

params = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}'
conn = pyodbc.connect(params)
cursor = conn.cursor()


def clean_data():

    with open('sample_names.csv', 'r') as csvfile, open('sample_names.json', 'w') as jsonfile:

        fieldnames = ("first_name", "last_name", "company_name", "address", "city", "county", "state", "zip", "phone1", "phone2", "email", "web")
        reader = csv.DictReader(csvfile, fieldnames)

        for row in reader:
            json.dump(row, jsonfile)
            jsonfile.write('\n')


def get_class_names():

    class_names = []
    with open("class_names.txt", 'r') as file:

        for line in file:

            class_names.append(line.strip())

    return class_names


def load_data():

    sample_name_list = []
    with open('sample_names.json', 'r') as jsonfile:

        for line in jsonfile:
            sample_name_list.append(json.loads(line))

    for x in sample_name_list:

        x['MatricNum'] = gen_id()

        x['LecturerID'] = gen_username(x['first_name'], x['last_name'] )

    return sample_name_list


def insert_data(sample_data, class_names):

    cursor = connect()
    students = []

    for x in sample_data[250:500]:

        students.append(insert_students(cursor, x))


    print("Students Loaded")

    counter = 0
    updated_list = []

    #list_of_indexes = [, [51, 100], [101, 150], [151, 200],[201, 250] ]
    list_of_students = []


    # print(students[0:50])
    # print(students[51:100])
    # print(students[101:150])

    student_list = []
    for x in students[0:50]:

        student_list.append(x)

    list_of_students.append(student_list)

    student_list = []
    for x in students[51:100]:

        student_list.append(x)

    list_of_students.append(student_list)

    student_list = []
    for x in students[101:150]:

        student_list.append(x)

    list_of_students.append(student_list)

    student_list = []
    for x in students[151:200]:

        student_list.append(x)

    list_of_students.append(student_list)

    student_list = []
    for x in students[201:251]:

        student_list.append(x)

    list_of_students.append(student_list)

    for index, value in enumerate(sample_data[200:205]):

        print(list_of_students)
        value['Module_1'] = class_names[counter]
        value['Module_2'] = class_names[counter + 1]
        counter = counter + 2

        insert_lecturers(cursor, value)
        insert_module(cursor, value, list_of_students[index])

    print("Lecturers and relevant Modules Loaded")


def insert_module(cursor, sample_data, students):

    new_students = []
    final_list = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    locations = ["Seminar Room", "QMB", "Dalhousie", "Carnelly", "Harris"]
    time = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
    name = ["Lecture", "Seminar", "Lab", "Tutorial"]

    module_ID = ('AC' + (''.join(random.sample('0123456789', 5))))

    query = "INSERT INTO Modules(ModuleID, ModuleName, LecturerID) VALUES (?, ?, ?);"
    cursor.execute(query, (module_ID, sample_data['Module_1'], sample_data['LecturerID']))
    cursor.commit()

    query = 'CREATE TABLE {} (MatricNum char(9), Attendance int);'.format(module_ID)
    cursor.execute(query)
    conn.commit()

    for i in range(2):

        lecture_name = random.choice(name)
        lecture_location = random.choice(locations)
        day = random.choice(days)

        for x in range(1, 12 + 1):

            lecture_time = convert_time(random.choice(time), day, x)

            query = "INSERT INTO Lectures (LectureID, ModuleID, LectureName, LectureLocation, LectureDuration, Week, Day, Time ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
            print(generatenewcode(), module_ID, lecture_name, lecture_location, x, day, lecture_time)

            cursor.execute(query, (generatenewcode(), module_ID, lecture_name, lecture_location, randint(1, 4), x, day, lecture_time))
            cursor.commit()

    print("Semester 1 is timetabled")

    for student in students[:50]:

        new_students.append(add_to_class_list(student, module_ID))

    module_ID = ('AC' + (''.join(random.sample('0123456789', 5))))

    query = "INSERT INTO Modules(ModuleID, ModuleName, LecturerID) VALUES (?, ?, ?);"
    cursor.execute(query, (module_ID, sample_data['Module_2'], sample_data['LecturerID']))
    cursor.commit()

    query = 'CREATE TABLE {} (MatricNum char(9), Attendance int);'.format(module_ID)
    cursor.execute(query)
    conn.commit()

    for i in range(2):
        lecture_name = random.choice(name)
        lecture_location = random.choice(locations)
        day = random.choice(days)

        for x in range(13, 24 + 1):

            lecture_time = convert_time(random.choice(time), day, x)

            query = "INSERT INTO Lectures (LectureID, ModuleID, LectureName, LectureLocation, LectureDuration, Week, Day, Time ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
            print(generatenewcode(), module_ID, lecture_name, lecture_location, x, day, lecture_time)

            cursor.execute(query, (generatenewcode(), module_ID, lecture_name, lecture_location, randint(1, 4), x, day, lecture_time))
            cursor.commit()

    print("Semester 2 is timetabled")

    for student in new_students[:50]:

        add_to_class_list(student, module_ID)


def add_to_class_list(student, module_id):

    lectures = get_lectures(module_id)
    x = [0, 1, 1]


    query = 'INSERT INTO {}(MatricNum, Attendance) VALUES (?, ?);'.format(module_id)
    cursor.execute(query, (student['MatricNum'], 0))
    conn.commit()

    student_string = ";" + str(module_id) + ":"

    print(str("Old String: ") + str(student['ModuleString']))
    for lecture in lectures:

        student_string = student_string + lecture['LectureID'] + "-" + str(random.choice(x)) + ','

    student_string = student_string[:-1]

    student_string = student_string + student['ModuleString']

    student['ModuleString'] = student_string

    print(str("New String: ") + str(student_string))

    query = 'UPDATE Students SET ModuleString={} WHERE MatricNum={};'.format("'" + student_string + "'", "'" + str(student['MatricNum']) + "'")

    cursor.execute(query)
    conn.commit()

    return student


def insert_students(cursor, sample_data):

    query = "INSERT INTO Students (MatricNum, FirstName, LastName, Password, ModuleString, Email) VALUES (?, ?, ? ,?, ?, ?);"
    cursor.execute(query, (sample_data['MatricNum'], sample_data['first_name'], sample_data['last_name'], hash_password('password123'), '', 'abc123@dundee.ac.uk'))
    json_string = str('{ "MatricNum" : ' + str(sample_data['MatricNum']) + ', "FirstName" : "' + str(sample_data['first_name']) + '", "LastName" : "' + str(sample_data['last_name'])  + '", "ModuleString" : "", ' + " "  + '"Email"' + ":" + '"abc123@dundee.ac.uk"' + '}')
    # print(json_string)
    return json.loads(json_string)


def insert_lecturers(cursor, sample_data):

    query = "INSERT INTO Lecturers (LecturerID, FirstName, LastName, Password) VALUES (?, ?, ? ,?);"
    cursor.execute(query, (sample_data['LecturerID'], sample_data['first_name'], sample_data['last_name'], hash_password('password123')))
    print(sample_data['LecturerID'], sample_data['first_name'], sample_data['last_name'], hash_password('password123'))
    cursor.commit()


def generatenewcode():

    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))


def hash_password(password):
    """Hash a password for storing."""
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')



def gen_id():

    return randint(100000000, 999999999)


def gen_username(first_name, last_name):

    return first_name[:1] + "." + last_name + str(randint(100, 999))


def clear_table():


    query = "SELECT * FROM  Modules"
    result = pd.read_sql(query, conn)
    modules = result.to_dict('records')

    cursor = connect()
    cursor.execute("TRUNCATE TABLE Students")
    cursor.commit()

    cursor.execute("TRUNCATE TABLE Lecturers")
    cursor.commit()

    cursor.execute("TRUNCATE TABLE Lectures")
    cursor.commit()

    for module in modules:

        query = 'DROP Table {};'.format(module['ModuleID'])
        cursor.execute(query)
        cursor.commit()

    cursor.execute("TRUNCATE TABLE Modules")
    cursor.commit()


def convert_time(hour, day, week):

    # print(hour)
    # print(day)
    # print(week)


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


def get_lectures(module):

    query = "SELECT * FROM Lectures WHERE ModuleID=? ORDER BY Time ASC"

    result = pd.read_sql(query, conn, params=(module,))

    return result.to_dict('records')


def create_mock_data():

    query = "SELECT top 25 * FROM Students;"
    print(query)
    result = pd.read_sql(query, conn)
    students = result.to_dict('records')

    with open('MOCK_DATA.csv', 'w') as file:

        file.write('MatricNum,FirstName,LastName')

        for student in students:
            print(student)
            file.write('\n' + str(student['MatricNum']) + ',' + student['FirstName'] + ',' + student['LastName'])


if __name__ == "__main__":

    clear_table()
    sample_data = load_data()
    updated_students = []
    insert_data(sample_data, get_class_names())
    create_mock_data()