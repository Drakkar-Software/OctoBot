from flask import render_template

from interfaces.web import server_instance


@server_instance.route("/dash")
def dash():
    return render_template('dashboard.html')
