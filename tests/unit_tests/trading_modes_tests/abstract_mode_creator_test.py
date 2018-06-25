import math

import ccxt

from config.cst import EvaluatorStates
from tests.test_utils.config import load_test_config
from trading.exchanges.exchange_manager import ExchangeManager
from trading.trader.modes import AbstractTradingModeCreator
from trading.trader.portfolio import Portfolio
from trading.trader.trader_simulator import TraderSimulator
from config.cst import ExchangeConstantsMarketStatusColumns as Ecmsc


class TestAbstractTradingModeCreator:
    @staticmethod
    def _get_tools():
        config = load_test_config()
        symbol = "BTC/USDT"
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        exchange_inst = exchange_manager.get_exchange()
        trader_inst = TraderSimulator(config, exchange_inst, 0.3)
        trader_inst.stop_order_manager()
        trader_inst.portfolio.portfolio["SUB"] = {
            Portfolio.TOTAL: 0.000000000000000000005,
            Portfolio.AVAILABLE: 0.000000000000000000005
        }
        trader_inst.portfolio.portfolio["BNB"] = {
            Portfolio.TOTAL: 0.000000000000000000005,
            Portfolio.AVAILABLE: 0.000000000000000000005
        }
        trader_inst.portfolio.portfolio["USDT"] = {
            Portfolio.TOTAL: 2000,
            Portfolio.AVAILABLE: 2000
        }

        return config, exchange_inst, trader_inst, symbol

    def test_can_create_order(self):
        config, exchange, trader, symbol = self._get_tools()
        portfolio = trader.get_portfolio()
        # portfolio: "BTC": 10 "USD": 1000
        not_owned_symbol = "ETH/BTC"
        not_owned_market = "BTC/ETH"
        min_trigger_symbol = "SUB/BTC"
        min_trigger_market = "ADA/BNB"

        # order from neutral state => false
        assert not AbstractTradingModeCreator(None).can_create_order(symbol, exchange,
                                                                     EvaluatorStates.NEUTRAL, portfolio)

        # sell order using a currency with 0 available
        assert not AbstractTradingModeCreator(None).can_create_order(not_owned_symbol, exchange,
                                                                     EvaluatorStates.SHORT, portfolio)
        assert not AbstractTradingModeCreator(None).can_create_order(not_owned_symbol, exchange,
                                                                     EvaluatorStates.VERY_SHORT, portfolio)

        # sell order using a currency with < min available
        assert not AbstractTradingModeCreator(None).can_create_order(min_trigger_symbol, exchange,
                                                                     EvaluatorStates.SHORT, portfolio)
        assert not AbstractTradingModeCreator(None).can_create_order(min_trigger_symbol, exchange,
                                                                     EvaluatorStates.VERY_SHORT, portfolio)

        # sell order using a currency with > min available
        assert AbstractTradingModeCreator(None).can_create_order(not_owned_market, exchange,
                                                                 EvaluatorStates.SHORT, portfolio)
        assert AbstractTradingModeCreator(None).can_create_order(not_owned_market, exchange,
                                                                 EvaluatorStates.VERY_SHORT, portfolio)

        # buy order using a market with 0 available
        assert not AbstractTradingModeCreator(None).can_create_order(not_owned_market, exchange,
                                                                     EvaluatorStates.LONG, portfolio)
        assert not AbstractTradingModeCreator(None).can_create_order(not_owned_market, exchange,
                                                                     EvaluatorStates.VERY_LONG, portfolio)

        # buy order using a market with < min available
        assert not AbstractTradingModeCreator(None).can_create_order(min_trigger_market, exchange,
                                                                     EvaluatorStates.LONG, portfolio)
        assert not AbstractTradingModeCreator(None).can_create_order(min_trigger_market, exchange,
                                                                     EvaluatorStates.VERY_LONG, portfolio)

        # buy order using a market with > min available
        assert AbstractTradingModeCreator(None).can_create_order(not_owned_symbol, exchange,
                                                                 EvaluatorStates.LONG, portfolio)
        assert AbstractTradingModeCreator(None).can_create_order(not_owned_symbol, exchange,
                                                                 EvaluatorStates.VERY_LONG, portfolio)

    def test_can_create_order_unknown_symbols(self):
        config, exchange, trader, symbol = self._get_tools()
        portfolio = trader.get_portfolio()
        unknown_symbol = "VI?/BTC"
        unknown_market = "BTC/*s?"
        unknown_everything = "VI?/*s?"

        # buy order with unknown market
        assert not AbstractTradingModeCreator(None).can_create_order(unknown_market, exchange,
                                                                     EvaluatorStates.LONG, portfolio)
        assert not AbstractTradingModeCreator(None).can_create_order(unknown_market, exchange,
                                                                     EvaluatorStates.VERY_LONG, portfolio)
        assert AbstractTradingModeCreator(None).can_create_order(unknown_market, exchange,
                                                                 EvaluatorStates.SHORT, portfolio)
        assert AbstractTradingModeCreator(None).can_create_order(unknown_market, exchange,
                                                                 EvaluatorStates.VERY_SHORT, portfolio)

        # sell order with unknown symbol
        assert not AbstractTradingModeCreator(None).can_create_order(unknown_symbol, exchange,
                                                                     EvaluatorStates.SHORT, portfolio)
        assert not AbstractTradingModeCreator(None).can_create_order(unknown_symbol, exchange,
                                                                     EvaluatorStates.VERY_SHORT, portfolio)
        assert AbstractTradingModeCreator(None).can_create_order(unknown_symbol, exchange,
                                                                 EvaluatorStates.LONG, portfolio)
        assert AbstractTradingModeCreator(None).can_create_order(unknown_symbol, exchange,
                                                                 EvaluatorStates.VERY_LONG, portfolio)

        # neutral state with unknown symbol, market and everything
        assert not AbstractTradingModeCreator(None).can_create_order(unknown_symbol, exchange,
                                                                     EvaluatorStates.NEUTRAL, portfolio)
        assert not AbstractTradingModeCreator(None).can_create_order(unknown_market, exchange,
                                                                     EvaluatorStates.NEUTRAL, portfolio)
        assert not AbstractTradingModeCreator(None).can_create_order(unknown_everything, exchange,
                                                                     EvaluatorStates.NEUTRAL, portfolio)

    def test_valid_create_new_order(self):
        config, exchange, trader, symbol = self._get_tools()
        portfolio = trader.get_portfolio()
        order_creator = AbstractTradingModeCreator(None)

        # should raise NotImplementedError Exception
        try:
            order_creator.create_new_order(-1, symbol, exchange, trader, portfolio, EvaluatorStates.NEUTRAL)
            order_creator.create_new_order(1, symbol, exchange, trader, portfolio, EvaluatorStates.VERY_SHORT)
            order_creator.create_new_order(-0.65, symbol, exchange, trader, portfolio, EvaluatorStates.LONG)
            order_creator.create_new_order(-1, symbol, exchange, trader, portfolio, EvaluatorStates.VERY_LONG)
            assert False
        except NotImplementedError:
            assert True

    # Commented line are related to #261
    def test_adapt_price(self):
        # will use symbol market
        symbol_market = {Ecmsc.PRECISION.value: {Ecmsc.PRECISION_PRICE.value: 4}}
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.0001) == 0.0001
        # assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.00015) == 0.00015
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.005) == 0.005
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 1) == 1.0000000000000000000000001

        # TODO : digit number is not only after comma ?
        # assert AbstractTradingModeCreator.adapt_price(symbol_market, 56.5128597145) == 56.5128
        # assert AbstractTradingModeCreator.adapt_price(symbol_market, 1251.0000014576121234854513) == 1251.0000

        # will use default (CURRENCY_DEFAULT_MAX_PRICE_DIGITS)
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.0001) == 0.0001
        # assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.00015) == 0.00015
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.005) == 0.005
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 1) == 1.0000000000000000000000001

        # TODO : digit number is not only after comma ?
        # assert AbstractTradingModeCreator.adapt_price(symbol_market, 56.5128597145) == 56.51285971
        # assert AbstractTradingModeCreator.adapt_price(symbol_market, 1251.0000014576121234854513) == 1251.00000145

    def test_get_additional_dusts_to_quantity_if_necessary(self):
        pass

    def test_check_and_adapt_order_details_if_necessary(self):
        pass

    def test_get_pre_order_data(self):
        pass

    def test_adapt_quantity(self):
        pass

    def test_adapt_order_quantity_because_quantity(self):
        pass

    def test_adapt_order_quantity_because_price(self):
        pass

    @staticmethod
    def test_trunc_with_n_decimal_digits():
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(1.00000000001, 10) == 1
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(1.00000000001, 11) == 1.00000000001
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 3) == 578
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 4) == 578.0001
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 7) == 578.000145
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 9) == 578.000145
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 10) == 578.0001450001
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 12) == 578.000145000156

    def test_get_value_or_default(self):
        test_dict = {"a": 1, "b": 2, "c": 3}
        assert AbstractTradingModeCreator._get_value_or_default(test_dict, "b", default="") == 2
        assert AbstractTradingModeCreator._get_value_or_default(test_dict, "d") is math.nan
        assert AbstractTradingModeCreator._get_value_or_default(test_dict, "d", default="") == ""
