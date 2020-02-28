import os
from main import pull_soc_list, push_to_soc, get_lectures
path = os.path.abspath(os.path.dirname(__file__)) + '/Class_Lists'
x = []
school_list = pull_soc_list()
for filename in os.listdir(path):
    path = os.path.abspath(os.path.dirname(__file__)) + '/Class_Lists/' + filename
    with open(path, 'r') as file:

        class_list = file.readlines()
        for line in class_list:
            line = line.strip()

        for student in school_list:

            for matric_num in class_list:

                if int(student['MatricNum']) == int(matric_num):
                    x.append(student['MatricNum'])

                    for lecture in get_lectures(filename[:-4]):

                        if lecture['LectureID'] not in student:

                            student[lecture['LectureID']] = 'Absent'


push_to_soc(school_list)
