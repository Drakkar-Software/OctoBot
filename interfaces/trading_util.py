from interfaces import get_bot
from trading.trader.portfolio import Portfolio


def get_traders():
    return [trader for trader in get_bot().get_exchange_traders().values()] + \
           [trader for trader in get_bot().get_exchange_trader_simulators().values()]


def get_portfolio_current_value():
    simulated_value = 0
    real_value = 0
    traders = get_traders()
    has_real_trader = False
    has_simulated_trader = False

    for trader in traders:
        if trader.enabled(trader.config):
            trade_manager = trader.get_trades_manager()

            current_value = trade_manager.get_portfolio_current_value()

            # current_value might be 0 if no trades have been made / canceled => use origin value
            if current_value == 0:
                current_value = trade_manager.get_portfolio_origin_value()

            if trader.get_simulate():
                simulated_value += current_value
                has_simulated_trader = True
            else:
                real_value += current_value
                has_real_trader = True

    return has_real_trader, has_simulated_trader, real_value, simulated_value


def has_real_and_or_simulated_traders():
    has_real_trader = False
    has_simulated_trader = False
    traders = get_traders()
    for trader in traders:
        if trader.enabled(trader.config):
            if trader.get_simulate():
                has_simulated_trader = True
            else:
                has_real_trader = True
    return has_real_trader, has_simulated_trader


def get_open_orders():
    simulated_open_orders = []
    real_open_orders = []
    traders = get_traders()

    for trader in traders:
        if trader.get_simulate():
            simulated_open_orders.append(trader.get_open_orders())
        else:
            real_open_orders.append(trader.get_open_orders())

    return real_open_orders, simulated_open_orders


def cancel_all_open_orders():
    for trader in get_traders():
        trader.cancel_all_open_orders()


def set_enable_trading(enable):
    for trader in get_traders():
        if trader.enabled(trader.config):
            trader.set_enabled(enable)


def get_trades_history():
    simulated_trades_history = []
    real_trades_history = []
    traders = get_traders()

    for trader in traders:
        if trader.get_simulate():
            simulated_trades_history.append(trader.get_trades_manager().get_trade_history())
        else:
            real_trades_history.append(trader.get_trades_manager().get_trade_history())

    return real_trades_history, simulated_trades_history


def set_risk(risk):
    traders = get_traders()

    for trader in traders:
        trader.set_risk(risk)


def get_risk():
    return next(iter(get_bot().get_exchange_traders().values())).get_risk()


def get_global_profitability():
    simulated_global_profitability = 0
    real_global_profitability = 0
    traders = get_traders()
    simulated_full_origin_value = 0
    real_full_origin_value = 0
    has_real_trader = False
    has_simulated_trader = False

    for trader in traders:
        if trader.enabled(trader.config):
            trade_manager = trader.get_trades_manager()

            # TODO : use other return values
            current_value, _, _ = trade_manager.get_profitability()

            if trader.get_simulate():
                simulated_full_origin_value += trade_manager.get_portfolio_origin_value()
                simulated_global_profitability += current_value
                has_simulated_trader = True
            else:
                real_full_origin_value += trade_manager.get_portfolio_origin_value()
                real_global_profitability += current_value
                has_real_trader = True

    simulated_percent_profitability = simulated_global_profitability * 100 / simulated_full_origin_value \
        if simulated_full_origin_value > 0 else 0
    real_percent_profitability = real_global_profitability * 100 / real_full_origin_value \
        if real_full_origin_value > 0 else 0

    return has_real_trader, has_simulated_trader, \
        real_global_profitability, simulated_global_profitability, \
        real_percent_profitability, simulated_percent_profitability


def get_portfolios():
    simulated_portfolios = []
    real_portfolios = []
    traders = get_traders()

    for trader in traders:
        if trader.get_simulate():
            simulated_portfolios.append(trader.get_portfolio().get_portfolio())
        else:
            real_portfolios.append(trader.get_portfolio().get_portfolio())

    return real_portfolios, simulated_portfolios


def get_currencies_with_status():
    symbol_with_evaluation = {}
    for symbol_evaluator in get_bot().get_symbol_evaluator_list().values():
        symbol_with_evaluation[symbol_evaluator.get_symbol()] = \
            {exchange.get_name():
                ",".join([
                    dec.get_state().name if dec.get_state() is not None else "N/A"
                    for dec in symbol_evaluator.get_deciders(exchange)])
             for exchange in get_bot().get_exchanges_list().values()
             if symbol_evaluator.has_exchange(exchange)}
    return symbol_with_evaluation


def get_global_portfolio_currencies_amounts():
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


def get_trades_by_times_and_prices():
    simulated_trades_times = []
    simulated_trades_prices = []

    real_trades_times = []
    real_trades_prices = []

    traders = get_traders()

    for trader in traders:
        for trade in trader.get_trades_manager().get_trade_history():
            if trader.get_simulate():
                simulated_trades_times.append(trade.get_filled_time())
                simulated_trades_prices.append(trade.get_price())
            else:
                real_trades_times.append(trade.get_filled_time())
                real_trades_prices.append(trade.get_price())

    return real_trades_prices, real_trades_times, simulated_trades_prices, simulated_trades_times
