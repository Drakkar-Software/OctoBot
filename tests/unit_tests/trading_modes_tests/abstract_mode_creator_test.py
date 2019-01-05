#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import math
import pytest

import ccxt

from config import EvaluatorStates
from tests.test_utils.config import load_test_config
from trading.exchanges.exchange_manager import ExchangeManager
from trading.trader.modes import AbstractTradingModeCreator
from trading.trader.portfolio import Portfolio
from trading.trader.trader_simulator import TraderSimulator
from config import ExchangeConstantsMarketStatusColumns as Ecmsc


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestAbstractTradingModeCreator:
    @staticmethod
    async def _get_tools():
        config = load_test_config()
        symbol = "BTC/USDT"
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        await exchange_manager.initialize()
        exchange_inst = exchange_manager.get_exchange()
        trader_inst = TraderSimulator(config, exchange_inst, 0.3)
        await trader_inst.portfolio.initialize()
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

    async def test_can_create_order(self):
        _, exchange, trader, symbol = await self._get_tools()
        portfolio = trader.get_portfolio()
        # portfolio: "BTC": 10 "USD": 1000
        not_owned_symbol = "ETH/BTC"
        not_owned_market = "BTC/ETH"
        min_trigger_symbol = "SUB/BTC"
        min_trigger_market = "ADA/BNB"

        # order from neutral state => false
        assert not await AbstractTradingModeCreator(None).can_create_order(symbol, exchange,
                                                                           EvaluatorStates.NEUTRAL, portfolio)

        # sell order using a currency with 0 available
        assert not await AbstractTradingModeCreator(None).can_create_order(not_owned_symbol, exchange,
                                                                           EvaluatorStates.SHORT, portfolio)
        assert not await AbstractTradingModeCreator(None).can_create_order(not_owned_symbol, exchange,
                                                                           EvaluatorStates.VERY_SHORT, portfolio)

        # sell order using a currency with < min available
        assert not await AbstractTradingModeCreator(None).can_create_order(min_trigger_symbol, exchange,
                                                                           EvaluatorStates.SHORT, portfolio)
        assert not await AbstractTradingModeCreator(None).can_create_order(min_trigger_symbol, exchange,
                                                                           EvaluatorStates.VERY_SHORT, portfolio)

        # sell order using a currency with > min available
        assert AbstractTradingModeCreator(None).can_create_order(not_owned_market, exchange,
                                                                 EvaluatorStates.SHORT, portfolio)
        assert AbstractTradingModeCreator(None).can_create_order(not_owned_market, exchange,
                                                                 EvaluatorStates.VERY_SHORT, portfolio)

        # buy order using a market with 0 available
        assert not await AbstractTradingModeCreator(None).can_create_order(not_owned_market, exchange,
                                                                           EvaluatorStates.LONG, portfolio)
        assert not await AbstractTradingModeCreator(None).can_create_order(not_owned_market, exchange,
                                                                           EvaluatorStates.VERY_LONG, portfolio)

        # buy order using a market with < min available
        assert not await AbstractTradingModeCreator(None).can_create_order(min_trigger_market, exchange,
                                                                           EvaluatorStates.LONG, portfolio)
        assert not await AbstractTradingModeCreator(None).can_create_order(min_trigger_market, exchange,
                                                                           EvaluatorStates.VERY_LONG, portfolio)

        # buy order using a market with > min available
        assert AbstractTradingModeCreator(None).can_create_order(not_owned_symbol, exchange,
                                                                 EvaluatorStates.LONG, portfolio)
        assert AbstractTradingModeCreator(None).can_create_order(not_owned_symbol, exchange,
                                                                 EvaluatorStates.VERY_LONG, portfolio)

    async def test_can_create_order_unknown_symbols(self):
        _, exchange, trader, _ = await self._get_tools()
        portfolio = trader.get_portfolio()
        unknown_symbol = "VI?/BTC"
        unknown_market = "BTC/*s?"
        unknown_everything = "VI?/*s?"

        # buy order with unknown market
        assert not await AbstractTradingModeCreator(None).can_create_order(unknown_market, exchange,
                                                                           EvaluatorStates.LONG, portfolio)
        assert not await AbstractTradingModeCreator(None).can_create_order(unknown_market, exchange,
                                                                           EvaluatorStates.VERY_LONG, portfolio)
        assert AbstractTradingModeCreator(None).can_create_order(unknown_market, exchange,
                                                                 EvaluatorStates.SHORT, portfolio)
        assert AbstractTradingModeCreator(None).can_create_order(unknown_market, exchange,
                                                                 EvaluatorStates.VERY_SHORT, portfolio)

        # sell order with unknown symbol
        assert not await AbstractTradingModeCreator(None).can_create_order(unknown_symbol, exchange,
                                                                           EvaluatorStates.SHORT, portfolio)
        assert not await AbstractTradingModeCreator(None).can_create_order(unknown_symbol, exchange,
                                                                           EvaluatorStates.VERY_SHORT, portfolio)
        assert await AbstractTradingModeCreator(None).can_create_order(unknown_symbol, exchange,
                                                                       EvaluatorStates.LONG, portfolio)
        assert await AbstractTradingModeCreator(None).can_create_order(unknown_symbol, exchange,
                                                                       EvaluatorStates.VERY_LONG, portfolio)

        # neutral state with unknown symbol, market and everything
        assert not await AbstractTradingModeCreator(None).can_create_order(unknown_symbol, exchange,
                                                                           EvaluatorStates.NEUTRAL, portfolio)
        assert not await AbstractTradingModeCreator(None).can_create_order(unknown_market, exchange,
                                                                           EvaluatorStates.NEUTRAL, portfolio)
        assert not await AbstractTradingModeCreator(None).can_create_order(unknown_everything, exchange,
                                                                           EvaluatorStates.NEUTRAL, portfolio)

    async def test_valid_create_new_order(self):
        _, exchange, trader, symbol = await self._get_tools()
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

    async def test_adapt_price(self):
        # will use symbol market
        symbol_market = {Ecmsc.PRECISION.value: {Ecmsc.PRECISION_PRICE.value: 4}}
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.0001) == 0.0001
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.00015) == 0.0001
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.005) == 0.005
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 1) == 1

        assert AbstractTradingModeCreator.adapt_price(symbol_market, 56.5128597145) == 56.5128
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 1251.0000014576121234854513) == 1251.0000

        # will use default (CURRENCY_DEFAULT_MAX_PRICE_DIGITS)
        symbol_market = {Ecmsc.PRECISION.value: {}}
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.0001) == 0.0001
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.00015) == 0.00014999
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 0.005) == 0.005
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 1) == 1.0000000000000000000000001
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 1) == 1

        assert AbstractTradingModeCreator.adapt_price(symbol_market, 56.5128597145) == 56.51285971
        assert AbstractTradingModeCreator.adapt_price(symbol_market, 1251.0000014576121234854513) == 1251.00000145

    async def test_get_additional_dusts_to_quantity_if_necessary(self):
        symbol_market = {Ecmsc.LIMITS.value: {
            Ecmsc.LIMITS_AMOUNT.value: {
                Ecmsc.LIMITS_AMOUNT_MIN.value: 0.5
            },
            Ecmsc.LIMITS_COST.value: {
                Ecmsc.LIMITS_COST_MIN.value: 1
            }
        }}

        current_symbol_holding = 5
        quantity = 4
        price = 1
        assert AbstractTradingModeCreator.get_additional_dusts_to_quantity_if_necessary(quantity,
                                                                                        price,
                                                                                        symbol_market,
                                                                                        current_symbol_holding) == 0

        current_symbol_holding = 5
        quantity = 4.5
        price = 1
        assert AbstractTradingModeCreator.get_additional_dusts_to_quantity_if_necessary(quantity,
                                                                                        price,
                                                                                        symbol_market,
                                                                                        current_symbol_holding) == 0.5

        symbol_market = {Ecmsc.LIMITS.value: {
            Ecmsc.LIMITS_AMOUNT.value: {
                Ecmsc.LIMITS_AMOUNT_MIN.value: 0.005
            },
            Ecmsc.LIMITS_COST.value: {
                Ecmsc.LIMITS_COST_MIN.value: 0.00005
            }
        }}

        current_symbol_holding = 0.99000000001
        quantity = 0.9
        price = 0.5
        assert AbstractTradingModeCreator.get_additional_dusts_to_quantity_if_necessary(quantity,
                                                                                        price,
                                                                                        symbol_market,
                                                                                        current_symbol_holding) == 0

        current_symbol_holding = 0.99000000001
        quantity = 0.0215245845
        price = 0.5
        assert AbstractTradingModeCreator.get_additional_dusts_to_quantity_if_necessary(quantity,
                                                                                        price,
                                                                                        symbol_market,
                                                                                        current_symbol_holding) == 0

        current_symbol_holding = 0.99999999
        quantity = 0.99999
        price = 0.5
        exp = 0.00000999
        assert AbstractTradingModeCreator.get_additional_dusts_to_quantity_if_necessary(quantity,
                                                                                        price,
                                                                                        symbol_market,
                                                                                        current_symbol_holding) == exp

    async def test_check_and_adapt_order_details_if_necessary(self):
        atmc = AbstractTradingModeCreator(None)

        symbol_market = {
            Ecmsc.LIMITS.value: {
                Ecmsc.LIMITS_AMOUNT.value: {
                    Ecmsc.LIMITS_AMOUNT_MIN.value: 0.5,
                    Ecmsc.LIMITS_AMOUNT_MAX.value: 100,
                },
                Ecmsc.LIMITS_COST.value: {
                    Ecmsc.LIMITS_COST_MIN.value: 1,
                    Ecmsc.LIMITS_COST_MAX.value: 200
                },
                Ecmsc.LIMITS_PRICE.value: {
                    Ecmsc.LIMITS_PRICE_MIN.value: 0.5,
                    Ecmsc.LIMITS_PRICE_MAX.value: 50
                },
            },
            Ecmsc.PRECISION.value: {
                Ecmsc.PRECISION_PRICE.value: 8,
                Ecmsc.PRECISION_AMOUNT.value: 8
            }
        }

        # correct min
        quantity = 0.5
        price = 2
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [(quantity, price)]

        # correct max
        quantity = 100
        price = 2
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [(quantity, price)]

        # correct
        quantity = 10
        price = 0.6
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [(quantity, price)]

        # correct
        quantity = 3
        price = 49.9
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [(quantity, price)]

        # invalid price >
        quantity = 1
        price = 100
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == []

        # invalid price <
        quantity = 1
        price = 0.1
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == []

        # invalid cost <
        quantity = 0.5
        price = 1
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == []

        # invalid cost >
        quantity = 10
        price = 49
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [(1.83673469, 49),
                                                                                                   (4.08163265, 49),
                                                                                                   (4.08163265, 49)]

        # invalid cost with invalid price >=
        quantity = 10
        price = 50
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [(2, 50), (4, 50),
                                                                                                   (4, 50)]

        # invalid cost with invalid price >
        quantity = 10
        price = 51
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == []

        # invalid amount >
        quantity = 200
        price = 5
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == [(40.0, 5), (40.0, 5),
                                                                                                   (40.0, 5), (40.0, 5),
                                                                                                   (40.0, 5)]

        # invalid amount <
        quantity = 0.4
        price = 5
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == []

        symbol_market = {
            Ecmsc.LIMITS.value: {
                Ecmsc.LIMITS_AMOUNT.value: {
                    Ecmsc.LIMITS_AMOUNT_MIN.value: 0.0000005,
                    Ecmsc.LIMITS_AMOUNT_MAX.value: 100,
                },
                Ecmsc.LIMITS_COST.value: {
                    Ecmsc.LIMITS_COST_MIN.value: 0.00000001,
                    Ecmsc.LIMITS_COST_MAX.value: 10
                },
                Ecmsc.LIMITS_PRICE.value: {
                    Ecmsc.LIMITS_PRICE_MIN.value: 0.000005,
                    Ecmsc.LIMITS_PRICE_MAX.value: 50
                },
            },
            Ecmsc.PRECISION.value: {
                Ecmsc.PRECISION_PRICE.value: 8,
                Ecmsc.PRECISION_AMOUNT.value: 8
            }
        }

        # correct quantity
        # to test _adapt_order_quantity_because_quantity
        quantity = 5000
        price = 0.001
        expected = [(100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                    (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                    (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                    (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                    (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                    (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                    (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                    (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001), (100.0, 0.001),
                    (100.0, 0.001), (100.0, 0.001)]
        assert atmc.check_and_adapt_order_details_if_necessary(quantity, price, symbol_market) == expected

    async def test_get_pre_order_data(self):
        pass

    async def test_adapt_quantity(self):
        # will use symbol market
        symbol_market = {Ecmsc.PRECISION.value: {Ecmsc.PRECISION_AMOUNT.value: 4}}
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 0.0001) == 0.0001
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 0.00015) == 0.0001
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 0.005) == 0.005
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 1) == 1.0000000000000000000000001
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 1) == 1

        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 56.5128597145) == 56.5128
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 1251.0000014576121234854513) == 1251.0000

        # will use default (0)
        symbol_market = {Ecmsc.PRECISION.value: {}}
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 0.0001) == 0
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 0.00015) == 0
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 0.005) == 0
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 1) == 1.0000000000000000000000001
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 1) == 1

        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 56.5128597145) == 56
        assert AbstractTradingModeCreator._adapt_quantity(symbol_market, 1251.0000014576121234854513) == 1251

    @staticmethod
    async def test_trunc_with_n_decimal_digits():
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(1.00000000001, 10) == 1
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(1.00000000001, 11) == 1.00000000001
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 3) == 578
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 4) == 578.0001
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 7) == 578.000145
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 9) == 578.000145
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 10) == 578.0001450001
        assert AbstractTradingModeCreator._trunc_with_n_decimal_digits(578.000145000156, 12) == 578.000145000156

    async def test_get_value_or_default(self):
        test_dict = {"a": 1, "b": 2, "c": 3}
        assert AbstractTradingModeCreator.get_value_or_default(test_dict, "b", default="") == 2
        assert AbstractTradingModeCreator.get_value_or_default(test_dict, "d") is math.nan
        assert AbstractTradingModeCreator.get_value_or_default(test_dict, "d", default="") == ""
