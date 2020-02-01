import csv
import json
import hashlib, binascii, os
import random,string
from random import randint

from dbconn import connect


def clean_data():

    with open('sample_names.csv', 'r') as csvfile, open('sample_names.json', 'w') as jsonfile:

        fieldnames = ("first_name", "last_name", "company_name", "address", "city", "county", "state", "zip", "phone1", "phone2", "email", "web")
        reader = csv.DictReader(csvfile, fieldnames)

        for row in reader:
            json.dump(row, jsonfile)
            jsonfile.write('\n')


def load_data():

    sample_name_list = []
    with open('sample_names.json', 'r') as jsonfile:

        for line in jsonfile:
            sample_name_list.append(json.loads(line))

    for x in sample_name_list:

        x['MatricNum'] = gen_id()
        x['LecturerID'] = gen_username()

    return sample_name_list


def insert_data(sample_data):

    cursor = connect()

    for x in sample_data[1:100]:

        insert_students(cursor, x)

    print("Students Loaded")

   # # for x in sample_data[200:215]:
   #
   #      insert_lecturers(cursor, x)
   #
   #  print("Lecturers and relevant Modules Loaded")


def insert_students(cursor, sample_data):

    # #query = "INSERT INTO Students (MatricNum, FirstName, LastName, Password) VALUES (?, ?, ? ,?);"
    # #cursor.execute(query, (sample_data['MatricNum'], sample_data['first_name'], sample_data['last_name'], hash_password('password123')))
    # print(sample_data['MatricNum'], sample_data['first_name'], sample_data['last_name'], hash_password('password123'))

    json_string = str('{ "MatricNum" : ' + str(sample_data['MatricNum']) + ', "FirstName" : "' + str(sample_data['first_name']) + '", "LastName" : "' + str(sample_data['last_name']) + '" }')
    print(json_string)

    with open("SOC_Students.txt", "a") as f:

        f.write('\n' + json_string)

    # #cursor.commit()


def insert_lecturers(cursor, sample_data):

    days = ["Monday", "Tuesday","Wednesday", "Thursday", "Friday"]
    locations = ["Seminar Room", "QMB", "Dalhousie", "Carnelly", "Harris"]
    time = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
    name = ["Lecture", "Seminar", "Lab", "Tutorial"]

    query = "INSERT INTO Lecturers (LecturerID, FirstName, LastName, Password) VALUES (?, ?, ? ,?);"
    cursor.execute(query, (sample_data['LecturerID'], sample_data['first_name'], sample_data['last_name'], hash_password('password123')))
    print(sample_data['LecturerID'], sample_data['first_name'], sample_data['last_name'], hash_password('password123'))
    cursor.commit()

    module_ID = ('AC' + (''.join(random.sample('0123456789', 5))))

    query = "INSERT INTO Modules(ModuleID, ModuleName, LecturerID) VALUES (?, ?, ?);"
    cursor.execute(query, (module_ID,("Introduction To " + sample_data['company_name']) , sample_data['LecturerID']))
    print(module_ID, ("Introduction To " + sample_data['company_name']) , sample_data['LecturerID'])
    cursor.commit()

    lecture_name = random.choice(name)
    lecture_location = random.choice(locations)
    day = random.choice(days)
    lecture_time = random.choice(time)
    for x in range(1, 12 + 1):

        query = "INSERT INTO Lectures (LectureID, ModuleID, LectureName, LectureLocation, LectureDuration, Week, Day, Time ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
        print(generatenewcode(), module_ID, lecture_name, lecture_location, x, day, lecture_time)

        cursor.execute(query, (generatenewcode(), module_ID, lecture_name, lecture_location,randint(1,4), x, day, lecture_time))
        cursor.commit()
    print("Semester 1 is timetabled")

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


def gen_username():

    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(10))



if __name__ == "__main__":

    sample_data = load_data()
    insert_data(sample_data)



