
import csv
import json
import hashlib, binascii, os
import random,string
from random import randint

from dbconn import connect


def gen_id():

    return randint(100000000, 999999999)


def gen_username():

    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(10))


def clear_table():

    cursor = connect()
    cursor.execute("TRUNCATE TABLE Students")
    cursor.commit()


def load_data():

    sample_name_list = []
    with open('../sample_names.json', 'r') as jsonfile:

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


def generatenewcode():

    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))


def hash_password(password):
    """Hash a password for storing."""
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


def insert_students(cursor, sample_data):

    query = "INSERT INTO Students (MatricNum, FirstName, LastName, Password) VALUES (?, ?, ? ,?);"
    cursor.execute(query, (sample_data['MatricNum'], sample_data['first_name'], sample_data['last_name'], hash_password('password123')))
    # print(sample_data['MatricNum'], sample_data['first_name'], sample_data['last_name'], hash_password('password123'))

    json_string = str('{ "MatricNum" : ' + str(sample_data['MatricNum']) + ', "FirstName" : "' + str(sample_data['first_name']) + '", "LastName" : "' + str(sample_data['last_name']) + '" }')
    # print(json_string)

    cursor.commit()
    with open("SOC_Students.txt", "a") as f:
        # print(os.stat("SOC_Students.txt").st_size)
        if os.stat("SOC_Students.txt").st_size == 0:

            f.write(json_string)

        else:

            f.write('\n' + json_string)


def create_test_file():

    student_list = []

    school_list = []
    path = os.path.abspath(os.path.dirname(__file__)) + '/SOC_Students.txt'
    with open(path, 'r') as file:
        for line in file:
            line = line.replace("\'", "\"")
            school_list.append(json.loads(line))

    path = os.path.abspath(os.path.dirname(__file__)) + '/testfile.csv'
    with open(path, 'w') as f:

        w = csv.DictWriter(f, school_list[0].keys())
        w.writeheader()
        for item in school_list:
            w = csv.DictWriter(f, item.keys())

            w.writerow(item)

def prepare():

    clear_table()
    sample_data = load_data()
    insert_data(sample_data)
    create_test_file()
