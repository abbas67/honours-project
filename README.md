Manual


Introduction 

It is highly advisable that the application is ran locally, to avoid database issues, however, if this is not possible, the application is available at http://134.36.36.224:5000/ on the school of computing VPN. Python 3 and pip being installed is also a requirement.
Setup and Running Using an IDE e.g. PyCharm 

Installing requirements 

Simply typing pip install -r requirements.txt into the terminal and running it in the root source code directory should install all requirements. 

Running the Application 

Simply right click and run Easy_Setup.py in the IDE of choice. Once this is complete, you should be provided with a sample username and password. 

Finally, run the web application by right clicking and running main.py.
Setup and Running Using Only the Terminal 

Following this series of commands should provide you with a sample username and password along with running the application. 

Firstly, navigate to the root source code folder and type the following commands: 

1.	pip install -r requirements.txt
2.	python3 Easy_Setup.py
3.	export FLASK_APP=main.py
4.	flask run 
Uploading A Sample Class List

Within module management, it is possible to upload a class list by file. A sample class list has been created to demonstrate this. This file can be found within the root source code folder and is called Mock_Data.CSV. 
Looking at Students Signing In 

1.	A student account will have to be created and this can be done through home page. 
2.	The newly created student must be added to the class list and this can be done within the ‘edit class list’ functionality. 
3.	The student can then be signed into any lecture. 



