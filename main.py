import datetime, string, random
from flask import Flask, render_template


app = Flask(__name__)


@app.route("/")
@app.route("/home")
def index():
    date = datetime.datetime.now()

    #uses template from https://bootsnipp.com/snippets/vl4R7
    return render_template('home.html', date=date)


@app.route("/genCode")
def codedisplay():

    return render_template('genCode.html', code=generatenewcode())


def generatenewcode():

    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))


if __name__ == "__main__":
    app.run(host= '0.0.0.0', threaded=True)