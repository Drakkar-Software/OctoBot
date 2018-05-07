from interfaces import get_bot
from trading.trader.portfolio import Portfolio


def get_portfolio_current_value():
    simulated_value = 0
    real_value = 0

    traders = [trader for trader in get_bot().get_exchange_traders().values()] + \
              [trader for trader in get_bot().get_exchange_trader_simulators().values()]
    for trader in traders:
        trade_manager = trader.get_trades_manager()

        current_value = trade_manager.get_portfolio_current_value()

        # current_value might be 0 if no trades have been made / canceled => use origin value
        if current_value == 0:
            current_value = trade_manager.get_portfolio_origin_value()

        if trader.get_simulate():
            simulated_value += current_value
        else:
            real_value += current_value

    return real_value, simulated_value


def get_open_orders():
    simulated_open_orders = []
    real_open_orders = []

    traders = [trader for trader in get_bot().get_exchange_traders().values()] + \
              [trader for trader in get_bot().get_exchange_trader_simulators().values()]
    for trader in traders:
        if trader.get_simulate():
            simulated_open_orders.append(trader.get_open_orders())
        else:
            real_open_orders.append(trader.get_open_orders())

    return real_open_orders, simulated_open_orders


def set_risk(risk):
    traders = [trader for trader in get_bot().get_exchange_traders().values()] + \
              [trader for trader in get_bot().get_exchange_trader_simulators().values()]
    for trader in traders:
        trader.set_risk(risk)


def get_global_profitability():
    simulated_global_profitability = 0
    real_global_profitability = 0

    traders = [trader for trader in get_bot().get_exchange_traders().values()] + \
              [trader for trader in get_bot().get_exchange_trader_simulators().values()]
    for trader in traders:
        trade_manager = trader.get_trades_manager()

        # TODO : use other return values
        current_value, _, _ = trade_manager.get_profitability()

        if trader.get_simulate():
            simulated_global_profitability += current_value
        else:
            real_global_profitability += current_value

    return real_global_profitability, simulated_global_profitability


def get_portfolios():
    simulated_portfolios = []
    real_portfolios = []

    traders = [trader for trader in get_bot().get_exchange_traders().values()] + \
              [trader for trader in get_bot().get_exchange_trader_simulators().values()]
    for trader in traders:
        if trader.get_simulate():
            simulated_portfolios.append(trader.get_portfolio().get_portfolio())
        else:
            real_portfolios.append(trader.get_portfolio().get_portfolio())

    return real_portfolios, simulated_portfolios


def get_global_portfolio_currencies_amouts():
    real_portfolios, simulated_portfolios = get_portfolios()
    real_global_portfolio = {}
    simulated_global_portfolio = {}

    for portfolio in simulated_portfolios:
        for currency, amounts in portfolio.items():
            if currency not in simulated_global_portfolio:
                simulated_global_portfolio[currency] = {
                    Portfolio.TOTAL: 0,
                    Portfolio.AVAILABLE: 0
                }

            simulated_global_portfolio[currency][Portfolio.TOTAL] += amounts[Portfolio.TOTAL]
            simulated_global_portfolio[currency][Portfolio.AVAILABLE] = amounts[Portfolio.AVAILABLE]

    for portfolio in real_portfolios:
        for currency, amounts in portfolio.items():
            if currency not in real_global_portfolio:
                real_global_portfolio[currency] = {
                    Portfolio.TOTAL: 0,
                    Portfolio.AVAILABLE: 0
                }

            real_global_portfolio[currency][Portfolio.TOTAL] += amounts[Portfolio.TOTAL]
            real_global_portfolio[currency][Portfolio.AVAILABLE] = amounts[Portfolio.AVAILABLE]

    return real_global_portfolio, simulated_global_portfolio


def get_trades_by_times_and_prices(time_factor=1):
    simulated_trades_times = []
    simulated_trades_prices = []

    real_trades_times = []
    real_trades_prices = []

    traders = [trader for trader in get_bot().get_exchange_traders().values()] + \
              [trader for trader in get_bot().get_exchange_trader_simulators().values()]
    for trader in traders:
        for trade in trader.get_trades_manager().get_trade_history():
            if trader.get_simulate():
                simulated_trades_times.append(trade.get_filled_time()*time_factor)
                simulated_trades_prices.append(trade.get_price())
            else:
                real_trades_times.append(trade.get_filled_time()*time_factor)
                real_trades_prices.append(trade.get_price())

    return real_trades_prices, real_trades_times, simulated_trades_prices, simulated_trades_times
