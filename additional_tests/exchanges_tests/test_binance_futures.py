#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import pytest

from additional_tests.exchanges_tests import abstract_authenticated_future_exchange_tester, \
    abstract_authenticated_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestBinanceFuturesAuthenticatedExchange(
    abstract_authenticated_future_exchange_tester.AbstractAuthenticatedFutureExchangeTester
):
    # enter exchange name as a class variable here
    EXCHANGE_NAME = "binance"
    CREDENTIALS_EXCHANGE_NAME = "BINANCE_FUTURES"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}:{SETTLEMENT_CURRENCY}"
    INVERSE_SYMBOL = f"{ORDER_CURRENCY}/USD:{ORDER_CURRENCY}"
    ORDER_SIZE = 10  # % of portfolio to include in test orders
    DUPLICATE_TRADES_RATIO = 0.1   # allow 10% duplicate in trades (due to trade id set to order id)
    IS_ACCOUNT_ID_AVAILABLE = False  # set False when get_account_id is not available and should be checked
    VALID_ORDER_ID = "26408108410"

    async def _set_account_types(self, account_types):
        # todo remove this and use both types when exchange-side multi portfolio is enabled
        self.exchange_manager.exchange._futures_account_types = account_types

    async def test_get_portfolio(self):
        await super().test_get_portfolio()

    async def test_get_portfolio_with_market_filter(self):
        # pass if not implemented
        pass

    async def test_get_account_id(self):
        await super().test_get_account_id()

    async def test_get_api_key_permissions(self):
        # pass if not implemented
        pass

    async def test_missing_trading_api_key_permissions(self):
        pass

    async def test_get_not_found_order(self):
        await super().test_get_not_found_order()

    async def test_get_empty_linear_and_inverse_positions(self):
        # todo ensure parse_account_positions override is still identical to origin when updating ccxt
        await super().test_get_empty_linear_and_inverse_positions()

    async def inner_test_get_empty_linear_and_inverse_positions(self):
        # todo remove this and use both types when exchange-side multi portfolio is enabled
        await self._set_account_types(
            [self.exchange_manager.exchange.LINEAR_TYPE, self.exchange_manager.exchange.INVERSE_TYPE]
        )
        await super().inner_test_get_empty_linear_and_inverse_positions()

    async def test_get_and_set_margin_type(self):
        await super().test_get_and_set_margin_type()

    async def test_get_and_set_leverage(self):
        await super().test_get_and_set_leverage()

    async def test_create_and_cancel_limit_orders(self):
        await super().test_create_and_cancel_limit_orders()

    async def inner_test_create_and_cancel_limit_orders(self, symbol=None, settlement_currency=None):
        # todo remove this and use both types when exchange-side multi portfolio is enabled
        # test with linear symbol
        await abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester\
            .inner_test_create_and_cancel_limit_orders(self)
        # test with inverse symbol
        await self._set_account_types(
            [self.exchange_manager.exchange.INVERSE_TYPE]
        )
        await abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester\
            .inner_test_create_and_cancel_limit_orders(
                self, symbol=self.INVERSE_SYMBOL, settlement_currency=self.ORDER_CURRENCY
            )

    async def test_create_and_fill_market_orders(self):
        await super().test_create_and_fill_market_orders()

    async def test_get_my_recent_trades(self):
        await super().test_get_my_recent_trades()

    async def test_get_closed_orders(self):
        await super().test_get_closed_orders()

    async def test_create_and_cancel_stop_orders(self):
        await super().test_create_and_cancel_stop_orders()

    async def test_edit_limit_order(self):
        # pass if not implemented
        pass

    async def test_edit_stop_order(self):
        # pass if not implemented
        pass

    async def test_create_single_bundled_orders(self):
        # pass if not implemented
        pass

    async def test_create_double_bundled_orders(self):
        # pass if not implemented
        pass
