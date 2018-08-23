from backtesting.backtesting_util import create_backtesting_config, create_backtesting_bot, start_backtesting_bot
from tests.test_utils.config import load_test_config


def test_backtesting():
    config = create_backtesting_config(load_test_config(), ["ICX/BTC"])
    bot = create_backtesting_bot(config)
    previous_profitability, previous_market_profitability = start_backtesting_bot(bot)
    config = create_backtesting_config(load_test_config(), ["ICX/BTC"])
    bot = create_backtesting_bot(config)
    current_profitability, current_market_profitability = start_backtesting_bot(bot)

    # ensure no randomness in backtesting
    assert previous_profitability == current_profitability
    assert previous_market_profitability == current_market_profitability


def test_multi_symbol_backtesting():
    config = create_backtesting_config(load_test_config(), ["ICX/BTC", "VEN/BTC", "XRB/BTC"])
    bot = create_backtesting_bot(config)
    start_backtesting_bot(bot)
