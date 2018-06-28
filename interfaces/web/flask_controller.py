import json
import logging

from flask import render_template, jsonify

from interfaces import get_bot
from tools.commands import Commands

from interfaces.web import server_instance, get_notifications, flush_notifications

logger = logging.getLogger("ServerInstance Controller")

@server_instance.route("/")
@server_instance.route("/home")
def home():
    return render_template('index.html')


@server_instance.route("/dash")
def dash():
    return render_template('dashboard.html')


@server_instance.route("/config")
def config():
    return render_template('config.html')


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
