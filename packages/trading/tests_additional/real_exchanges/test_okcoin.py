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
import pytest

from tests_additional.real_exchanges.test_okx import TestOkxRealExchangeTester
from octobot_commons.enums import PriceIndexes
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc
# required to catch async loop context exceptions
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class _TestOkcoinRealExchangeTester(TestOkxRealExchangeTester): #unreachable ?
    EXCHANGE_NAME = "okcoin"
    SYMBOL = "BTC/USD"
    SYMBOL_2 = "ETH/USD"
    SYMBOL_3 = "NYC/USD"

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(2300, 2300)

    async def test_get_market_status(self):
        for market_status in await self.get_market_statuses():
            self.ensure_required_market_status_values(market_status)
            assert 1e-08 <= market_status[Ecmsc.PRECISION.value][
                Ecmsc.PRECISION_AMOUNT.value] < 1   # to be fixed in tentacle
            assert 1e-08 <= market_status[Ecmsc.PRECISION.value][
                Ecmsc.PRECISION_PRICE.value] < 1    # to be fixed in tentacle
            assert all(elem in market_status[Ecmsc.LIMITS.value]
                       for elem in (Ecmsc.LIMITS_AMOUNT.value,
                                    Ecmsc.LIMITS_PRICE.value,
                                    Ecmsc.LIMITS_COST.value))
            self.check_market_status_limits(market_status,
                                            normal_cost_min=1e-08,
                                            low_price_min=1e-06,  # DOGE/USD instead of /BTC
                                            low_price_max=1e-04,
                                            low_cost_min=1e-06,
                                            low_cost_max=1e-04,
                                            expect_invalid_price_limit_values=False,
                                            enable_price_and_cost_comparison=False)

    async def test_get_symbol_prices(self):
        # without limit
        symbol_prices = await self.get_symbol_prices()
        assert len(symbol_prices) == 200
        # check candles order (oldest first)
        self.ensure_elements_order(symbol_prices, PriceIndexes.IND_PRICE_TIME.value)
        # check last candle is the current candle
        assert symbol_prices[-1][PriceIndexes.IND_PRICE_TIME.value] >= self.get_time() - self.get_allowed_time_delta()

        # try with candles limit (used in candled updater)
        symbol_prices = await self.get_symbol_prices(limit=200)
        assert len(symbol_prices) == 200
        # check candles order (oldest first)
        self.ensure_elements_order(symbol_prices, PriceIndexes.IND_PRICE_TIME.value)
        # check last candle is the current candle
        assert symbol_prices[-1][PriceIndexes.IND_PRICE_TIME.value] >= self.get_time() - self.get_allowed_time_delta()
