#  Drakkar-Software OctoBot-Trading
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
import os
from math import nan

from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc, \
    ExchangeConstantsMarketStatusInfoColumns as Ecmsic
from octobot_trading.exchanges.util.exchange_market_status_fixer import ExchangeMarketStatusFixer


class TestExchangeMarketStatusFixer:

    @staticmethod
    def _get_limits(amount_min=None, amount_max=None,
                    price_min=None, price_max=None,
                    cost_min=None, cost_max=None):
        return {
            Ecmsc.LIMITS_AMOUNT.value: {
                Ecmsc.LIMITS_AMOUNT_MIN.value: amount_min,
                Ecmsc.LIMITS_AMOUNT_MAX.value: amount_max,
            },
            Ecmsc.LIMITS_PRICE.value: {
                Ecmsc.LIMITS_PRICE_MIN.value: price_min,
                Ecmsc.LIMITS_PRICE_MAX.value: price_max,
            },
            Ecmsc.LIMITS_COST.value: {
                Ecmsc.LIMITS_COST_MIN.value: cost_min,
                Ecmsc.LIMITS_COST_MAX.value: cost_max,
            },
        }

    @staticmethod
    def _get_precision(precision_amount=None, precision_cost=None, precision_price=None):
        return {
            Ecmsc.PRECISION_AMOUNT.value: precision_amount,
            Ecmsc.PRECISION_PRICE.value: precision_price,
        }

    # Global
    def test_exchange_market_status_fixer_without_precision_cost_and_amount_with_price(self):
        current_price = 4564.1458

        ms = {
            Ecmsc.PRECISION.value: self._get_precision(1, 0, 1),
            Ecmsc.LIMITS.value: self._get_limits(None, nan, 0.05, 1e4, nan, None)
        }

        assert ExchangeMarketStatusFixer(ms, price_example=current_price).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(1, 0, 1),
            Ecmsc.LIMITS.value: self._get_limits(
                0.002190990480628382, 21909.904806283797,
                0.05, 10000.0,
                0, 219099048.062838
            )
        }

        ms = {
            Ecmsc.PRECISION.value: self._get_precision(nan, None, nan),
            Ecmsc.LIMITS.value: self._get_limits(None, nan, 0.05, 1e4, nan, None)
        }

        assert ExchangeMarketStatusFixer(ms, price_example=current_price).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(4, 4, 4),
            Ecmsc.LIMITS.value: self._get_limits(
                0.002190990480628382, 21909.904806283797,
                0.05, 10000.0,
                0, 219099048.062838
            )
        }

        current_price = 1.56e-6
        ms = {
            Ecmsc.PRECISION.value: self._get_precision(nan, None, nan),
            Ecmsc.LIMITS.value: self._get_limits(None, nan, None, None, nan, None)
        }

        assert ExchangeMarketStatusFixer(ms, price_example=current_price).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(8, 8, 8),
            Ecmsc.LIMITS.value: self._get_limits(
                641.0256410256403, 64102564102564.04,
                1.5600000000000002e-09, 0.0015600000000000002,
                0, 99999999999.99991
            )
        }

        current_price = 1.5678999
        ms = {
            Ecmsc.PRECISION.value: self._get_precision(nan, None, nan),
            Ecmsc.LIMITS.value: self._get_limits(None, nan, 0, 0, nan, None)
        }

        assert ExchangeMarketStatusFixer(ms, price_example=current_price).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(7, 7, 7),
            Ecmsc.LIMITS.value: self._get_limits(
                6.37795818470299, 63779581.84702988,
                0.0015678999, 1567.8999000000001,
                0, 99999999999.99997
            )
        }

        current_price = 25.87257
        ms = {
            Ecmsc.PRECISION.value: self._get_precision(),
            Ecmsc.LIMITS.value: self._get_limits(None, None, 0, 0, 11, None)
        }

        assert ExchangeMarketStatusFixer(ms, price_example=current_price).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(5, 5, 5),
            Ecmsc.LIMITS.value: self._get_limits(
                0.3865097282566056, 3865097.2825660524,
                0.02587257, current_price * 1000,
                11, 99999999999.99997
            )
        }

        current_price = 200.555
        ms = {
            Ecmsc.PRECISION.value: self._get_precision(nan, nan, nan),
            Ecmsc.LIMITS.value: self._get_limits(nan, nan, 3, 3, nan, nan)
        }

        assert ExchangeMarketStatusFixer(ms, price_example=current_price).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(3, 3, 3),
            Ecmsc.LIMITS.value: self._get_limits(
                0.04986163396574511, 498616.3396574511,
                3, 3,
                0, 1495849.0189723533
            )
        }

    def test_exchange_market_status_fixer_without_market_status(self):
        assert ExchangeMarketStatusFixer({}).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(None, None, None),
            Ecmsc.LIMITS.value: self._get_limits(None, None, None, None, 0, None)
        }

    def test_exchange_market_status_fixer_with_str_instead_of_floats(self):
        ms = {
            Ecmsc.PRECISION.value: self._get_precision("5", "5.777772", None),
            Ecmsc.LIMITS.value: self._get_limits("0.05", "1e4", "0.01", "1e4", "3.3", "11111111111")
        }

        assert ExchangeMarketStatusFixer(ms).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(5, 5.777772, None),
            Ecmsc.LIMITS.value: self._get_limits(0.05, 1e4, 0.01, 1e4, 3.3, 11111111111)
        }

        assert ExchangeMarketStatusFixer(
            {Ecmsc.LIMITS.value: self._get_limits("0.05", "1e4", "plop", nan, "3.3", "11111111111")}
        ).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(None, None, None),
            # replace "plop" and nan with computed numbers
            Ecmsc.LIMITS.value: self._get_limits(0.05, 1e4, None, None, 3.3, 11111111111)
        }

        # missing and added keys
        limits = self._get_limits("0.05", "1e4", "plop", nan, "3.3", "11111111111")
        limits["plop"] = {"a": "1"}
        limits[Ecmsc.LIMITS_AMOUNT.value]["plop"] = "2"
        limits[Ecmsc.LIMITS_AMOUNT.value].pop(Ecmsc.LIMITS_AMOUNT_MIN.value)

        expected_limits = self._get_limits(0.05, 1e4, None, None, 3.3, 11111111111)
        expected_limits[Ecmsc.LIMITS_AMOUNT.value].pop(Ecmsc.LIMITS_AMOUNT_MIN.value)
        expected_limits[Ecmsc.LIMITS_AMOUNT.value]["plop"] = "2"
        expected_limits["plop"] = {"a": "1"}

        assert ExchangeMarketStatusFixer(
            {Ecmsc.LIMITS.value: limits}
        ).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(None, None, None),
            # replace "plop" and nan with computed numbers
            Ecmsc.LIMITS.value: expected_limits
        }

    def test_exchange_market_status_fixer_without_cost(self):
        ms = {
            Ecmsc.PRECISION.value: self._get_precision(5, 5, 5),
            Ecmsc.LIMITS.value: self._get_limits(0.05, 1e4, 0.01, 1e4, None, None)
        }

        assert ExchangeMarketStatusFixer(ms).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(5, 5, 5),
            Ecmsc.LIMITS.value: self._get_limits(0.05, 1e4, 0.01, 1e4, 0.01 * 0.05, 1e4 * 1e4)
        }

    def test_exchange_market_status_fixer_without_price(self):
        ms = {
            Ecmsc.PRECISION.value: self._get_precision(5, 5, 5),
            Ecmsc.LIMITS.value: self._get_limits(0.01, 1e3, nan, nan, 0.05, 1e5)
        }

        assert ExchangeMarketStatusFixer(ms).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(5, 5, 5),
            Ecmsc.LIMITS.value: self._get_limits(0.01, 1e3, None, None, 0.05, 1e5)
        }

    def test_exchange_market_status_fixer_without_price_amount(self):
        ms = {
            Ecmsc.PRECISION.value: self._get_precision(5, 5, 5),
            Ecmsc.LIMITS.value: self._get_limits(nan, None, 0.03, 1e4, 0.05, 1e7)
        }

        assert ExchangeMarketStatusFixer(ms).market_status == {
            Ecmsc.PRECISION.value: self._get_precision(5, 5, 5),
            Ecmsc.LIMITS.value: self._get_limits(0.05 / 0.03, 1e7 / 1e4, 0.03, 1e4, 0.05, 1e7)
        }

    # Limits
    def test_fix_market_status_limits(self):
        if not os.getenv('CYTHON_IGNORE'):
            from octobot_trading.exchanges.util.exchange_market_status_fixer import check_market_status_limits
            assert not check_market_status_limits(self._get_limits(4, None, None, 1000, 56, 45))
            assert not check_market_status_limits(self._get_limits(9, None, 5066, 1000, 56, nan))
            assert not check_market_status_limits(self._get_limits(8, nan, 789, 1000, nan, 45))
            assert not check_market_status_limits(self._get_limits(0, 0, 789, 1000, 0, 45))
            assert check_market_status_limits(self._get_limits(12, 2752783, 242, 1000, 56, 45))

    def test_check_market_status_values(self):
        if not os.getenv('CYTHON_IGNORE'):
            from octobot_trading.exchanges.util.exchange_market_status_fixer import check_market_status_values
            assert not check_market_status_values([78272, None, None, 5e-10, 100, 0.12])
            assert not check_market_status_values([78272, None, nan, 5e-10, 100, 0.12])
            assert not check_market_status_values([78272, nan, nan, 5e-10, 100, 0.12])
            assert not check_market_status_values([78272, 0, 0, 5e-10, 100, 0.12])
            assert check_market_status_values([17, 78272, 79, 5e-10, 145, 100])

    def test_fix_market_status_limits_with_price(self):
        emsf = ExchangeMarketStatusFixer({}, 98765)
        if not os.getenv('CYTHON_IGNORE'):
            emsf._fix_market_status_limits_with_price()
            assert emsf.market_status[Ecmsc.LIMITS.value] == self._get_limits(
                0.00010125044297068805, 1012.5044297068805,
                98.765, 98765000,
                0.010000000000000005, 100000000000.00005
            )

            emsf = ExchangeMarketStatusFixer({}, 0.00123456)
            emsf._fix_market_status_limits_with_price()
            assert emsf.market_status[Ecmsc.LIMITS.value] == self._get_limits(
                0.8100051840331779, 81000518403.3177,
                1.23456e-06, 1.23456,
                1.0000000000000002e-06, 99999999999.99991
            )

            emsf = ExchangeMarketStatusFixer({}, 0.0000012)
            emsf._fix_market_status_limits_with_price()
            assert emsf.market_status[Ecmsc.LIMITS.value] == self._get_limits(
                833.3333333333311, 83333333333333.28,
                1.2e-09, 0.0012,
                9.999999999999974e-07, 99999999999.99992
            )

            emsf = ExchangeMarketStatusFixer({}, 0.000999)
            emsf._fix_market_status_limits_with_price()
            assert emsf.market_status[Ecmsc.LIMITS.value] == self._get_limits(
                1.001001001001, 100100100100.09999,
                9.99e-07, 0.9990000000000001,
                9.999999999999991e-07, 99999999999.99991
            )

            emsf = ExchangeMarketStatusFixer({
                Ecmsc.LIMITS.value: self._get_limits(cost_min=1, cost_max=11000.33)
            }, 0.000999)
            emsf._fix_market_status_limits_with_price()
            assert emsf.market_status[Ecmsc.LIMITS.value] == self._get_limits(
                1.001001001001, 100100100100.09999,
                9.99e-07, 0.9990000000000001,
                1, 11000.33
            )

            emsf = ExchangeMarketStatusFixer({
                Ecmsc.LIMITS.value: self._get_limits(
                    amount_min=0.1, amount_max=10000,
                    price_min=44, price_max=4444,
                )
            }, 52)
            # cost min max computed using price & amount
            emsf._fix_market_status_limits_with_price()
            assert emsf.market_status[Ecmsc.LIMITS.value] == self._get_limits(
                0.1, 10000,
                44, 4444,
                4.4, 44440000
            )

            # cost max ONLY computed using price & amount (missing min price)
            emsf = ExchangeMarketStatusFixer({
                Ecmsc.LIMITS.value: self._get_limits(
                    amount_min=0.1, amount_max=10000,
                    price_max=4444,
                )
            }, 52)
            assert emsf.market_status[Ecmsc.LIMITS.value] == self._get_limits(
                0.1, 10000,
                0.052, 4444,
                0, 44440000    # min cost impossible to compute (no exchange info)
            )
            # min cost inferred from price (2nd call: consider min price as 'from exchange')
            emsf._fix_market_status_limits_with_price()
            assert emsf.market_status[Ecmsc.LIMITS.value] == self._get_limits(
                0.1, 10000,
                0.052, 4444,
                0.0052, 44440000
            )

    # Precision
    def test_get_price_precision(self):
        if not os.getenv('CYTHON_IGNORE'):
            assert ExchangeMarketStatusFixer({}, 10.5555)._get_price_precision() == 4
            assert ExchangeMarketStatusFixer({}, 1014578587.5)._get_price_precision() == 1
            assert ExchangeMarketStatusFixer({}, 1.00000000055)._get_price_precision() == 11
            assert ExchangeMarketStatusFixer({}, 1)._get_price_precision() == 0

    def test_fix_market_status_precision_with_price(self):
        if not os.getenv('CYTHON_IGNORE'):
            emsf = ExchangeMarketStatusFixer({}, 10234.55)
            emsf._fix_market_status_precision_with_price()
            assert emsf.market_status[Ecmsc.PRECISION.value] == self._get_precision(2, 2, 2)

            emsf = ExchangeMarketStatusFixer({}, 10234)
            emsf._fix_market_status_precision_with_price()
            assert emsf.market_status[Ecmsc.PRECISION.value] == self._get_precision(0, 0, 0)

            emsf = ExchangeMarketStatusFixer({}, 10.234140561412567)
            emsf._fix_market_status_precision_with_price()
            assert emsf.market_status[Ecmsc.PRECISION.value] == self._get_precision(15, 15, 15)

    # Specific
    def test_fix_market_status_precision_with_specific(self):
        pass

    def test_fix_market_status_limits_with_specific(self):
        # binance specific
        market_status = {
            Ecmsc.INFO.value: {
                Ecmsic.FILTERS.value: [
                    {
                        Ecmsic.FILTER_TYPE.value: Ecmsic.PRICE_FILTER.value,
                        Ecmsic.MAX_PRICE.value: 123456789,
                        Ecmsic.MIN_PRICE.value: 0.1234567
                    },
                    {
                        Ecmsic.FILTER_TYPE.value: Ecmsic.LOT_SIZE.value,
                        Ecmsic.MAX_QTY.value: 9e11,
                        Ecmsic.MIN_QTY.value: 5e-11
                    }
                ]
            }
        }
        emsf = ExchangeMarketStatusFixer(market_status)
        if not os.getenv('CYTHON_IGNORE'):
            emsf._fix_market_status_limits_with_specific()
            assert emsf.market_status[Ecmsc.LIMITS.value] == self._get_limits(5e-11, 9e11,
                                                                              0.1234567, 123456789,
                                                                              5e-11 * 0.1234567, 9e11 * 123456789)
