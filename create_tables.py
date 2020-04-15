import sqlite3
import os


def create_all_tables():

    file_path = os.path.abspath(os.path.dirname(__file__)) + '/Database/database.db'
    with open(file_path, 'w') as file:
        pass

    conn = sqlite3.connect(file_path, check_same_thread=False, timeout=10)
    cursor = conn.cursor()

    cursor = conn.cursor()

    create_modules = """CREATE TABLE Modules (
        ModuleID CHAR( 7 ) NOT NULL,
        ModuleName VARCHAR( 256 ) NOT NULL,
        LecturerID VARCHAR( 256 ) NOT NULL);
    """

    cursor.execute(create_modules)

    create_lecturers = """CREATE TABLE Lecturers(
        LecturerID VARCHAR( 255 ) NOT NULL,
        FirstName VARCHAR( 255 ) NOT NULL,
        LastName VARCHAR( 255 ) NOT NULL,
        Password VARCHAR( 255 ) NOT NULL,
        PRIMARY KEY ( LecturerID ) );"""

    cursor.execute(create_lecturers)

    create_lectures = """ CREATE TABLE Lectures (
        LectureID VARCHAR( 256 ) NOT NULL,
        ModuleID CHAR( 7 ) NOT NULL,
        LectureName VARCHAR( 256 ) NOT NULL,
        LectureLocation VARCHAR( 256 ) NOT NULL,
        LectureDuration INT NOT NULL,
        Week INT NOT NULL,
        Day VARCHAR( 256 ) NOT NULL,
        Time DATETIME NOT NULL,
        PRIMARY KEY ( LectureID ));"""

    cursor.execute(create_lectures)

    create_students = """ CREATE TABLE Students (
        MatricNum CHAR( 9 ) NOT NULL,
        FirstName VARCHAR( 256 ) NOT NULL,
        LastName VARCHAR( 256 ) NOT NULL,
        Password VARCHAR( 256 ) NOT NULL,
        ModuleString VARCHAR( 3000 ) NOT NULL,
        Email VARCHAR( 256 ) NOT NULL);
    """

    cursor.execute(create_students)

