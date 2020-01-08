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

        pass

    def tearDown(self,):
        cursor = connect()

        cursor.execute("DELETE FROM Students WHERE MatricNum=?", ('160012345',))
        cursor.commit()

        cursor.execute("DELETE FROM Lecturers WHERE LecturerID=?", ('testaccount123',))
        cursor.commit()

        cursor.execute("DELETE FROM Lecturers WHERE LecturerID=?", ('testlecturerID123',))
        cursor.commit()

    # Testing the account creation functionality for students
    def test_studentsignup(self):

        with self.assertLogs(level='INFO') as cm:
            # sending a post request to the application.
            response = self.app.post('/signup', data=dict(idnum='160012345', password='password123', fname="John",
                                                          lname="Smith", lecturercheck="Student", follow_redirects=True))
            # checking tha the application has actually created the account by checking the logs.
            self.assertEqual(['INFO:logger:Student account successfully created'], cm.output)

        # Testing for issues with the matriculation number.
        with self.assertLogs(level='INFO') as cm:
            # sending a post request to the application with a matriculation number that is invalid.
            response = self.app.post('/signup', data=dict(idnum='1', password='password123', fname="John",
                                                          lname="Smith", lecturercheck="Student", follow_redirects=True))
            # checking that an error is caught and account creation has been failed.
            self.assertEqual(['INFO:logger:Invalid Matriculation Number'], cm.output)

        # Testing that duplicate accounts cannot be created.
        with self.assertLogs(level='INFO') as cm:
            # sending a post request to the application with the same credentials as an account that already exists.
            response = self.app.post('/signup', data=dict(idnum='160012345', password='password123', fname="John",
                                                          lname="Smith", lecturercheck="Student", follow_redirects=True))
            # checking that an error is caught and account creation has been failed.
            self.assertEqual(['INFO:logger:Error, ID already exists'], cm.output)

    # Testing the account creation functionality for lecturers
    def test_lecturersignup(self):

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
            self.lecturer_sign_up('testaccount123', 'password123', 'John', 'Doe', 'Lecturer')
            # sending a post request to the application, attempting to log in...
            self.app.post('/lecturersignin',
                          data=dict(lecturerid='testaccount123', Password='password123', follow_redirects=True))
            # 'checks to see if the account has been successfully signed in or not.
            print(cm.output)
            self.assertIn('INFO:logger:Successfully Signed Into Lecturer Account', cm.output)


    def test_student_lecture_login(self):
        
        response = self.app.post('/signup', data=dict(idnum=idnum, password=password, fname=fname,
                                                      lname=lname, lecturercheck=type, follow_redirects=True))

    ########################
    #### helper methods ####
    ########################

    def lecturer_sign_up(self, idnum, password, fname, lname, type):
        response = self.app.post('/signup', data=dict(idnum=idnum, password=password, fname=fname,
                                                      lname=lname, lecturercheck=type, follow_redirects=True))


if __name__ == '__main__':
    unittest.main()







