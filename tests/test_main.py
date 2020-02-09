import os

from flask import Flask, render_template, request, redirect, url_for, flash, session, g, json
import requests
import unittest
import logging
from dbconn import connect

import requests
from unittest import mock

from main import app

app.testing = True


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

        os.remove(os.path.abspath(os.path.dirname(__file__)) + '/SOC_Students.txt')


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
    def test_lecturer_signup(self):

        with self.assertLogs(level='INFO') as cm:
            # Sending a post request to the application.
            response = self.app.post('/signup', data=dict(idnum='testaccount123', password='password123', fname="Jane",
                                                          lname="Doe", lecturercheck="Lecturer", follow_redirects=True))
            # Checking that the account has been successfully created.
            self.assertEqual(['INFO:logger:Lecturer account successfully created'], cm.output)

        # Testing that duplicate accounts cannot be created

        with self.assertLogs(level='INFO') as cm:
            # Sending a post request to the application
            response = self.app.post('/signup', data=dict(idnum='testaccount123', password='password123', fname="Jane",
                                                          lname="Doe", lecturercheck="Lecturer", follow_redirects=True))
            # checking that the error has been caught and that the account has not been created.
            self.assertEqual(['INFO:logger:The ID already exists, Account Creation failed'], cm.output)

    def test_lecturer_login(self):

        with self.assertLogs(level='INFO') as cm:
            # Creating a lecturer account using the helper sign up method.
            self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer')
            # sending a post request to the application, attempting to log in...
            self.app.post('/lecturersignin',
                          data=dict(lecturerid='testaccount123', Password='password123', follow_redirects=True))
            # 'checks to see if the account has been successfully signed in or not.
            self.assertIn('INFO:logger:Successfully Signed Into Lecturer Account', cm.output)

    def test_create_delete_module(self):

        self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer')
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
            response = self.app.post('/modulemanagement', data=dict(moduleid='AC12345', modulename='Another Test Module',follow_redirects=True))
            # checking tha the application does not make duplicate modules.
            self.assertIn('INFO:logger:Error, module ID already exists, please choose another.', cm.output)

    def test_create_lecture(self):

        #performing prerequisites for test such as logging in etc...
        self.account_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer')
        self.lecturer_login('testaccount123', 'password123')
        response = self.app.post('/select_module_lecture',data=dict(module='AC12345'))

        with self.assertLogs(level='INFO') as cm:

            response = self.app.post('/createlecture', data=dict(time='14:00', duration='4', name='Seminar',
                                                             selected_module_lecture='AC12345', weekday='Monday', first='1', last='12',location='Dalhousie',
                                                             follow_redirects=True))
            print(response.status_code)
            self.assertIn('INFO:logger:Error, module ID already exists, please choose another.', cm.output)




    # def test_student_lecture_login(self):
    #
    #     with self.assertLogs(level='INFO') as cm:
    #
    #         # Checking to see if a register already exists, so that it can be deleted, making sure the test is accurate.
    #         path = os.path.abspath(os.path.dirname(__file__)) + '/../Attendance_Docs/Z80JCL.txt'
    #         if os.path.isfile(path):
    #             os.remove(path)
    #         # Creating the required accounts for the test.
    #         self.account_sign_up('160012346', 'password123', 'Harry', 'Potter', 'Student')
    #         self.account_sign_up('160012345', 'password123', 'Draco', 'Malfoy', 'Student')
    #         # Sending the required request to the application
    #         response = self.app.post('/lecturesignin', data=dict(MatriculationNumber='160012346', LectureCode='Z80JCL',
    #                                                              Password='password123', follow_redirects=True))
    #
    #         # Checking to see the register has been created and that the student has been signed in.
    #         self.assertTrue(os.path.isfile(path))
    #         self.assertIn('INFO:logger:Lecture attendance file does not exist yet, creating new file...', cm.output)
    #         self.assertIn('INFO:logger:Successfully signed into lecture', cm.output)
    #         # Sending the required request to the application
    #         response = self.app.post('/lecturesignin', data=dict(MatriculationNumber='160012345', LectureCode='Z80JCL',
    #                                                              Password='password123', follow_redirects=True))
    #
    #         # checking that the student has been added to the register and signed in.
    #         self.assertIn('INFO:logger:Lecture attendance file exists, appending to file...', cm.output)
    #         self.assertIn('INFO:logger:Successfully signed into lecture', cm.output)
    #
    #         # Testing that students cannot be signed into the same lecture twice.
    #
    #         response = self.app.post('/lecturesignin', data=dict(MatriculationNumber='160012345', LectureCode='Z80JCL',
    #                                                              Password='password123', follow_redirects=True))
    #
    #         self.assertIn('INFO:logger:Error, student attendance has already been recorded', cm.output)

    ########################
    #### helper methods ####
    ########################

    def account_sign_up(self, idnum, password, fname, lname, type):
        response = self.app.post('/signup', data=dict(idnum=idnum, password=password, fname=fname,
                                                      lname=lname, lecturercheck=type, follow_redirects=True))

    def create_lecture(self,time, duration, name, module, weekday, first, last):

        response = self.app.post('/createlecture', data=dict(time=time, duration=duration, name=name,
                                                      module=module, weekday=weekday, first=first, last=last, follow_redirects=True))

    def lecturer_login(self, username, password):

        self.app.post('/lecturersignin',
                      data=dict(lecturerid=username, Password=password, follow_redirects=True))


if __name__ == '__main__':
    unittest.main()







