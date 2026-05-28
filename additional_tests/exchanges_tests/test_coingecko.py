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


class TestCoingeckoAuthenticatedExchange(
    abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester
):
    # enter exchange name as a class variable here
    EXCHANGE_NAME = "coingecko"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USD"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}"
    IS_READ_ONLY_EXCHANGE = True

    async def test_invalid_api_key_error(self):
        # invalid API keys can't be checked for now (coingecko accepts any key and returns 200)
        pass

    async def test_untradable_symbols(self):
        await super().test_untradable_symbols()

    async def test_get_portfolio(self):
        # ensure not supported for read only exchanges
        await super().test_get_portfolio()

    async def test_create_and_cancel_limit_orders(self):
        # ensure not supported for read only exchanges
        await super().test_create_and_cancel_limit_orders()

    async def test_create_and_fill_market_orders(self):
        # ensure not supported for read only exchanges
        await super().test_create_and_fill_market_orders()

    async def test_get_my_recent_trades(self):
        # ensure not supported for read only exchanges
        await super().test_get_my_recent_trades()

    async def test_get_closed_orders(self):
        # ensure not supported for read only exchanges
        await super().test_get_closed_orders()

    async def test_get_cancelled_orders(self):
        # ensure not supported for read only exchanges
        await super().test_get_cancelled_orders()

    async def test_get_max_open_orders_count(self):
        # irrelevant for coingecko
        pass

    async def test_get_account_id(self):
        # irrelevant for coingecko
        pass

    async def test_is_authenticated_request(self):
        # irrelevant for coingecko
        pass

    async def test_get_api_key_permissions(self):
        # irrelevant for coingecko
        pass

    async def test_missing_trading_api_key_permissions(self):
        # irrelevant for coingecko
        pass

    async def test_api_key_ip_whitelist_error(self):
        # irrelevant for coingecko
        pass

    async def test_get_not_found_order(self):
        # irrelevant for coingecko
        pass

    async def test_is_broker_enabled(self):
        # irrelevant for coingecko
        pass

    async def test_get_special_orders(self):
        # irrelevant for coingecko
        pass

    async def test_cancel_uncancellable_order(self):
        # irrelevant for coingecko
        pass

    async def test_create_and_cancel_stop_orders(self):
        # irrelevant for coingecko
        pass

    async def test_edit_limit_order(self):
        # irrelevant for coingecko
        pass

    async def test_edit_stop_order(self):
        # irrelevant for coingecko
        pass

    async def test_create_single_bundled_orders(self):
        # irrelevant for coingecko
        pass

    async def test_create_double_bundled_orders(self):
        # irrelevant for coingecko
        pass
