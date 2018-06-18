import ccxt

from backtesting.collector.data_parser import DataCollectorParser
from config.cst import CONFIG_ENABLED_OPTION, CONFIG_BACKTESTING, TimeFrames, HOURS_TO_MSECONDS, PriceIndexes, \
    CONFIG_BACKTESTING_DATA_FILES
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

        # use legacy data
        exchange_simulator.data[TestExchangeSimulator.DEFAULT_SYMBOL] = DataCollectorParser.parse(
            config[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILES][0], use_legacy_parsing=True)

        trader_inst = TraderSimulator(config, exchange_inst, 1)
        return config, exchange_inst, exchange_simulator, trader_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    def test_multiple_get_symbol_prices(self):
        _, exchange_inst, _, trader_inst = self.init_default()
        self.stop(trader_inst)

        first_data = exchange_inst.get_symbol_prices(
            self.DEFAULT_SYMBOL,
            self.DEFAULT_TF,
            return_list=False)

        second_data = exchange_inst.get_symbol_prices(
            self.DEFAULT_SYMBOL,
            self.DEFAULT_TF,
            return_list=False)

        # different arrays
        assert first_data is not second_data

        # second is first with DEFAULT_TF difference
        assert first_data[PriceIndexes.IND_PRICE_CLOSE.value][1] == second_data[PriceIndexes.IND_PRICE_CLOSE.value][0]
        assert first_data[PriceIndexes.IND_PRICE_TIME.value][0] + HOURS_TO_MSECONDS == second_data[
            PriceIndexes.IND_PRICE_TIME.value][0]

        # end is end -1 with DEFAULT_TF difference
        assert first_data[PriceIndexes.IND_PRICE_CLOSE.value][-1] == second_data[PriceIndexes.IND_PRICE_CLOSE.value][-2]
        assert first_data[PriceIndexes.IND_PRICE_TIME.value][-1] + HOURS_TO_MSECONDS == second_data[
            PriceIndexes.IND_PRICE_TIME.value][-1]

    def test_get_recent_trades(self):
        _, exchange_inst, _, trader_inst = self.init_default()
        self.stop(trader_inst)

        exchange_inst.get_recent_trades(self.DEFAULT_SYMBOL)

    def test_get_all_currencies_price_ticker(self):
        _, exchange_inst, _, trader_inst = self.init_default()
        self.stop(trader_inst)

        exchange_inst.get_all_currencies_price_ticker()

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
