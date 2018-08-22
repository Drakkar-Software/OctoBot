from flask import render_template

from interfaces.web import server_instance, get_logs, flush_errors_count


@server_instance.route("/logs")
def logs():
    flush_errors_count()
    return render_template("logs.html",
                           logs=get_logs())
