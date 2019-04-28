#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from tools.logging.logging_util import get_logger
from copy import copy
from flask import render_template, jsonify

from config.disclaimer import DISCLAIMER
from interfaces.web import server_instance, get_notifications, flush_notifications, get_errors_count
from interfaces import get_bot
from tools.commands import Commands
from interfaces.web.models.configuration import get_metrics_enabled


logger = get_logger("ServerInstance Controller")


@server_instance.route("/commands")
@server_instance.route('/commands/<cmd>', methods=['GET', 'POST'])
def commands(cmd=None):
    if cmd == "restart":
        Commands.restart_bot()
        return jsonify("Success")

    elif cmd == "stop":
        Commands.stop_bot(get_bot())
        return jsonify("Success")

    return render_template('commands.html',
                           cmd=cmd,
                           metrics_enabled=get_metrics_enabled(),
                           disclaimer=DISCLAIMER)


@server_instance.route("/update")
def update():
    update_data = {
        "notifications": copy(get_notifications()),
        "errors_count": get_errors_count()
    }
    flush_notifications()
    return jsonify(update_data)
