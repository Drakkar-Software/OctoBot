from interfaces import get_bot


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

