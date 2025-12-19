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

try:
    import tentacles.Trading.Exchange.polymarket.ccxt.polymarket_async
except ImportError:
    pytest.skip(
        reason=(
            "Polymarket tentacle is not installed, skipping TestPolymarketAuthenticatedExchange"
        )
    )

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestPolymarketAuthenticatedExchange(
    abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester
):
    # enter exchange name as a class variable here
    EXCHANGE_NAME = "polymarket"
    ORDER_CURRENCY = "will-bitcoin-replace-sha-256-before-2027"
    SETTLEMENT_CURRENCY = "USDC"
    EXPIRATION_DATE = "261231"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}:{SETTLEMENT_CURRENCY}-{EXPIRATION_DATE}"
    ORDER_SIZE = 10  # % of portfolio to include in test orders
    EXPECT_MISSING_FEE_IN_CANCELLED_ORDERS = False
    CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = True
    CONVERTS_ORDER_PRICE_BEFORE_PUSHING_TO_EXCHANGE = True
    ORDER_IMPACTS_PORTFOLIO_FREE_BALANCE = False

    async def test_get_portfolio(self):
        await super().test_get_portfolio()

    async def test_get_portfolio_with_market_filter(self):
        # pass if not implemented
        pass

    async def test_untradable_symbols(self):
        # pass if not implemented
        pass

    async def test_get_max_orders_count(self):
        # pass if not implemented
        pass

    async def test_get_account_id(self):
        # pass if not implemented
        pass

    async def test_is_authenticated_request(self):
        await super().test_is_authenticated_request()

    async def test_invalid_api_key_error(self):
        await super().test_invalid_api_key_error()

    async def test_get_api_key_permissions(self):
        # pass if not implemented
        pass

    async def test_missing_trading_api_key_permissions(self):
        pass

    async def test_api_key_ip_whitelist_error(self):
        # pass if not implemented
        pass

    async def test_get_not_found_order(self):
        await super().test_get_not_found_order()

    async def test_is_valid_account(self):
        # pass if not implemented
        pass

    async def test_get_special_orders(self):
        # pass if not implemented
        pass

    async def test_create_and_cancel_limit_orders(self):
        await super().test_create_and_cancel_limit_orders()

    async def test_create_and_fill_market_orders(self):
        await super().test_create_and_fill_market_orders()

    async def test_get_my_recent_trades(self):
        await super().test_get_my_recent_trades()

    async def test_get_closed_orders(self):
        # pass if not implemented
        pass

    async def test_get_cancelled_orders(self):
        # pass if not implemented
        pass

    async def test_create_and_cancel_stop_orders(self):
        # pass if not implemented
        pass

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
