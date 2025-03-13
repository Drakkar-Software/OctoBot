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

import octobot_trading.enums
from additional_tests.exchanges_tests import abstract_authenticated_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestCoinbaseAuthenticatedExchange(
    abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester
):
    # enter exchange name as a class variable here
    EXCHANGE_NAME = "coinbase"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDC"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}"
    ORDER_SIZE = 30  # % of portfolio to include in test orders
    CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = True
    VALID_ORDER_ID = "8bb80a81-27f7-4415-aa50-911ea46d841c"
    USE_ORDER_OPERATION_TO_CHECK_API_KEY_RIGHTS = True    # set True when api key rights can't be checked using a
    EXPECT_MISSING_FEE_IN_CANCELLED_ORDERS = False
    IS_BROKER_ENABLED_ACCOUNT = False
    IS_AUTHENTICATED_REQUEST_CHECK_AVAILABLE = True    # set True when is_authenticated_request is implemented

    SPECIAL_ORDER_TYPES_BY_EXCHANGE_ID: dict[
        str, (
            str, # symbol
            str, # order type key in 'info' dict
            str, # order type found in 'info' dict
            str, # parsed trading_enums.TradeOrderType
            str, # parsed trading_enums.TradeOrderSide
            bool, # trigger above (on higher price than order price)
        )
    ] = {
        '7e03c745-7340-49ef-8af1-b8f7fe431c8a': (
            "BTC/EUR", "order_type", "STOP_LIMIT",  # sell at a lower price
            octobot_trading.enums.TradeOrderType.STOP_LOSS.value, octobot_trading.enums.TradeOrderSide.SELL.value, False
        ),
        '1e2f0918-5728-4c68-b8f4-6fd804396248': (
            "ETH/BTC", "order_type", "STOP_LIMIT",  # buy at a higher price
            octobot_trading.enums.TradeOrderType.STOP_LOSS.value, octobot_trading.enums.TradeOrderSide.BUY.value, True
        ),
        'f4016e50-1f0b-4caa-abe5-1ec00af18be9': (
            "ETH/BTC", "order_type", "STOP_LIMIT",  # buy at a lower price
            octobot_trading.enums.TradeOrderType.LIMIT.value, octobot_trading.enums.TradeOrderSide.BUY.value, False
        ),
    }  # stop loss / take profit and other special order types to be successfully parsed
    # details of an order that exists but can"t be cancelled
    UNCANCELLABLE_ORDER_ID_SYMBOL_TYPE: tuple[str, str, octobot_trading.enums.TraderOrderType] = (
        "f4016e50-1f0b-4caa-abe5-1ec00af18be9", "ETH/BTC", octobot_trading.enums.TraderOrderType.BUY_LIMIT.value
    )

    async def test_get_portfolio(self):
        await super().test_get_portfolio()

    async def test_get_portfolio_with_market_filter(self):
        await super().test_get_portfolio_with_market_filter()

    async def test_untradable_symbols(self):
        await super().test_untradable_symbols()

    async def test_get_account_id(self):
        await super().test_get_account_id()

    async def test_is_authenticated_request(self):
        await super().test_is_authenticated_request()

    async def test_invalid_api_key_error(self):
        await super().test_invalid_api_key_error()

    async def test_get_api_key_permissions(self):
        await super().test_get_api_key_permissions()

    async def test_missing_trading_api_key_permissions(self):
        await super().test_missing_trading_api_key_permissions()

    async def test_api_key_ip_whitelist_error(self):
        await super().test_api_key_ip_whitelist_error()

    async def test_get_not_found_order(self):
        await super().test_get_not_found_order()

    async def test_is_valid_account(self):
        await super().test_is_valid_account()

    async def test_get_special_orders(self):
        await super().test_get_special_orders()

    async def test_create_and_cancel_limit_orders(self):
        await super().test_create_and_cancel_limit_orders()

    async def test_create_and_fill_market_orders(self):
        await super().test_create_and_fill_market_orders()

    async def test_get_my_recent_trades(self):
        await super().test_get_my_recent_trades()

    async def test_get_closed_orders(self):
        await super().test_get_closed_orders()

    async def test_get_cancelled_orders(self):
        await super().test_get_cancelled_orders()

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
