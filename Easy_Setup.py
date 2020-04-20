from sample_data_load import prepare
import os
import sqlite3
import pandas as pd

print("Preparing...")
prepare()
print("Finished Preparation")
print("fetching example account info...")
file_path = os.path.abspath(os.path.dirname(__file__)) + '/Database/database.db'

conn = sqlite3.connect(file_path, check_same_thread=False, timeout=10)
cursor = conn.cursor()
query = ("SELECT LecturerID FROM Lecturers LIMIT 5;")
result = pd.read_sql(query, conn)
print("The sample lecturer username is " +
      result.to_dict('records')[0]['LecturerID'] + " and the password is: password123")
