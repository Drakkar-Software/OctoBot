from flask import render_template

from interfaces.web import server_instance


@server_instance.route("/")
def index():
    return render_template('index.html')
