import logging
import json
from flask import render_template, jsonify

from interfaces.web import server_instance, get_notifications, flush_notifications
from interfaces.web.bot_data_model import get_bot
from tools.commands import Commands


logger = logging.getLogger("ServerInstance Controller")


@server_instance.route("/commands")
@server_instance.route('/commands/<cmd>', methods=['GET', 'POST'])
def commands(cmd=None):
    if cmd == "update":
        Commands.update(logger, catch=True)
        return jsonify("Success")

    elif cmd == "restart":
        Commands.restart_bot(get_bot(), args="--web")
        return jsonify("Success")

    elif cmd == "stop":
        Commands.stop_bot(get_bot())
        return jsonify("Success")

    return render_template('commands.html', cmd=cmd)


@server_instance.route("/update")
def update():
    notifications_result = json.dumps(get_notifications(), ensure_ascii=False)
    flush_notifications()
    return notifications_result
