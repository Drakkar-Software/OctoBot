from tools.logging.logging_util import get_logger
from copy import copy
from flask import render_template, jsonify

from interfaces.web import server_instance, get_notifications, flush_notifications, get_errors_count
from interfaces import get_bot
from tools.commands import Commands


logger = get_logger("ServerInstance Controller")


@server_instance.route("/commands")
@server_instance.route('/commands/<cmd>', methods=['GET', 'POST'])
def commands(cmd=None):
    if cmd == "update":
        Commands.update(logger, catch=True)
        return jsonify("Success")

    elif cmd == "restart":
        Commands.restart_bot()
        return jsonify("Success")

    elif cmd == "stop":
        Commands.stop_bot(get_bot())
        return jsonify("Success")

    return render_template('commands.html', cmd=cmd)


@server_instance.route("/update")
def update():
    update_data = {
        "notifications": copy(get_notifications()),
        "errors_count": get_errors_count()
    }
    flush_notifications()
    return jsonify(update_data)
