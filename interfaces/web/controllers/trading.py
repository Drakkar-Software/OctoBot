import datetime

from flask import render_template

from interfaces.trading_util import get_open_orders, get_trades_history, get_global_portfolio_currencies_amounts, \
    get_currencies_with_status
from interfaces.web import server_instance
from trading.trader.portfolio import Portfolio


@server_instance.route("/portfolio")
def portfolio():
    real_portfolio, simulated_portfolio = get_global_portfolio_currencies_amounts()

    filtered_real_portfolio = {currency: amounts
                               for currency, amounts in real_portfolio.items()
                               if amounts[Portfolio.TOTAL] > 0}
    filtered_simulated_portfolio = {currency: amounts
                                    for currency, amounts in simulated_portfolio.items()
                                    if amounts[Portfolio.TOTAL] > 0}

    return render_template('portfolio.html',
                           simulated_portfolio=filtered_simulated_portfolio,
                           real_portfolio=filtered_real_portfolio)


@server_instance.route("/market_status")
def market_status():
    return render_template('market_status.html',
                           pairs_with_status=get_currencies_with_status())


@server_instance.route("/orders")
def orders():
    real_open_orders, simulated_open_orders = get_open_orders()
    return render_template('orders.html',
                           real_open_orders=real_open_orders,
                           simulated_open_orders=simulated_open_orders)


@server_instance.route("/trades")
def trades():
    real_trades_history, simulated_trades_history = get_trades_history()
    return render_template('trades.html',
                           real_trades_history=real_trades_history,
                           simulated_trades_history=simulated_trades_history)


@server_instance.context_processor
def utility_processor():
    def convert_timestamp(str_time):
        return datetime.datetime.fromtimestamp(str_time).strftime('%Y-%m-%d %H:%M:%S')

    def convert_type(str_type):
        return str(str_type).replace("TraderOrderType.", "")

    return dict(convert_timestamp=convert_timestamp, convert_type=convert_type)
