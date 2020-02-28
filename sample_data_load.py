import csv
import json
import hashlib, binascii, os
import random,string
from random import randint
from os import path
from dbconn import connect
import pandas as pd
import pyodbc
import shutil
from main import pull_soc_list, push_to_soc

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

    for x in sample_data[250:400]:

        students.append(insert_students(cursor, x))

    print(students)
    print("Students Loaded")

    counter = 0
    for x in sample_data[200:210]:

        x['Module_1'] = class_names[counter]
        x['Module_2'] = class_names[counter + 1]
        counter = counter + 2

        insert_lecturers(cursor, x)
        insert_module(cursor, x, random.sample(students, 90))

    print("Lecturers and relevant Modules Loaded")


def insert_module(cursor, sample_data, students):

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    locations = ["Seminar Room", "QMB", "Dalhousie", "Carnelly", "Harris"]
    time = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
    name = ["Lecture", "Seminar", "Lab", "Tutorial"]

    module_ID = ('AC' + (''.join(random.sample('0123456789', 5))))

    query = "INSERT INTO Modules(ModuleID, ModuleName, LecturerID) VALUES (?, ?, ?);"
    cursor.execute(query, (module_ID, sample_data['Module_1'], sample_data['LecturerID']))
    print(module_ID,sample_data['Module_1'], sample_data['LecturerID'])
    cursor.commit()

    for i in range(2):

        lecture_name = random.choice(name)
        lecture_location = random.choice(locations)
        day = random.choice(days)
        lecture_time = random.choice(time)

        for x in range(1, 12 + 1):

            query = "INSERT INTO Lectures (LectureID, ModuleID, LectureName, LectureLocation, LectureDuration, Week, Day, Time ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
            print(generatenewcode(), module_ID, lecture_name, lecture_location, x, day, lecture_time)

            cursor.execute(query, (generatenewcode(), module_ID, lecture_name, lecture_location, randint(1, 4), x, day, lecture_time))
            cursor.commit()

    print("Semester 1 is timetabled")

    filename = ('/Class_Lists/%s.txt' % module_ID)
    current_path = os.path.abspath(os.path.dirname(__file__))
    path = current_path + filename

    # query = "SELECT * FROM Lectures WHERE ModuleID=? ORDER BY Week ASC"
    # result = pd.read_sql(query, conn, params=(module_ID,))
    # lectures = result.to_dict('records')

    with open(path, 'w') as file:

        file.write(str(students[0]['MatricNum']))

        for student in students[1:45]:

            file.write('\n' + str(student['MatricNum']))

    module_ID = ('AC' + (''.join(random.sample('0123456789', 5))))

    filename = ('/Class_Lists/%s.txt' % module_ID)
    current_path = os.path.abspath(os.path.dirname(__file__))
    path = current_path + filename

    query = "INSERT INTO Modules(ModuleID, ModuleName, LecturerID) VALUES (?, ?, ?);"
    cursor.execute(query, (module_ID, sample_data['Module_2'], sample_data['LecturerID']))
    print(module_ID, sample_data['Module_2'], sample_data['LecturerID'])
    cursor.commit()

    for i in range(2):
        lecture_name = random.choice(name)
        lecture_location = random.choice(locations)
        day = random.choice(days)
        lecture_time = random.choice(time)

        for x in range(13, 24 + 1):

            query = "INSERT INTO Lectures (LectureID, ModuleID, LectureName, LectureLocation, LectureDuration, Week, Day, Time ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
            print(generatenewcode(), module_ID, lecture_name, lecture_location, x, day, lecture_time)

            cursor.execute(query, (generatenewcode(), module_ID, lecture_name, lecture_location, randint(1,4), x, day, lecture_time))
            cursor.commit()

    print("Semester 2 is timetabled")

    with open(path, 'w') as file:

        file.write(str(students[45]['MatricNum']))

        for student in students[46:91]:

            file.write('\n' + str(student['MatricNum']))


def insert_students(cursor, sample_data):

    query = "INSERT INTO Students (MatricNum, FirstName, LastName, Password) VALUES (?, ?, ? ,?);"
    cursor.execute(query, (sample_data['MatricNum'], sample_data['first_name'], sample_data['last_name'], hash_password('password123')))
    print(sample_data['MatricNum'], sample_data['first_name'], sample_data['last_name'], hash_password('password123'))

    json_string = str('{ "MatricNum" : ' + str(sample_data['MatricNum']) + ', "FirstName" : "' + str(sample_data['first_name']) + '", "LastName" : "' + str(sample_data['last_name']) + '" }')

    cursor.commit()
    with open("SOC_Students.txt", "a") as f:
        # print(os.stat("SOC_Students.txt").st_size)
        if os.stat("SOC_Students.txt").st_size == 0:

            f.write(json_string)

        else:

            f.write('\n' + json_string)

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


def create_test_file():

    school_list = []
    path = os.path.abspath(os.path.dirname(__file__)) + '/SOC_Students.txt'
    with open(path, 'r') as file:
        for line in file:
            line = line.replace("\'", "\"")
            school_list.append(json.loads(line))

    path = os.path.abspath(os.path.dirname(__file__)) + '/testfile.csv'
    with open(path, 'w') as f:  # Just use 'w' mode in 3.x

        w = csv.DictWriter(f, school_list[0].keys())
        w.writeheader()
        for item in school_list[:45]:
            w = csv.DictWriter(f, item.keys())

            w.writerow(item)


def gen_id():

    return randint(100000000, 999999999)


def gen_username(first_name, last_name):

    return first_name[:1] + "." + last_name + str(randint(100, 999))


def clear_table():

    cursor = connect()
    cursor.execute("TRUNCATE TABLE Students")
    cursor.commit()

    cursor.execute("TRUNCATE TABLE Lecturers")
    cursor.commit()

    cursor.execute("TRUNCATE TABLE Lectures")
    cursor.commit()

    cursor.execute("TRUNCATE TABLE Modules")
    cursor.commit()


def wipe_folder():

    folder = os.path.abspath(os.path.dirname(__file__)) + '/Class_Lists'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


if __name__ == "__main__":

    if path.exists(os.path.abspath(os.path.dirname(__file__)) + '/SOC_Students.txt'):
        os.remove(os.path.abspath(os.path.dirname(__file__)) + '/SOC_Students.txt')

    wipe_folder()
    clear_table()
    sample_data = load_data()
    updated_students = []
    insert_data(sample_data, get_class_names())
    #create_test_file()



