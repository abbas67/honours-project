"""
NOTE THAT EVERY TEST HAS TO BE RAN INDIVIDUALLY TO AVOID ISSUES WITH DATABASE LOCKING.

Abbas Lawal
AC40001 Honours Project
BSc (Hons) Computing Science
University of Dundee 2019/20
Supervisor: Dr Craig Ramsay
All CODE IS ORIGINAL UNLESS STATED SO.
"""

import csv
import os
import io
import sqlite3
from sqlite3 import Error
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, json
import flask
import requests
import unittest
import logging
import pyodbc
import requests
from unittest import mock
from dbconn import connect
from main import app
from create_tables import create_all_tables

app.testing = True
conn = connect()
create_all_tables()


# Testing that each page returns the required response.
class BasicTests(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        pass

    def test_main_pages(self):

        # These are basic tests to make sure that there are no crashes as pages are loaded.

        response = self.app.get('/Home', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/signup', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/lecturer_home', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/lecturesignin', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/class_list_management', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/modulemanagement', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/gencode', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/create_lecture', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/student_stats', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/module_options', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/class_list_management', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)


class AdvancedTests(unittest.TestCase):

    idname = '160012345'
    password = 'password123'
    fname = 'John'
    lname = 'Smith'
    signuptype = 'Student'

    def setUp(self):

        self.app = app.test_client()
        self.app.testing = True


        pass

    def tearDown(self,):

        create_all_tables()


    #Testing the account creation functionality for students

    def test_student_signup(self):

        with self.assertLogs(level='INFO') as cm:
            # sending a post request to the application.
            response = self.app.post('/signup', data=dict(idnum='160012345', password='password123',
                                                          fname="John", lname="Smith", lecturercheck="Student", email="testemail123@google.com", follow_redirects=True))
            # checking tha the application has actually created the account by checking the logs.
            # checking to see that the correct response code is given by the request.

            self.assertEqual(response.status_code, 200)
            self.assertIn('INFO:logger:Student account successfully created', cm.output)
            # Checking to see that the student has been uploaded to the database.

            self.assertTrue(self.check_student_upload(160012345), "Test Failed")

        # Testing for issues with the matriculation number.
        with self.assertLogs(level='INFO') as cm:
            # sending a post request to the application with a matriculation number that is invalid.
            response = self.app.post('/signup', data=dict(idnum='1', password='password123', fname="John",
                                                          lname="Smith", lecturercheck="Student", email="testemail123@google.com", follow_redirects=True))
            # checking that an error is caught and account creation has been failed.
            self.assertEqual(['INFO:logger:Invalid Matriculation Number'], cm.output)
            # checking to see that the correct response code is given by the request.
            self.assertEqual(response.status_code, 200)
            # Checking to see that the student has NOT been uploaded to the database.
            self.assertFalse(self.check_student_upload(1), "Test Failed")

        # Testing that duplicate accounts cannot be created.
        with self.assertLogs(level='INFO') as cm:
            # sending a post request to the application with the same credentials as an account that already exists.
            response = self.app.post('/signup', data=dict(idnum='160012345', password='password123', fname="John",
                                                          lname="Smith", lecturercheck="Student", email="testemail123@google.com", follow_redirects=True))
            # checking to see that the correct response code is given by the request.
            self.assertEqual(response.status_code, 200)
            # checking that an error is caught and account creation has been failed.
            self.assertEqual(['INFO:logger:Error, ID already exists'], cm.output)

    #Testing the account creation functionality for lecturers

    def test_lecturer_signup(self):

        with self.assertLogs(level='INFO') as cm:
            # Sending a post request to the application.
            response = self.app.post('/signup', data=dict(idnum='testaccount123', password='password123', fname="Jane",
                                                          lname="Doe", lecturercheck="Lecturer",email="testemail123@google.com", follow_redirects=True))

            # checking to see that the correct response code is given by the request.
            self.assertEqual(response.status_code, 200)

            # Checking that the account has been successfully created.
            self.assertEqual(['INFO:logger:Lecturer account successfully created'], cm.output)

            # Checking to see that the lecturer has been uploaded to the database.
            self.assertTrue(self.check_lecturer_upload('testaccount123'), "Test Failed")

        # Testing that duplicate accounts cannot be created

        with self.assertLogs(level='INFO') as cm:

            # Sending a post request to the application
            response = self.app.post('/signup', data=dict(idnum='testaccount123', password='password123', fname="Jane",
                                                          lname="Doe", lecturercheck="Lecturer", email="testemail123@google.com", follow_redirects=True))
            # checking to see that the correct response code is given by the request.
            self.assertEqual(response.status_code, 200)

            # checking that the error has been caught and that the account has not been created.
            self.assertEqual(['INFO:logger:The ID already exists, Account Creation failed'], cm.output)

    def test_lecturer_login(self):

        with self.assertLogs(level='INFO') as cm:
            # Creating a lecturer account using the helper sign up method.
            self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer', 'testemail@gmail.com')
            # sending a post request to the application, attempting to log in...
            self.app.post('/lecturer_sign_in',
                          data=dict(lecturerid='testaccount123', Password='password123', follow_redirects=True))
            # 'checks to see if the account has been successfully signed in or not.
            self.assertIn('INFO:logger:Successfully Signed Into Lecturer Account', cm.output)

        with self.assertLogs(level='INFO') as cm:
            # Sending a post request to the application
            response = self.app.post('/lecturer_sign_in',
                                     data=dict(lecturerid='wrong_account', Password='password123',  follow_redirects=True))
            # checking that the error has been caught and that the account has not been signed into.
            self.assertEqual(['INFO:logger:Account does not exist'], cm.output)

    def test_create_delete_module(self):

        self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer', 'testemail@gmail.com')
        self.lecturer_login('testaccount123', 'password123')

        with self.assertLogs(level='INFO') as cm:
            # sending a post request to the application.
            response = self.app.post('/modulemanagement', data=dict(moduleid='AC12345', modulename='Test Module', follow_redirects=True))
            # checking tha the application has created the module.
            self.assertIn('INFO:logger:AC12345 : Test Module successfully created.', cm.output)

        with self.assertLogs(level='INFO') as cm:
            # sending a post request to the application.
            response = self.app.post('/modulemanagement', data=dict(moduleid='AC12346', modulename='Test Module', follow_redirects=True))
            # checking tha the application does not make duplicate modules.
            self.assertIn('INFO:logger:Error, module names cannot be duplicated...', cm.output)

        with self.assertLogs(level='INFO') as cm:
            # sending a post request to the application.
            response = self.app.post('/modulemanagement', data=dict(moduleid='AC12345', modulename='Another Test Module', follow_redirects=True))
            # checking tha the application does not make duplicate modules.
            self.assertIn('INFO:logger:Error, module ID already exists, please choose another.', cm.output)

    def test_create_lecture(self):

        # performing prerequisites for test such as logging in etc...

        self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer', email="test_email@gmail.com")
        self.lecturer_login('testaccount123', 'password123')
        response = self.app.post('/update_managed_modules', data=dict(user_id='testaccount123'))
        response = self.app.post('/select_module_lecture',data=dict(module='AC12345'))

        with self.assertLogs(level='INFO') as cm:

            response = self.app.post('/create_lecture', data=dict(time='14:00', duration='4', name='Seminar',
                                                             selected_module_lecture='AC12345', weekday='Monday', first='1', last='12', location='Dalhousie',
                                                             follow_redirects=True))
            self.assertIn('INFO:logger:Lecture set: Monday from week 1 to 12 at Dalhousie at'
                          ' 2019-12-02 14:00:00 successfully created.', cm.output)

    def test_class_list(self):

        with self.assertLogs(level='INFO') as cm:
            # prerequisites such as creating a module, lecture and required accounts.
            self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer', 'test_email@gmail.com')
            self.lecturer_login('testaccount123', 'password123')
            self.app.post('/update_managed_modules', data=dict(user_id='testaccount123'))
            self.app.post('/select_module_lecture', data=dict(module='AC10000'))
            self.create_module('AC10000', 'Test Module 1')
            self.create_lecture('14:00', 4, 'Seminar', 'AC10000', 'Monday', 1, 12, 'Dalhousie')
            self.account_sign_up('160012346', 'password123', 'Harry', 'Potter', 'Student', 'test_email@gmail.com')
            self.account_sign_up('160012345', 'password123', 'Draco', 'Malfoy', 'Student', 'test_email@gmail.com')

            with self.app as client:
                with client.session_transaction() as sess:
                    sess['moduleid'] = 'AC10000'
                    sess.modified = True

            # Attempting to add the students to the class list
            self.app.post('/class_list_management', data=dict(f_name='Harry', l_name='Potter', matric_num='160012346'))
            self.app.post('/class_list_management', data=dict(f_name='Draco', l_name='Malfoy', matric_num='160012345'))

            # Checkng that the log has been triggered and the code has not failed so far...
            self.assertIn('INFO:logger:Draco Malfoy Added To Class list', cm.output)
            self.assertIn('INFO:logger:Harry Potter Added To Class list', cm.output)

            # Now attempting to add the students to another lecture.

            self.app.post('/update_managed_modules', data=dict(user_id='testaccount123'))
            self.app.post('/select_module_lecture', data=dict(module='AC12345'))
            self.create_module('AC12345', 'Test Module 2')
            self.create_lecture('14:00', 4, 'Seminar', 'AC10000', 'Tuesday', 1, 12, 'Dalhousie')

            with self.app as client:
                with client.session_transaction() as sess:
                    sess['moduleid'] = 'AC12345'
                    sess.modified = True

            self.app.post('/class_list_management',
                          data=dict(f_name='Harry', l_name='Potter', matric_num='160012346'))
            self.app.post('/class_list_management',
                          data=dict(f_name='Draco', l_name='Malfoy', matric_num='160012345'))

            # Checkng that the log has been triggered and the code has not failed so far...
            self.assertIn('INFO:logger:Draco Malfoy Added To Class list', cm.output)
            self.assertIn('INFO:logger:Harry Potter Added To Class list', cm.output)

            students = [self.get_student(160012345), self.get_student(160012346)]

            lectures = self.get_lectures('AC12345') + self.get_lectures('AC10000')

            # checking that each student has all the required lectures for BOTH moduleS.
            for student in students:

                # Checking that the student is in BOTH module class list.
                self.assertTrue(self.check_if_in_class_list('AC10000', student['MatricNum']))

                self.assertTrue(self.check_if_in_class_list('AC12345', student['MatricNum']))

                # The total amount of characters should be 116 for each student so far...
                self.assertEqual(len(student['ModuleString']), 232)

                for lecture in lectures:
                    self.assertIn(lecture['LectureID'] + '-0', student['ModuleString'])

            # Now checking to see what happens when a student is removed from a class list...

            self.app.post('/update_managed_modules', data=dict(user_id='testaccount123'))
            self.app.post('/select_module_lecture', data=dict(module='AC10000'))

            with self.app as client:
                with client.session_transaction() as sess:
                    sess['moduleid'] = 'AC10000'
                    sess.modified = True

            self.app.post('/remove_from_class_list', data=dict(Student='160012345'))
            self.app.post('/remove_from_class_list', data=dict(Student='160012346'))
            # Checking to see that the log statement has been triggered.
            self.assertIn('INFO:logger:Draco Malfoy Removed From AC10000', cm.output)
            self.assertIn('INFO:logger:Harry Potter Removed From AC10000', cm.output)

            students = [self.get_student(160012345), self.get_student(160012346)]

            for student in students:

                # Checking that the student is in the correct module class lists.
                self.assertFalse(self.check_if_in_class_list('AC10000', student['MatricNum']))

                self.assertTrue(self.check_if_in_class_list('AC12345', student['MatricNum']))

                # Checking that the lectures have been removed for each student.
                for lecture in self.get_lectures('AC10000'):

                    self.assertNotIn(lecture['LectureID'] + '-0', student['ModuleString'])

                # Checking that the correct lectures are still there for the students.
                for lecture in self.get_lectures('AC12345'):

                    self.assertIn(lecture['LectureID'] + '-0', student['ModuleString'])

    def test_lecture_signin(self):

        # prerequisites such as creating a module, lecture and required accounts.

        with self.assertLogs(level='INFO') as cm:

            with self.app as client:
                with client.session_transaction() as sess:
                                sess['moduleid'] = 'AC12345'
                                sess.modified = True

            self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer',  email='test@gmail.com')
            self.lecturer_login('testaccount123', 'password123')
            self.app.post('/update_managed_modules', data=dict(user_id='testaccount123'))
            self.app.post('/select_module_lecture', data=dict(module='AC12345'))
            self.create_module('AC12345', 'Test Module 1')
            self.create_lecture('14:00', 4, 'Seminar', 'AC12345', 'Monday', 1, 12, 'Dalhousie')
            self.account_sign_up('160012345', 'password123', 'Draco', 'Malfoy', 'Student', email='test@gmail.com')
            self.app.post('/class_list_management', data=dict(f_name='Draco', l_name='Malfoy', matric_num='160012345'))

            # Attempting to sign into a lecture...

            # Sending the required request to the application

            lectures = self.get_lectures('AC12345')
            for lecture in lectures:

                response = self.app.post('/lecturesignin', data=dict(MatriculationNumber='160012345', LectureCode=lecture['LectureID'],
                                                                     Password='password123', follow_redirects=True))

                # All lectures that are scheduled are being signed into...

                self.assertIn('INFO:logger:Draco Malfoy Successfully Signed into ' + lecture['LectureID'], cm.output)
                self.assertIn(lecture['LectureID'] + '-1', self.get_student(160012345)['ModuleString'])

                # Testing that students cannot be signed into the same lecture twice.

                response = self.app.post('/lecturesignin', data=dict(MatriculationNumber='160012345', LectureCode=lecture['LectureID'],
                                                                     Password='password123', follow_redirects=True))

            self.assertEqual(cm.output.count('INFO:logger:Error, Student has already been signed in.'), 12)

            # Making sure students can't sign in with the wrong credentials

            response = self.app.post('/lecturesignin', data=dict(MatriculationNumber='160012349', LectureCode=lectures[0]['LectureID'],
                                                                 Password='password123', follow_redirects=True))

            self.assertIn('INFO:logger:Matriculation Number or password is incorrect', cm.output)

            response = self.app.post('/lecturesignin', data=dict(MatriculationNumber='160012345', LectureCode="wrong lecture code",
                                                                 Password='password123', follow_redirects=True))

            self.assertIn('INFO:logger:Incorrect lecture code, attempt made by: 160012345', cm.output)

    def test_file_upload(self):

        with self.app as client:

            with client.session_transaction() as sess:
                sess['moduleid'] = 'AC12345'
                sess.modified = True

        self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer', 'test_email@gmail.com')
        self.lecturer_login('testaccount123', 'password123')
        self.app.post('/update_managed_modules', data=dict(user_id='testaccount123'))
        self.app.post('/select_module_lecture', data=dict(module='AC12345'))
        self.create_module('AC12345', 'Test Module 1')
        self.create_lecture('14:00', 4, 'Seminar', 'AC10000', 'Monday', 1, 12, 'Dalhousie')

        filepath = os.path.abspath(os.path.dirname(__file__)) + '/MOCK_DATA.csv'
        students = []
        with open(filepath) as file:
            reader = csv.DictReader(file)
            for row in reader:
                students.append(dict(row))

        for student in students:

            self.account_sign_up(student['MatricNum'], 'password123', student['FirstName'],
                                 student['LastName'], 'Student', email='test@gmail.com')

        with self.assertLogs(level='INFO') as cm:

            response = self.app.post('/upload_file', content_type='multipart/form-data',
                                     data=dict(file=open(filepath, 'rb')))

            self.assertIn('INFO:logger:all students successfully added to class list.', cm.output)

        with self.assertLogs(level='INFO') as cm:

            response = self.app.post('/upload_file', content_type='multipart/form-data',
                                     data=dict())

            self.assertIn('INFO:logger:no file found', cm.output)

    def test_attendance(self):

        # testing the attendance flagging function.
        with self.app as client:
            with client.session_transaction() as sess:
                sess['moduleid'] = 'AC12345'
                sess.modified = True

        # prerequisites such as creating a module, lecture and required accounts etc.
        self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer', 'test_email@gmail.com')
        self.lecturer_login('testaccount123', 'password123')
        self.app.post('/update_managed_modules', data=dict(user_id='testaccount123'))
        self.app.post('/select_module_lecture', data=dict(module='AC12345'))
        self.create_module('AC12345', 'Test Module 1')
        self.create_lecture('14:00', 4, 'Seminar', 'AC10000', 'Monday', 13, 24, 'Dalhousie')

        filepath = os.path.abspath(os.path.dirname(__file__)) + '/MOCK_DATA.csv'
        students = []
        with open(filepath) as file:
            reader = csv.DictReader(file)
            for row in reader:
                students.append(dict(row))

        # testing attendance flagging and expected lectures..

        for student in students[:5]:
            # list of expected attendance.
            attendance = ["less than 50", "less than 50", "less than 50", "less than 80", "100"]
            # creating the required students and adding them to a class list.
            self.account_sign_up(student['MatricNum'], 'password123', student['FirstName'],
                                 student['LastName'], 'Student', email='test@gmail.com')
            self.app.post('/class_list_management', data=dict(f_name=student['FirstName'],l_name=student['LastName'],
                                                              matric_num=student['MatricNum']))

            for x in range(1, 5):

                string = self.get_student(student['MatricNum'])['ModuleString']
                # changing the number of lectures attended.
                string = string.replace('-0', '-1', x)
                # Updating the student in the DB.
                query = 'UPDATE Students SET ModuleString={} WHERE MatricNum={};'\
                    .format("'" + string + "'", "'" + student['MatricNum'] + "'")

                cursor = conn.cursor()
                cursor.execute(query,conn)

                # verifying the correct response has been logged.
                with self.assertLogs(level='INFO') as cm:
                    response = self.app.get('/lecturer_home')
                    response = self.app.get('/module_options', data=dict(module_id='AC12345'))
                    self.assertIn('INFO:logger:' + student['FirstName'] + " " + student['LastName'] + " Has " + str(
                        attendance[x]) + "% attendance for AC12345", cm.output)

    ########################
    #### helper methods ####
    ########################

    def account_sign_up(self, idnum, password, fname, lname, type, email):
        response = self.app.post('/signup', data=dict(idnum=idnum, password=password, fname=fname,
                                                      lname=lname, lecturercheck=type, email=email, follow_redirects=True))

    def create_module(self, module_id, module_name):

        response = self.app.post('/modulemanagement', data=dict(moduleid=module_id, modulename=module_name, follow_redirects=True))

    def create_lecture(self,time, duration, name, module, weekday, first, last,location):

        response = self.app.post('/create_lecture', data=dict(time=time, duration=duration, name=name,
                                                      selected_module_lecture=module, weekday=weekday, first=first, last=last, location=location, follow_redirects=True))

    def lecturer_login(self, username, password):

        self.app.post('/lecturer_sign_in',
                      data=dict(lecturerid=username, Password=password, follow_redirects=True))

    def get_lectures(self, module_id):

        query = "SELECT * FROM Lectures WHERE ModuleID=?"

        result = pd.read_sql(query, conn, params=(module_id,))
        data = result.to_dict('records')

        return data

    def check_student_upload(self, matric_num):

        query = "SELECT * FROM Students WHERE MatricNum=?"
        result = pd.read_sql(query, conn, params=(int(matric_num),))
        student = result.to_dict('records')

        return len(student)

    def get_student(self, matric_num):

        query = "SELECT * FROM Students WHERE MatricNum=?"
        result = pd.read_sql(query, conn, params=(int(matric_num),))
        student = result.to_dict('records')

        if len(student) == 1:

            return student[0]

    def check_lecturer_upload(self, lecturer_id):

        query = "SELECT * FROM Lecturers WHERE LecturerID=?"
        result = pd.read_sql(query, conn, params=(lecturer_id,))
        lecturer = result.to_dict('records')

        return len(lecturer) == 1

    def check_if_in_class_list(self, module_id, matric_num):

        query = 'SELECT * FROM {} WHERE MatricNum={}'.format(module_id, int(matric_num))
        result = pd.read_sql(query, conn)
        student = result.to_dict('records')

        return len(student) == 1

    def retrieve_class_list(self, module_id):
        cursor = connect()
        class_list = []

        query = 'SELECT {}.MatricNum, {}.Attendance, Students.FirstName,Students.LastName, Students.ModuleString FROM {} INNER JOIN Students ON {}.MatricNum=Students.MatricNum;'.format(
            module_id, module_id, module_id, module_id)

        result = pd.read_sql(query, conn)

        students = result.to_dict('records')

        return students


if __name__ == '__main__':
    unittest.main()

