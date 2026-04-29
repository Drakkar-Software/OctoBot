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
import octobot_trading.enums

from additional_tests.exchanges_tests import abstract_authenticated_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestKucoinAuthenticatedExchange(
    abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester
):
    # WARNING: can't be tested since dec 2025 due to regulatory changes on EU countries
    # enter exchange name as a class variable here
    EXCHANGE_NAME = "kucoin"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDC"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}"
    ORDER_SIZE = 50  # % of portfolio to include in test orders
    EXPECT_MISSING_FEE_IN_CANCELLED_ORDERS = False  # when get_cancelled_orders returns None in fee
    EXPECTED_GENERATED_ACCOUNT_ID = False   # True when subaccounts are created
    USE_ORDER_OPERATION_TO_CHECK_API_KEY_RIGHTS = True
    VALID_ORDER_ID = "6617e84c5c1e0000083c71f7"
    IS_AUTHENTICATED_REQUEST_CHECK_AVAILABLE = True    # set True when is_authenticated_request is implemented
    CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = True
    SUPPORTS_GET_MAX_ORDERS_COUNT = True

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
        # can't be fetched anymore
        "vs93gpruc6ikekiv003o48ci": (
            "BTC/USDT", "type", "market",
            octobot_trading.enums.TradeOrderType.LIMIT.value, octobot_trading.enums.TradeOrderSide.BUY.value, False
        ),
        'vs93gpruc6n45taf003lr546': (
            "BTC/USDT", "type", "market",
            octobot_trading.enums.TradeOrderType.STOP_LOSS.value, octobot_trading.enums.TradeOrderSide.BUY.value, True
        ),
        'vs93gpruc69s00cs003tat0g': (
            "BTC/USDT", "type", "limit",
            octobot_trading.enums.TradeOrderType.LIMIT.value, octobot_trading.enums.TradeOrderSide.BUY.value, False
        ),
        'vs93gpruc5q45taf003lr545': (
            "BTC/USDT", "type", "limit",
            octobot_trading.enums.TradeOrderType.STOP_LOSS.value, octobot_trading.enums.TradeOrderSide.BUY.value, True
        ),
    }  # stop loss / take profit and other special order types to be successfully parsed
    # details of an order that exists but can"t be cancelled
    UNCANCELLABLE_ORDER_ID_SYMBOL_TYPE: tuple[str, str, octobot_trading.enums.TraderOrderType] = (
        "vs93gpruc69s00cs003tat0g", "BTC/USDT", octobot_trading.enums.TraderOrderType.BUY_LIMIT.value
    )

    async def test_get_portfolio(self):
        await super().test_get_portfolio()

    async def test_get_portfolio_with_market_filter(self):
        await super().test_get_portfolio_with_market_filter()

    async def test_untradable_symbols(self):
        await super().test_untradable_symbols()

    async def test_get_max_orders_count(self):
        await super().test_get_max_orders_count()

    async def test_is_valid_account(self):
        await super().test_is_valid_account()

    async def test_get_special_orders(self):
        await super().test_get_special_orders()

    async def test_create_and_cancel_limit_orders(self):
        await super().test_create_and_cancel_limit_orders()

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
        await super().test_edit_limit_order()

    async def test_edit_stop_order(self):
        await super().test_edit_stop_order()

    async def test_create_single_bundled_orders(self):
        # pass if not implemented
        pass

    async def test_create_double_bundled_orders(self):
        # pass if not implemented
        pass
