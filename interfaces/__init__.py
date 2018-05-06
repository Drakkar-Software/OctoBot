bot_instance = None
reference_market = None


def __init__(bot):
    global bot_instance
    bot_instance = bot


def get_bot():
    return bot_instance


def get_reference_market():
    global reference_market
    if reference_market is None:
        reference_market = next(iter(get_bot().get_exchange_traders().values())).get_trades_manager().get_reference()
    return reference_market
