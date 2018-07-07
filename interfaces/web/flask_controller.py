import json
import logging

from flask import render_template, jsonify, request

from interfaces import get_bot
from tools.commands import Commands

from interfaces.web import server_instance, get_notifications, flush_notifications
from interfaces.web.bot_data_model import get_evaluator_config, update_evaluator_config
from interfaces.web.flask_util import get_rest_reply

logger = logging.getLogger("ServerInstance Controller")


@server_instance.route("/")
@server_instance.route("/home")
def home():
    return render_template('index.html')


@server_instance.route("/dash")
def dash():
    return render_template('dashboard.html')


@server_instance.route("/config")
@server_instance.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        update_type = request.args["update_type"]
        if update_type == "evaluator_config":
            updated_data = request.get_json()

            if updated_data:
                if update_evaluator_config(updated_data):
                    return get_rest_reply(jsonify(get_evaluator_config()))
                else:
                    return get_rest_reply('{"update": "ko"}', 500)
    else:
        return render_template('config.html', get_evaluator_config=get_evaluator_config)


@server_instance.route("/portfolio")
def portfolio():
    return render_template('portfolio.html')


@server_instance.route("/tentacles")
def tentacles():
    return render_template('tentacles.html')


@server_instance.route("/orders")
def orders():
    return render_template('orders.html')


@server_instance.route("/trades")
def trades():
    return render_template('trades.html')


@server_instance.route("/backtesting")
def backtesting():
    return render_template('backtesting.html')


@server_instance.route("/tentacle_manager")
def tentacle_manager():
    return render_template('tentacle_manager.html')


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
