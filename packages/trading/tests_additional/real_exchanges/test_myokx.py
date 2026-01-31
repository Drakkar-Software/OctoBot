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

from octobot_commons.enums import TimeFrames, PriceIndexes
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc, \
    ExchangeConstantsOrderBookInfoColumns as Ecobic, ExchangeConstantsOrderColumns as Ecoc, \
    ExchangeConstantsTickersColumns as Ectc
from tests_additional.real_exchanges.real_exchange_tester import RealExchangeTester
# required to catch async loop context exceptions
from tests import event_loop

import tests_additional.real_exchanges.test_okx as test_okx

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestMyOkxRealExchangeTester(test_okx.TestOkxRealExchangeTester):
    EXCHANGE_NAME = "myokx"

    # myokx overrides
    async def test_active_symbols(self):
        await self.inner_test_active_symbols(2100, 2200)

    async def test_get_all_currencies_price_ticker_with_market_filter(self):
        tickers = await self.get_all_currencies_price_ticker(market_filter=self.get_market_filter())
        assert len(tickers) > 2    # all tickers
        assert self.SYMBOL in tickers
        assert self.SYMBOL_2 in tickers
        assert self.SYMBOL_3 not in tickers  # symbol not correctly parsed as not in available markets
        tickers = await self.get_all_currencies_price_ticker(
            symbols=[self.SYMBOL, self.SYMBOL_2],
            market_filter=self.get_market_filter()
        )
        assert list(tickers) == [self.SYMBOL, self.SYMBOL_2]    # ticker for self.SYMBOL, self.SYMBOL_2
        for symbol, ticker in tickers.items():
            self._check_ticker(ticker, symbol)
