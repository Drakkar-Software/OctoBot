from flask import render_template

from interfaces.web import server_instance


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


@server_instance.route("/update")
def update():
    return ""
