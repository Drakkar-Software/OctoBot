from flask import render_template

from interfaces.web import server_instance


@server_instance.route("/portfolio")
def portfolio():
    return render_template('portfolio.html')


@server_instance.route("/orders")
def orders():
    return render_template('orders.html')


@server_instance.route("/trades")
def trades():
    return render_template('trades.html')
