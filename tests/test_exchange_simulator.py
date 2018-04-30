import ccxt
from pandas import DataFrame

from backtesting.exchange_simulator import ExchangeSimulator
from config.cst import CONFIG_ENABLED_OPTION, CONFIG_BACKTESTING, TimeFrames, HOURS_TO_MSECONDS
from tests.test_utils.config import load_test_config


class TestExchangeSimulator:
    DEFAULT_SYMBOL = "BTC"
    DEFAULT_TF = TimeFrames.ONE_HOUR

    @staticmethod
    def init_default():
        config = load_test_config()
        config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
        exchange_inst = ExchangeSimulator(config, ccxt.binance)
        return config, exchange_inst

    def test_get_symbol_prices_data_frame(self):
        _, exchange_inst = self.init_default()

        test_df = exchange_inst.get_symbol_prices(
            "BTC",
            TimeFrames.ONE_HOUR,
            data_frame=True)

        assert type(test_df) is DataFrame

    def test_multiple_get_symbol_prices(self):
        _, exchange_inst = self.init_default()

        first_data = exchange_inst.get_symbol_prices(
            self.DEFAULT_SYMBOL,
            self.DEFAULT_TF,
            data_frame=False)

        second_data = exchange_inst.get_symbol_prices(
            self.DEFAULT_SYMBOL,
            self.DEFAULT_TF,
            data_frame=False)

        # different arrays
        assert first_data != second_data

        # second is first with DEFAULT_TF difference
        assert first_data[1] == second_data[0]
        assert first_data[0][0] + HOURS_TO_MSECONDS == second_data[0][0]

        # end is end -1 with DEFAULT_TF difference
        assert first_data[-1] == second_data[-2]
        assert first_data[-1][0] + HOURS_TO_MSECONDS == second_data[-1][0]
