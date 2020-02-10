import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, json
import requests
import unittest
import logging
from dbconn import connect
import pyodbc
import requests
from unittest import mock

from main import app, updatemanagedmodules, get_class_attendance

app.testing = True

drivers = [item for item in pyodbc.drivers()]
driver = drivers[-1]
server = 'Zeno.computing.dundee.ac.uk'
database = 'abbaslawaldb'
uid = 'abbaslawal'
pwd = 'abc2019ABL123..'

params = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}'
conn = pyodbc.connect(params)
cursor = conn.cursor()

# Testing that each page returns the required response.
class BasicTests(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        pass

    def test_main_pages(self):

        ########################
        #### SPRINT 1 ####
        ########################

        response = self.app.get('/Home', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/signup', follow_redirects=True)
        # checks to see the page loads with no server errors etc.
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/lecturesignin', follow_redirects=True)
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

        if os.path.exists(os.path.abspath(os.path.dirname(__file__)) + '/SOC_Students.txt'):

            os.remove(os.path.abspath(os.path.dirname(__file__)) + '/SOC_Students.txt')

        file = open(os.path.abspath(os.path.dirname(__file__)) + '/SOC_Students.txt', 'w')
        file.close()

        pass

    def tearDown(self,):
        cursor = connect()

        cursor.execute("DELETE FROM Students WHERE MatricNum=?", ('160012345',))
        cursor.commit()

        cursor.execute("DELETE FROM Students WHERE MatricNum=?", ('160012346',))
        cursor.commit()

        cursor.execute("DELETE FROM Lecturers WHERE LecturerID=?", ('testaccount123',))
        cursor.commit()

        cursor.execute("DELETE FROM Lecturers WHERE LecturerID=?", ('testlecturerID123',))
        cursor.commit()

        cursor.execute("DELETE FROM Modules WHERE ModuleID=?", ('AC12345',))
        cursor.commit()

        cursor.execute("DELETE FROM Lectures WHERE ModuleID=?", ('AC12345',))
        cursor.commit()

        cursor.execute("DELETE FROM Modules WHERE ModuleID=?", ('AC12346',))
        cursor.commit()

        cursor.execute("DELETE FROM Lectures WHERE ModuleID=?", ('AC12346',))
        cursor.commit()




    # # Testing the account creation functionality for students
    # def test_student_signup(self):
    #
    #     with self.assertLogs(level='INFO') as cm:
    #         # sending a post request to the application.
    #         response = self.app.post('/signup', data=dict(idnum='160012345', password='password123', fname="John",
    #                                                       lname="Smith", lecturercheck="Student", follow_redirects=True))
    #         # checking tha the application has actually created the account by checking the logs.
    #         self.assertIn('INFO:logger:Student account successfully created', cm.output)
    #
    #     # Testing for issues with the matriculation number.
    #     with self.assertLogs(level='INFO') as cm:
    #         # sending a post request to the application with a matriculation number that is invalid.
    #         response = self.app.post('/signup', data=dict(idnum='1', password='password123', fname="John",
    #                                                       lname="Smith", lecturercheck="Student", follow_redirects=True))
    #         # checking that an error is caught and account creation has been failed.
    #         self.assertEqual(['INFO:logger:Invalid Matriculation Number'], cm.output)
    #
    #     # Testing that duplicate accounts cannot be created.
    #     with self.assertLogs(level='INFO') as cm:
    #         # sending a post request to the application with the same credentials as an account that already exists.
    #         response = self.app.post('/signup', data=dict(idnum='160012345', password='password123', fname="John",
    #                                                       lname="Smith", lecturercheck="Student", follow_redirects=True))
    #         # checking that an error is caught and account creation has been failed.
    #         self.assertEqual(['INFO:logger:Error, ID already exists'], cm.output)

    # Testing the account creation functionality for lecturers
    # def test_lecturer_signup(self):
    #
    #     with self.assertLogs(level='INFO') as cm:
    #         # Sending a post request to the application.
    #         response = self.app.post('/signup', data=dict(idnum='testaccount123', password='password123', fname="Jane",
    #                                                       lname="Doe", lecturercheck="Lecturer", follow_redirects=True))
    #         # Checking that the account has been successfully created.
    #         self.assertEqual(['INFO:logger:Lecturer account successfully created'], cm.output)
    #
    #     # Testing that duplicate accounts cannot be created
    #
    #     with self.assertLogs(level='INFO') as cm:
    #         # Sending a post request to the application
    #         response = self.app.post('/signup', data=dict(idnum='testaccount123', password='password123', fname="Jane",
    #                                                       lname="Doe", lecturercheck="Lecturer", follow_redirects=True))
    #         # checking that the error has been caught and that the account has not been created.
    #         self.assertEqual(['INFO:logger:The ID already exists, Account Creation failed'], cm.output)
    #
    # def test_lecturer_login(self):
    #
    #     with self.assertLogs(level='INFO') as cm:
    #         # Creating a lecturer account using the helper sign up method.
    #         self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer')
    #         # sending a post request to the application, attempting to log in...
    #         self.app.post('/lecturersignin',
    #                       data=dict(lecturerid='testaccount123', Password='password123', follow_redirects=True))
    #         # 'checks to see if the account has been successfully signed in or not.
    #         self.assertIn('INFO:logger:Successfully Signed Into Lecturer Account', cm.output)
    #
    # def test_create_delete_module(self):
    #
    #     self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer')
    #     self.lecturer_login('testaccount123', 'password123')
    #
    #     with self.assertLogs(level='INFO') as cm:
    #         # sending a post request to the application.
    #         response = self.app.post('/modulemanagement', data=dict(moduleid='AC12345', modulename='Test Module', follow_redirects=True))
    #         # checking tha the application has created the module.
    #         self.assertIn('INFO:logger:AC12345 : Test Module successfully created.', cm.output)
    #
    #     with self.assertLogs(level='INFO') as cm:
    #         # sending a post request to the application.
    #         response = self.app.post('/modulemanagement', data=dict(moduleid='AC12346', modulename='Test Module', follow_redirects=True))
    #         # checking tha the application does not make duplicate modules.
    #         self.assertIn('INFO:logger:Error, module names cannot be duplicated...', cm.output)
    #
    #     with self.assertLogs(level='INFO') as cm:
    #         # sending a post request to the application.
    #         response = self.app.post('/modulemanagement', data=dict(moduleid='AC12345', modulename='Another Test Module',follow_redirects=True))
    #         # checking tha the application does not make duplicate modules.
    #         self.assertIn('INFO:logger:Error, module ID already exists, please choose another.', cm.output)
    #
    # def test_create_lecture(self):
    #
    #     #performing prerequisites for test such as logging in etc...
    #
    #     self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer')
    #     self.lecturer_login('testaccount123', 'password123')
    #     response = self.app.post('/update_managed_modules', data=dict(user_id='testaccount123'))
    #     response = self.app.post('/select_module_lecture',data=dict(module='AC12345'))
    #
    #     with self.assertLogs(level='INFO') as cm:
    #
    #         response = self.app.post('/createlecture', data=dict(time='14:00', duration='4', name='Seminar',
    #                                                          selected_module_lecture='AC12345', weekday='Monday', first='1', last='12',location='Dalhousie',
    #                                                          follow_redirects=True))
    #         print(response.status_code)
    #         self.assertIn('INFO:logger:Lecture set: Monday from week 1 to 12 at Dalhousie at 14:00 successfully created.', cm.output)
    #
    # def test_class_list(self):
    #
    #     with self.assertLogs(level='INFO') as cm:
    #         # prerequisites such as creating a module, lecture and required accounts.
    #         self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer')
    #         self.lecturer_login('testaccount123', 'password123')
    #         self.app.post('/update_managed_modules', data=dict(user_id='testaccount123'))
    #         self.app.post('/select_module_lecture', data=dict(module='AC12345'))
    #         self.create_module('AC12345', 'Test Module 1')
    #         self.create_lecture('14:00', 4, 'Seminar', 'AC12345', 'Monday', 1, 12, 'Dalhousie')
    #         self.account_sign_up('160012346', 'password123', 'Harry', 'Potter', 'Student')
    #         self.account_sign_up('160012345', 'password123', 'Draco', 'Malfoy', 'Student')
    #
    #         with self.app as client:
    #             with client.session_transaction() as sess:
    #                 sess['moduleid'] = 'AC12345'
    #                 sess.modified = True
    #
    #         path = os.path.abspath(os.path.dirname(__file__)) + '/../Class_Lists/AC12345.txt'
    #
    #         if os.path.isfile(path):
    #             os.remove(path)
    #
    #         self.app.post('/class_list_management', data=dict(f_name='Harry', l_name='Potter', matric_num='160012346'))
    #
    #         self.app.post('/class_list_management', data=dict(f_name='Draco', l_name='Malfoy', matric_num='160012345'))
    #
    #         self.assertIn('INFO:logger:Draco Malfoy SOC data updated along with class list', cm.output)
    #         self.assertIn('INFO:logger:Harry Potter SOC data updated along with class list', cm.output)
    #
    #         with open(os.path.abspath(os.path.dirname(__file__)) + '/SOC_Students.txt', 'r') as f:
    #
    #             for line in f:
    #
    #                 for lecture_code in self.get_lectures('AC12345'):
    #
    #                     self.assertTrue(lecture_code in line, str(lecture_code) + " Error, Not found")

    def test_lecture_signin(self):

        # prerequisites such as creating a module, lecture and required accounts.

        path = os.path.abspath(os.path.dirname(__file__)) + '/../Class_Lists/AC12345.txt'

        if os.path.isfile(path):
            os.remove(path)

        with self.assertLogs(level='INFO') as cm:

            with self.app as client:
                with client.session_transaction() as sess:
                                sess['moduleid'] = 'AC12345'
                                sess.modified = True

            self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer')
            self.lecturer_login('testaccount123', 'password123')
            self.app.post('/update_managed_modules', data=dict(user_id='testaccount123'))
            self.app.post('/select_module_lecture', data=dict(module='AC12345'))
            self.create_module('AC12345', 'Test Module 1')
            self.create_lecture('14:00', 4, 'Seminar', 'AC12345', 'Monday', 1, 12, 'Dalhousie')
            self.account_sign_up('160012345', 'password123', 'Draco', 'Malfoy', 'Student')
            self.app.post('/class_list_management', data=dict(f_name='Draco', l_name='Malfoy', matric_num='160012345'))

            # Attempting to sign into a lecture...

            # Sending the required request to the application

            for x in range(0, 5):

                test_lecture = self.get_lectures('AC12345')[x]
                response = self.app.post('/lecturesignin', data=dict(MatriculationNumber='160012345', LectureCode=test_lecture,
                                                                     Password='password123', follow_redirects=True))

                with open(os.path.abspath(os.path.dirname(__file__)) + '/SOC_Students.txt', 'r') as f:

                    lines = f.readlines()
                    self.assertTrue("'" + test_lecture + "'" + ": 'Present'" in lines[0], "Error, not found")

            self.assertTrue(cm.output.count('INFO:logger:Draco Malfoy has been successfully signed into lecture') == 5, "Error")

            # Testing that students cannot be signed into the same lecture twice.

            response = self.app.post('/lecturesignin', data=dict(MatriculationNumber='160012345', LectureCode=test_lecture,
                                                                 Password='password123', follow_redirects=True))

            self.assertIn('INFO:logger:Draco Malfoy has already been signed in.', cm.output)

            #Making sure students can't sign in with the wrong credentials

            response = self.app.post('/lecturesignin', data=dict(MatriculationNumber='160012349', LectureCode=test_lecture,
                                                                 Password='password123', follow_redirects=True))

            self.assertIn('INFO:logger:Matriculation Number or password is incorrect', cm.output)

            response = self.app.post('/lecturesignin', data=dict(MatriculationNumber='160012345', LectureCode="wrong lecture code",
                                                                 Password='password123', follow_redirects=True))

            self.assertIn('INFO:logger:Incorrect lecture code, attempt made by: 160012345', cm.output)

    def test_attendance_percentage(self):

        with self.app as client:
            with client.session_transaction() as sess:
                sess['moduleid'] = 'AC12345'
                sess.modified = True

        with self.assertLogs(level='INFO') as cm:

            response = self.app.get('/student_stats', query_string=dict(Student='160012345'), follow_redirects=True)
            print(response.status_code)
            self.assertIn('INFO:logger:Incorrect lecture code, attempt made by: 160012345', cm.output)


    ########################
    #### helper methods ####
    ########################

    def account_sign_up(self, idnum, password, fname, lname, type):
        response = self.app.post('/signup', data=dict(idnum=idnum, password=password, fname=fname,
                                                      lname=lname, lecturercheck=type, follow_redirects=True))

    def create_module(self, module_id, module_name):

        response = self.app.post('/modulemanagement', data=dict(moduleid=module_id, modulename=module_name, follow_redirects=True))

    def create_lecture(self,time, duration, name, module, weekday, first, last,location):

        response = self.app.post('/createlecture', data=dict(time=time, duration=duration, name=name,
                                                      selected_module_lecture=module, weekday=weekday, first=first, last=last, location=location, follow_redirects=True))

    def lecturer_login(self, username, password):

        self.app.post('/lecturersignin',
                      data=dict(lecturerid=username, Password=password, follow_redirects=True))

    def get_lectures(self, module_id):

        query = "SELECT * FROM Lectures WHERE ModuleID=?"

        result = pd.read_sql(query, conn, params=(module_id,))
        data = result.to_dict('records')
        lecture_list = []

        for x in data:

            lecture_list.append(x['LectureID'])

        return lecture_list


if __name__ == '__main__':
    unittest.main()

