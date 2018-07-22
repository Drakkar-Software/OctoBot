from tests.test_utils.backtesting_util import create_backtesting_config, create_backtesting_bot, start_backtesting_bot

MULTIPLE_BACKTESTINGS_ITERATIONS = 10


def test_simple_backtesting():
    config = create_backtesting_config(["ICX/BTC"])

    bot = create_backtesting_bot(config)
    start_backtesting_bot(bot)


def test_multiple_backtestings():
    config = create_backtesting_config(["ICX/BTC"])
    bot = create_backtesting_bot(config)
    previous_profitability, previous_market_profitability = start_backtesting_bot(bot)
    for _ in range(MULTIPLE_BACKTESTINGS_ITERATIONS):
        config = create_backtesting_config(["ICX/BTC"])
        bot = create_backtesting_bot(config)
        current_profitability, current_market_profitability = start_backtesting_bot(bot)
        assert previous_profitability == current_profitability
        assert previous_market_profitability == current_market_profitability


def test_multiple_multi_symbol_backtestings():
    symbols = ["BTC/USDT", "NEO/BTC", "ICX/BTC", "VEN/BTC", "XRB/BTC"]
    config = create_backtesting_config(symbols)
    bot = create_backtesting_bot(config)
    start_backtesting_bot(bot)
    for _ in range(MULTIPLE_BACKTESTINGS_ITERATIONS):
        config = create_backtesting_config(symbols)
        bot = create_backtesting_bot(config)
        start_backtesting_bot(bot)
