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
from additional_tests.exchanges_tests import abstract_authenticated_future_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestKucoinFuturesAuthenticatedExchange(
    abstract_authenticated_future_exchange_tester.AbstractAuthenticatedFutureExchangeTester
):
    # WARNING: can't be tested since dec 2025 due to regulatory changes on EU countries
    # enter exchange name as a class variable here
    EXCHANGE_NAME = "kucoin"
    CREDENTIALS_EXCHANGE_NAME = "KUCOIN_FUTURES"
    ORDER_CURRENCY = "DOT"  # always use a contract that has a size different from 1 unit of the currency
    SETTLEMENT_CURRENCY = "USDT"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}:{SETTLEMENT_CURRENCY}"
    INVERSE_SYMBOL = f"{ORDER_CURRENCY}/USD:{ORDER_CURRENCY}"
    ORDER_SIZE = 80  # % of portfolio to include in test orders
    SUPPORTS_GET_LEVERAGE = False
    USE_ORDER_OPERATION_TO_CHECK_API_KEY_RIGHTS = True
    VALID_ORDER_ID = "6617e84c5c1e0000083c71f7"
    EXPECT_MISSING_FEE_IN_CANCELLED_ORDERS = False
    IS_AUTHENTICATED_REQUEST_CHECK_AVAILABLE = True    # set True when is_authenticated_request is implemented
    EXPECTED_QUOTE_MIN_ORDER_SIZE = 4
    EXPECT_BALANCE_FILTER_BY_MARKET_STATUS = True
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
        "266424660906831872": (
            "ETH/USDT:USDT", "type", "market",
            octobot_trading.enums.TradeOrderType.LIMIT.value, octobot_trading.enums.TradeOrderSide.BUY.value, False
        ),
        '266424746172764160': (
            "ETH/USDT:USDT", "type", "market",
            octobot_trading.enums.TradeOrderType.STOP_LOSS.value, octobot_trading.enums.TradeOrderSide.SELL.value, False
        ),
        '266424798085668865': (
            "ETH/USDT:USDT", "type", "limit",
            octobot_trading.enums.TradeOrderType.LIMIT.value, octobot_trading.enums.TradeOrderSide.BUY.value, False
        ),
        '266424826044899328': (
            "ETH/USDT:USDT", "type", "limit",
            octobot_trading.enums.TradeOrderType.STOP_LOSS.value, octobot_trading.enums.TradeOrderSide.SELL.value, False
        ),
    }  # stop loss / take profit and other special order types to be successfully parsed
    # details of an order that exists but can"t be cancelled
    UNCANCELLABLE_ORDER_ID_SYMBOL_TYPE: tuple[str, str, octobot_trading.enums.TraderOrderType] = (
        "266424798085668865", "ETH/USDT:USDT", octobot_trading.enums.TraderOrderType.BUY_LIMIT.value
    )

    async def test_get_portfolio(self):
        await super().test_get_portfolio()

    async def test_get_portfolio_with_market_filter(self):
        await super().test_get_portfolio_with_market_filter()   # can have small variations failing the test when positions are open

    async def test_untradable_symbols(self):
        await super().test_untradable_symbols()

    async def test_get_max_orders_count(self):
        await super().test_get_max_orders_count()

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

    async def test_get_empty_linear_and_inverse_positions(self):
        await super().test_get_empty_linear_and_inverse_positions()

    async def test_get_and_set_margin_type(self):
        await super().test_get_and_set_margin_type()

    async def test_get_and_set_leverage(self):
        await super().test_get_and_set_leverage()

    async def test_is_valid_account(self):
        await super().test_is_valid_account()

    async def test_get_special_orders(self):
        await super().test_get_special_orders()

    async def test_create_and_cancel_limit_orders(self):
        # todo test cross position order creation (kucoin param) at next ccxt update (will support set margin type)
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
        # pass if not implemented
        await super().test_create_and_cancel_stop_orders()

    async def test_edit_limit_order(self):
        await super().test_edit_limit_order()

    async def test_edit_stop_order(self):
        await super().test_edit_stop_order()

    async def test_create_single_bundled_orders(self):
        # pass if not implemented
        # no exchange API to bind secondary orders when creating a new order
        pass

    async def test_create_double_bundled_orders(self):
        # pass if not implemented
        # no exchange API to bind secondary orders when creating a new order
        pass
