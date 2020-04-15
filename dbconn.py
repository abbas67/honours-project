import sqlite3
import os
from sqlite3 import Error


def connect():

    file_path = os.path.abspath(os.path.dirname(__file__))
    conn = sqlite3.connect(file_path + '/Database/database.db', check_same_thread=False)

    return conn
