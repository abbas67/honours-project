from main import pull_soc_list, push_to_soc
import random
school_list = pull_soc_list()


def randomise_attendance():

    for student in school_list:

        for lecture in student:

            if student[lecture] == 'Present':

                student[lecture] = 'Absent'

    for student in school_list:

        for x in range(0, 150):

            selected = random.choice(list(student))

            if student[selected] == 'Absent':
                student[selected] = 'Present'

            else:

                continue

    push_to_soc(school_list)


if __name__ == "__main__":

    randomise_attendance()