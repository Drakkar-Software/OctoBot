import ccxt

from config import CONFIG_ENABLED_OPTION, CONFIG_BACKTESTING, TimeFrames, HOURS_TO_SECONDS, PriceIndexes, \
    TraderOrderType, ExchangeConstantsMarketPropertyColumns, FeePropertyColumns, CONFIG_SIMULATOR, \
    CONFIG_SIMULATOR_FEES, CONFIG_SIMULATOR_FEES_MAKER, CONFIG_SIMULATOR_FEES_TAKER
from tests.test_utils.config import load_test_config
from trading.exchanges.exchange_manager import ExchangeManager
from trading.trader.trader_simulator import TraderSimulator
from trading.trader.order import OrderConstants


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
        exchange_simulator.init_candles_offset([TimeFrames.ONE_HOUR, TimeFrames.FOUR_HOURS, TimeFrames.ONE_DAY],
                                               TestExchangeSimulator.DEFAULT_SYMBOL)

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
        assert first_data[PriceIndexes.IND_PRICE_CLOSE.value][0] == second_data[PriceIndexes.IND_PRICE_CLOSE.value][0]
        assert first_data[PriceIndexes.IND_PRICE_TIME.value][0] == second_data[
            PriceIndexes.IND_PRICE_TIME.value][0]

        # end is end -1 with DEFAULT_TF difference
        assert first_data[PriceIndexes.IND_PRICE_CLOSE.value][-1] == second_data[PriceIndexes.IND_PRICE_CLOSE.value][-2]
        assert first_data[PriceIndexes.IND_PRICE_TIME.value][-1] + HOURS_TO_SECONDS == second_data[
            PriceIndexes.IND_PRICE_TIME.value][-1]

    def test_get_recent_trades(self):
        _, exchange_inst, _, trader_inst = self.init_default()
        self.stop(trader_inst)

        exchange_inst.get_recent_trades(self.DEFAULT_SYMBOL)

    def test_get_all_currencies_price_ticker(self):
        _, exchange_inst, _, trader_inst = self.init_default()
        self.stop(trader_inst)

        exchange_inst.get_all_currencies_price_ticker()

    @staticmethod
    def _assert_fee(fee, currency, price, rate, fee_type):
        assert fee[FeePropertyColumns.CURRENCY.value] == currency
        assert fee[FeePropertyColumns.COST.value] == price
        assert fee[FeePropertyColumns.RATE.value] == rate
        assert fee[FeePropertyColumns.TYPE.value] == fee_type

    def test_get_trade_fee(self):
        _, exchange_inst, _, trader_inst = self.init_default()

        # force fees
        exchange_inst.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES] = {
            CONFIG_SIMULATOR_FEES_MAKER: 0.05,
            CONFIG_SIMULATOR_FEES_TAKER: 0.1
        }

        buy_market_fee = exchange_inst.get_trade_fee("BTC/USD",
                                                     OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_MARKET],
                                                     10, 100, ExchangeConstantsMarketPropertyColumns.TAKER.value)
        self._assert_fee(buy_market_fee, "BTC", 0.01, 0.001, ExchangeConstantsMarketPropertyColumns.TAKER.value)

        sell_market_fee = exchange_inst.get_trade_fee(
            "BTC/USD",  OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_MARKET],
            10, 100, ExchangeConstantsMarketPropertyColumns.TAKER.value)
        self._assert_fee(sell_market_fee, "USD", 1, 0.001, ExchangeConstantsMarketPropertyColumns.TAKER.value)

        buy_limit_fee = exchange_inst.get_trade_fee("BTC/USD",
                                                    OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_LIMIT],
                                                    10, 100, ExchangeConstantsMarketPropertyColumns.MAKER.value)
        self._assert_fee(buy_limit_fee, "BTC", 0.005, 0.0005, ExchangeConstantsMarketPropertyColumns.MAKER.value)

        sell_limit_fee = exchange_inst.get_trade_fee("BTC/USD",
                                                     OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT],
                                                     10, 100, ExchangeConstantsMarketPropertyColumns.TAKER.value)
        self._assert_fee(sell_limit_fee, "USD", 1, 0.001, ExchangeConstantsMarketPropertyColumns.TAKER.value)

    def test_should_update_data(self):
        _, exchange_inst, exchange_simulator, trader_inst = self.init_default()

        # first call
        assert exchange_simulator.should_update_data(TimeFrames.ONE_HOUR, self.DEFAULT_SYMBOL)
        assert exchange_simulator.should_update_data(TimeFrames.FOUR_HOURS, self.DEFAULT_SYMBOL)
        assert exchange_simulator.should_update_data(TimeFrames.ONE_DAY, self.DEFAULT_SYMBOL)

        # call get prices
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.FOUR_HOURS)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_DAY)

        # call with trader without order
        assert exchange_simulator.should_update_data(TimeFrames.ONE_HOUR, self.DEFAULT_SYMBOL)
        assert not exchange_simulator.should_update_data(TimeFrames.FOUR_HOURS, self.DEFAULT_SYMBOL)
        assert not exchange_simulator.should_update_data(TimeFrames.ONE_DAY, self.DEFAULT_SYMBOL)
        exchange_inst.get_symbol_prices(self.DEFAULT_SYMBOL, TimeFrames.ONE_HOUR)

        self.stop(trader_inst)

    @staticmethod
    def _get_start_index_for_timeframe(nb_candles, min_limit, timeframe_multiplier):
        return int(nb_candles - (nb_candles-min_limit) / timeframe_multiplier) - 1

    def test_init_candles_offset(self):
        _, exchange_inst, exchange_simulator, trader_inst = self.init_default()

        timeframes = [TimeFrames.THIRTY_MINUTES, TimeFrames.ONE_HOUR, TimeFrames.TWO_HOURS,
                      TimeFrames.FOUR_HOURS, TimeFrames.ONE_DAY]
        exchange_simulator.init_candles_offset(timeframes, self.DEFAULT_SYMBOL)

        offsets = exchange_simulator.time_frames_offset[self.DEFAULT_SYMBOL]
        nb_candles = len(exchange_simulator.data[self.DEFAULT_SYMBOL][TimeFrames.THIRTY_MINUTES.value])
        assert offsets[TimeFrames.THIRTY_MINUTES.value] == \
            self._get_start_index_for_timeframe(nb_candles, exchange_simulator.MIN_LIMIT, 1) + 1
        assert offsets[TimeFrames.ONE_HOUR.value] ==  \
            self._get_start_index_for_timeframe(nb_candles, exchange_simulator.MIN_LIMIT, 2)
        assert offsets[TimeFrames.TWO_HOURS.value] ==  \
            self._get_start_index_for_timeframe(nb_candles, exchange_simulator.MIN_LIMIT, 4)
        assert offsets[TimeFrames.FOUR_HOURS.value] ==  \
            self._get_start_index_for_timeframe(nb_candles, exchange_simulator.MIN_LIMIT, 8)
        assert offsets[TimeFrames.ONE_DAY.value] == 244
