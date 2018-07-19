from flask import render_template

from interfaces.web.advanced_controllers import advanced


@advanced.route("/")
@advanced.route("/home")
def home():
    return render_template('advanced_index.html')
