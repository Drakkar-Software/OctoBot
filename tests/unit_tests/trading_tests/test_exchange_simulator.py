import ccxt
from pandas import DataFrame

from config.cst import CONFIG_ENABLED_OPTION, CONFIG_BACKTESTING, TimeFrames, HOURS_TO_MSECONDS
from tests.test_utils.config import load_test_config
from trading.exchanges.exchange_manager import ExchangeManager
from trading.trader.trader_simulator import TraderSimulator


class TestExchangeSimulator:
    DEFAULT_SYMBOL = "BTC/USDT"
    DEFAULT_TF = TimeFrames.ONE_HOUR

    @staticmethod
    def init_default():
        config = load_test_config()
        config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        exchange_inst = exchange_manager.get_exchange()
        exchange_simulator = exchange_inst.get_exchange()
        trader_inst = TraderSimulator(config, exchange_inst, 1)
        return config, exchange_inst, exchange_simulator, trader_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    def test_get_symbol_prices_data_frame(self):
        _, exchange_inst, _, trader_inst = self.init_default()

        test_df = exchange_inst.get_symbol_prices(
            self.DEFAULT_SYMBOL,
            TimeFrames.ONE_HOUR,
            data_frame=True)

        assert type(test_df) is DataFrame

        self.stop(trader_inst)

    def test_get_symbol_prices_list(self):
        _, exchange_inst, _, trader_inst = self.init_default()

        test_list = exchange_inst.get_symbol_prices(
            self.DEFAULT_SYMBOL,
            TimeFrames.ONE_HOUR,
            data_frame=False)

        assert isinstance(test_list, list)

        self.stop(trader_inst)

    def test_multiple_get_symbol_prices(self):
        _, exchange_inst, _, trader_inst = self.init_default()

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

        self.stop(trader_inst)

    def test_get_recent_trades(self):
        _, exchange_inst, _, trader_inst = self.init_default()

        exchange_inst.get_recent_trades(self.DEFAULT_SYMBOL)

        self.stop(trader_inst)

    def test_get_all_currencies_price_ticker(self):
        _, exchange_inst, _, trader_inst = self.init_default()

        exchange_inst.get_all_currencies_price_ticker()

        self.stop(trader_inst)

    def test_should_update_data(self):
        _, exchange_inst, exchange_simulator, trader_inst = self.init_default()

        # first call
        assert exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR, trader_inst)
        assert exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS, trader_inst)
        assert exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY, trader_inst)

        # call get prices
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        # call with trader without order
        assert exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY, trader_inst)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)

        trader_inst.get_order_manager().order_list = [1]
        # call with trader with order and not recent trade
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY, trader_inst)

        # call with trader with order and not enough recent trade
        exchange_simulator.fetched_trades_counter[self.DEFAULT_SYMBOL] += 1
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY, trader_inst)

        # call with trader with order and enough recent trade
        exchange_simulator.fetched_trades_counter[self.DEFAULT_SYMBOL] += 2
        assert exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY, trader_inst)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)

        # call with trader with order and not enough recent trade
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY, trader_inst)

        # call with trader with order and enough recent trade
        exchange_simulator.fetched_trades_counter[self.DEFAULT_SYMBOL] += 1
        assert exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR, trader_inst)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        assert exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS, trader_inst)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY, trader_inst)

        # call with trader with order and not enough recent trade
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY, trader_inst)

        # call with trader with order and enough recent trade
        exchange_simulator.fetched_trades_counter[self.DEFAULT_SYMBOL] += 1
        assert exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS, trader_inst)
        assert not exchange_simulator.should_update_data(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY, trader_inst)

        self.stop(trader_inst)

    def test_should_update_recent_trades(self):
        _, exchange_inst, exchange_simulator, trader_inst = self.init_default()

        assert exchange_simulator.should_update_recent_trades(self.DEFAULT_SYMBOL)
        exchange_simulator.time_frame_get_times[self.DEFAULT_TF.value] += 1

        assert exchange_simulator.should_update_recent_trades(self.DEFAULT_SYMBOL)

        # call with not enough time frame refresh
        assert not exchange_simulator.should_update_recent_trades(self.DEFAULT_SYMBOL)

        exchange_simulator.time_frame_get_times[self.DEFAULT_TF.value] += 1
        assert exchange_simulator.should_update_recent_trades(self.DEFAULT_SYMBOL)

        # call with not enough time frame refresh
        assert not exchange_simulator.should_update_recent_trades(self.DEFAULT_SYMBOL)
        assert not exchange_simulator.should_update_recent_trades(self.DEFAULT_SYMBOL)

        self.stop(trader_inst)
