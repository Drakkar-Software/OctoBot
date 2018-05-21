import ccxt
from pandas import DataFrame

from trading.exchanges.exchange_simulator.exchange_simulator import ExchangeSimulator
from config.cst import CONFIG_ENABLED_OPTION, CONFIG_BACKTESTING, TimeFrames, HOURS_TO_MSECONDS
from tests.test_utils.config import load_test_config


class TestExchangeSimulator:
    DEFAULT_SYMBOL = "BTC/USDT"
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
            self.DEFAULT_SYMBOL,
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

    def test_get_recent_trades(self):
        _, exchange_inst = self.init_default()

        exchange_inst.get_recent_trades(self.DEFAULT_SYMBOL)

    def test_get_all_currencies_price_ticker(self):
        _, exchange_inst = self.init_default()

        exchange_inst.get_all_currencies_price_ticker()

    def test_should_update_data(self):
        _, exchange_inst = self.init_default()

        # first call
        assert exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        assert exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        # call get prices
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        # call without get_recent_trades
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        exchange_inst.fetched_trades_counter[self.DEFAULT_SYMBOL] = 2

        # call with not enough get_recent_trades
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        enough_recent_trades = exchange_inst.to_fetch_trades_by_time_frame[TimeFrames.ONE_HOUR] * 2
        exchange_inst.fetched_trades_counter[self.DEFAULT_SYMBOL] = enough_recent_trades

        # call with enough get_recent_trades
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        enough_recent_trades = exchange_inst.to_fetch_trades_by_time_frame[TimeFrames.ONE_HOUR] * 3
        exchange_inst.fetched_trades_counter[self.DEFAULT_SYMBOL] = enough_recent_trades

        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        enough_recent_trades = exchange_inst.to_fetch_trades_by_time_frame[TimeFrames.ONE_HOUR] * 4
        exchange_inst.fetched_trades_counter[self.DEFAULT_SYMBOL] = enough_recent_trades

        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        enough_recent_trades = exchange_inst.to_fetch_trades_by_time_frame[TimeFrames.ONE_HOUR] * 5
        exchange_inst.fetched_trades_counter[self.DEFAULT_SYMBOL] = enough_recent_trades

        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        assert exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        enough_recent_trades = exchange_inst.to_fetch_trades_by_time_frame[TimeFrames.ONE_HOUR] * 7
        exchange_inst.fetched_trades_counter[self.DEFAULT_SYMBOL] = enough_recent_trades

        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        assert not exchange_inst.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

    def test_should_update_recent_trades(self):
        _, exchange_inst = self.init_default()

        assert exchange_inst.should_update_recent_trades(self.DEFAULT_SYMBOL)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, self.DEFAULT_TF)

        # should be true
        for _ in range(0, int(exchange_inst.to_fetch_trades_by_time_frame[TimeFrames.ONE_HOUR])):
            assert exchange_inst.should_update_recent_trades(self.DEFAULT_SYMBOL)

        # exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, self.DEFAULT_TF)
        assert exchange_inst.should_update_recent_trades(self.DEFAULT_SYMBOL)
        # assert not exchange_inst.should_update_recent_trades(self.DEFAULT_SYMBOL)
