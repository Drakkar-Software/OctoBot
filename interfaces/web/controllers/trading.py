from flask import render_template

from interfaces.trading_util import get_traders
from interfaces.web import server_instance
from trading.trader.portfolio import Portfolio


@server_instance.route("/portfolio")
def portfolio():
    total_portfolio = {}
    traders = get_traders()

    for trader in traders:
        for currency, amounts in trader.get_portfolio().get_portfolio().items():
            if currency in total_portfolio:
                total_portfolio[currency][Portfolio.TOTAL] += amounts[Portfolio.TOTAL]
                total_portfolio[currency][Portfolio.AVAILABLE] += amounts[Portfolio.AVAILABLE]
            else:
                total_portfolio[currency] = {
                    Portfolio.TOTAL: amounts[Portfolio.TOTAL],
                    Portfolio.AVAILABLE: amounts[Portfolio.AVAILABLE],
                }

    return render_template('portfolio.html', total_portfolio=total_portfolio)


@server_instance.route("/orders")
def orders():
    return render_template('orders.html')


@server_instance.route("/trades")
def trades():
    return render_template('trades.html')
