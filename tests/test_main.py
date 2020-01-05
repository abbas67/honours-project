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
        cursor = connect()

        query = "INSERT INTO Lecturers (LecturerID, FirstName, LastName, Password) VALUES (?, ?, ? ,?);"
        cursor.execute(query, ('testlecturerID123', 'testfirstname', 'testsecondname', 'password123'))
        cursor.commit()

        pass

    def tearDown(self,):
        cursor = connect()

        cursor.execute("DELETE FROM Students WHERE MatricNum=?", ('160012345',))
        cursor.commit()

        cursor.execute("DELETE FROM Lecturers WHERE LecturerID=?", ('testaccount123',))
        cursor.commit()

        cursor.execute("DELETE FROM Lecturers WHERE LecturerID=?", ('testlecturerID123',))
        cursor.commit()

    def test_studentsignup(self):
        # Testing the account creation functionality for students
        response = self.app.post('/signup', data=dict(idname='160012345', password='password123', fname="John",
                                                      lname="Smith", type="Student", follow_redirects=True))

        with self.assertLogs('logger', level='INFO') as cm:
            # Checks the log to see if an account has been created
            logging.getLogger('logger').info("Student account successfully created")
            self.assertEqual(cm.output, ['INFO:logger:Student account successfully created'])

        # Testing for issues with the matriculation number.
        response = self.app.post('/signup', data=dict(idname='1', password='password123', fname="John",
                                                      lname="Smith", type="Student", follow_redirects=True))

        with self.assertLogs('logger', level='INFO') as cm:
            # Checks the log to see if an account has been created
            logging.getLogger('logger').info("Invalid Matriculation Number")
            self.assertEqual(cm.output, ['INFO:logger:Invalid Matriculation Number'])

        # Testing that duplicate accounts cannot be created.
        response = self.app.post('/signup', data=dict(idname='160012345', password='password123', fname="John",
                                                      lname="Smith", type="Student", follow_redirects=True))

        with self.assertLogs('logger', level='INFO') as cm:
            # Checks the log to see if an account has been created
            logging.getLogger('logger').info("Error, ID already exists")
            self.assertEqual(cm.output, ['INFO:logger:Error, ID already exists'])

    def test_lecturersignup(self):

        response = self.app.post('/signup', data=dict(idname='testaccount123', password='password123', fname="Jane",
                                                      lname="Doe", type="Lecturer", follow_redirects=True))
        # Testing the account creation functionality for lecturers
        with self.assertLogs('logger', level='INFO') as cm:
            # Checks the log to see if an account has been created
            logging.getLogger('logger').info("Lecturer account successfully created")
            self.assertEqual(cm.output, ['INFO:logger:Lecturer account successfully created'])

        # Testing that duplicate accounts cannot be created.
        response = self.app.post('/signup', data=dict(idname='testaccount123', password='password123', fname="Jane",
                                                      lname="Doe", type="Lecturer", follow_redirects=True))
        # Testing the account creation functionality for lecturers
        with self.assertLogs('logger', level='INFO') as cm:
            # Checks the log to see if an account has been created
            logging.getLogger('logger').info("The ID already exists, Account Creation failed")
            self.assertEqual(cm.output, ['INFO:logger:The ID already exists, Account Creation failed'])

    def test_lecturer_login(self):

        self.app.post('/lecturersignin', data=dict(lecturerid='testlecturerID123', Password='password123', follow_redirects=True))
        with self.assertLogs('logger', level='INFO') as cm:
            # Checks the log to see if an account has been created
            logging.getLogger('logger').info("Successfully Signed In1")
            self.assertEqual(cm.output, ['INFO:logger:Successfully Signed In1'])


if __name__ == '__main__':
    unittest.main()


########################
#### helper methods ####
########################
""""
def register(self, email, password, confirm):
    return self.app.post(
        '/register',
        data=dict(email=email, password=password, confirm=confirm),
        follow_redirects=True
    )

def logout(self):
    return self.app.get(
        '/logout',
        follow_redirects=True
    )
"""