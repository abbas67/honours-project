import csv
import pandas as pd
import pyodbc

drivers = [item for item in pyodbc.drivers()]
driver = drivers[-1]
server = 'Zeno.computing.dundee.ac.uk'
database = 'abbaslawaldb'
uid = 'abbaslawal'
pwd = 'abc2019ABL123..'

params = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}'
conn = pyodbc.connect(params)
cursor = conn.cursor()

query = "select top 50 MatricNum, FirstName, LastName from Students"
result = pd.read_sql(query, conn)
result_dict = result.to_dict('records')

print(result_dict)

with open('MOCK_DATA.csv', 'w') as file:

    file.write('MatricNum,FirstName,LastName')

    for student in result_dict:

        string = ('\n' + str(student['MatricNum']) + "," + student['FirstName'] + "," + student['LastName'])
        file.write(string)