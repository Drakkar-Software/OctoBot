from flask import render_template

from interfaces.web import server_instance


@server_instance.route("/")
@server_instance.route("/home")
def home():
    return render_template('index.html')

