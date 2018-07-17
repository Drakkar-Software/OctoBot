from flask import render_template

from interfaces.web import server_instance


@server_instance.route("/backtesting")
def backtesting():
    return render_template('backtesting.html')


@server_instance.route("/data_collector")
def data_collector():
    return render_template('data_collector.html')
