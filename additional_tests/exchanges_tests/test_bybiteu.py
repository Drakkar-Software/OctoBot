#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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

from additional_tests.exchanges_tests import abstract_authenticated_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

class TestBybitEuAuthenticatedExchange(
    abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester
):
    EXCHANGE_NAME = "bybiteu"
    EXCHANGE_TENTACLE_NAME = "BybitEu"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDC"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}"
    ORDER_SIZE = 30  # % of portfolio to include in test orders
    CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = True
    EXPECT_MISSING_ORDER_FEES_DUE_TO_ORDERS_TOO_OLD_FOR_RECENT_TRADES = True

    async def test_get_portfolio(self):
        await super().test_get_portfolio()

    async def test_untradable_symbols(self):
        await super().test_untradable_symbols()

    async def test_get_max_open_orders_count(self):
        await super().test_get_max_open_orders_count()

    async def test_get_account_id(self):
        pass

    async def test_is_authenticated_request(self):
        await super().test_is_authenticated_request()

    async def test_invalid_api_key_error(self):
        await super().test_invalid_api_key_error()

    async def test_get_api_key_permissions(self):
        pass

    async def test_missing_trading_api_key_permissions(self):
        pass

    async def test_api_key_ip_whitelist_error(self):
        pass

    async def test_get_not_found_order(self):
        await super().test_get_not_found_order()

    async def test_is_broker_enabled(self):
        await super().test_is_broker_enabled()

    async def test_get_special_orders(self):
        await super().test_get_special_orders()

    async def test_cancel_uncancellable_order(self):
        await super().test_cancel_uncancellable_order()

    async def test_create_and_cancel_limit_orders(self):
        await super().test_create_and_cancel_limit_orders()

    async def test_create_and_fill_market_orders(self):
        await super().test_create_and_fill_market_orders()

    async def test_get_my_recent_trades(self):
        await super().test_get_my_recent_trades()

    async def test_get_my_recent_trades_exhaust_history(self):
        await super().test_get_my_recent_trades_exhaust_history()

    async def test_get_deposits(self):
        await super().test_get_deposits()

    async def test_get_withdrawals(self):
        await super().test_get_withdrawals()

    async def test_get_closed_orders(self):
        await super().test_get_closed_orders()

    async def test_get_cancelled_orders(self):
        await super().test_get_cancelled_orders()

    async def test_create_and_cancel_stop_orders(self):
        pass

    async def test_edit_limit_order(self):
        pass

    async def test_edit_stop_order(self):
        pass

    async def test_create_single_bundled_orders(self):
        pass

    async def test_create_double_bundled_orders(self):
        pass
