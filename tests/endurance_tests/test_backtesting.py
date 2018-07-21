from tests.test_utils.backtesting_util import create_backtesting_config, create_backtesting_bot, start_backtesting_bot


def test_simple_backtesting():
    config = create_backtesting_config()
    bot = create_backtesting_bot(config)
    start_backtesting_bot(bot)


def test_multiple_backtesting():
    for _ in range(10):
        config = create_backtesting_config()
        bot = create_backtesting_bot(config)
        start_backtesting_bot(bot)
