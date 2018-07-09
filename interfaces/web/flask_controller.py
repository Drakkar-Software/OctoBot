import json
import logging

from flask import render_template, jsonify, request

from interfaces import get_bot
from tools.commands import Commands

from interfaces.web import server_instance, get_notifications, flush_notifications
from interfaces.web.bot_data_model import get_evaluator_config, update_evaluator_config, get_tentacles_packages, \
    get_tentacles, get_evaluator_startup_config, reset_evaluator_config, get_tentacles_package_description, \
    register_and_install
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
            request_data = request.get_json()
            success = False

            if request_data == "reset":
                success = reset_evaluator_config()
            elif request_data:
                success = update_evaluator_config(request_data)

            if success:
                return get_rest_reply(jsonify(get_evaluator_config()))
            else:
                return get_rest_reply('{"update": "ko"}', 500)
    else:
        return render_template('config.html',
                               get_evaluator_config=get_evaluator_config,
                               get_evaluator_startup_config=get_evaluator_startup_config)


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
@server_instance.route('/tentacle_manager', methods=['GET', 'POST'])
def tentacle_manager():
    if request.method == 'POST':
        update_type = request.args["update_type"]
        if update_type == "add_package":
            request_data = request.get_json()
            success = False

            if len(request_data) > 0:
                path_or_url, action = next(iter(request_data.items()))
                path_or_url = path_or_url.strip()
                if action == "description":
                    package_description = get_tentacles_package_description(path_or_url)
                    if package_description:
                        return get_rest_reply(jsonify(package_description))
                    else:
                        return get_rest_reply('{"Impossible to find tentacles package information.": "ko"}', 500)
                elif action == "register_and_install":
                    installation_result = register_and_install(path_or_url)
                    if installation_result:
                        return get_rest_reply(jsonify(installation_result))
                    else:
                        return get_rest_reply('{"Impossible to install the given tentacles package, check the logs '
                                              'for more information.": "ko"}', 500)

            if not success:
                return get_rest_reply('{"operation": "ko"}', 500)

    else:
        return render_template('tentacle_manager.html',
                               get_tentacles_packages=get_tentacles_packages,
                               get_tentacles=get_tentacles)


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
