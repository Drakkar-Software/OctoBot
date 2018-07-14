import ccxt

from config.cst import CONFIG_ENABLED_OPTION, CONFIG_BACKTESTING, TimeFrames, HOURS_TO_MSECONDS, PriceIndexes
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
        assert exchange_simulator.should_update_data(TimeFrames.ONE_HOUR)
        assert exchange_simulator.should_update_data(TimeFrames.FOUR_HOURS)
        assert exchange_simulator.should_update_data(TimeFrames.ONE_DAY)

        # call get prices
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        # call with trader without order
        assert exchange_simulator.should_update_data(TimeFrames.ONE_HOUR)
        assert not exchange_simulator.should_update_data(TimeFrames.FOUR_HOURS)
        assert not exchange_simulator.should_update_data(TimeFrames.ONE_DAY)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)

        self.stop(trader_inst)
