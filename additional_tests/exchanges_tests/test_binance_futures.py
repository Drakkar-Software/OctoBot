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
import decimal

import octobot_trading.enums
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
    ORDER_CURRENCY = "BTC"  # always use a contract that has a size different from 1 unit of the currency
    SETTLEMENT_CURRENCY = "USDT"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}:{SETTLEMENT_CURRENCY}"
    INVERSE_SYMBOL = f"{ORDER_CURRENCY}/USD:{ORDER_CURRENCY}"
    ORDER_SIZE = 5  # % of portfolio to include in test orders
    DUPLICATE_TRADES_RATIO = 0.1   # allow 10% duplicate in trades (due to trade id set to order id)
    VALID_ORDER_ID = "26408108410"
    EXPECTED_QUOTE_MIN_ORDER_SIZE = 200   # min quote value of orders to create (used to check market status parsing)
    IS_AUTHENTICATED_REQUEST_CHECK_AVAILABLE = True    # set True when is_authenticated_request is implemented
    MAX_TRADE_USD_VALUE = decimal.Decimal(450000)   # testnet portfolio
    ALLOW_0_MAKER_FEES = True

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
        "4075521283": (
            "BTC/USDT:USDT", "type", "TAKE_PROFIT_MARKET",
            octobot_trading.enums.TradeOrderType.LIMIT.value, octobot_trading.enums.TradeOrderSide.SELL.value, True
        ),
        '622529': (
            "BTC/USDC:USDC", "type", "STOP_MARKET",
            octobot_trading.enums.TradeOrderType.STOP_LOSS.value, octobot_trading.enums.TradeOrderSide.SELL.value, False
        ),
        '4076521927': (
            "BTC/USDT:USDT", "type", "TAKE_PROFIT",
            octobot_trading.enums.TradeOrderType.LIMIT.value, octobot_trading.enums.TradeOrderSide.BUY.value, False
        ),
        '4076521976': (
            "BTC/USDT:USDT", "type", "STOP",
            octobot_trading.enums.TradeOrderType.STOP_LOSS.value, octobot_trading.enums.TradeOrderSide.SELL.value, False
        ),
    }  # stop loss / take profit and other special order types to be successfully parsed
    # details of an order that exists but can"t be cancelled
    UNCANCELLABLE_ORDER_ID_SYMBOL_TYPE: tuple[str, str, octobot_trading.enums.TraderOrderType] = (
        "4076521927", "BTC/USDT:USDT", octobot_trading.enums.TraderOrderType.BUY_LIMIT.value
    )

    async def _set_account_types(self, account_types):
        # todo remove this and use both types when exchange-side multi portfolio is enabled
        self.exchange_manager.exchange._futures_account_types = account_types

    async def test_get_portfolio(self):
        await super().test_get_portfolio()

    async def test_get_portfolio_with_market_filter(self):
        await super().test_get_portfolio_with_market_filter()   # can have small variations failing the test when positions are open

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
        pass

    async def test_api_key_ip_whitelist_error(self):
        await super().test_api_key_ip_whitelist_error()

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

    async def test_is_valid_account(self):
        await super().test_is_valid_account()

    async def test_get_special_orders(self):
        await super().test_get_special_orders()

    async def test_create_and_cancel_limit_orders(self):
        await super().test_create_and_cancel_limit_orders()

    async def _inner_test_create_and_cancel_limit_orders_for_margin_type(
        self, symbol=None, settlement_currency=None, margin_type=None
    ):
        # todo remove this and use both types when exchange-side multi portfolio is enabled
        # test with linear symbol
        await self._set_account_types(
            [self.exchange_manager.exchange.LINEAR_TYPE]
        )
        await abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester\
            .inner_test_create_and_cancel_limit_orders(self, margin_type=margin_type)
        # test with inverse symbol
        await self._set_account_types(
            [self.exchange_manager.exchange.INVERSE_TYPE]
        )
        await abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester\
            .inner_test_create_and_cancel_limit_orders(
                self, symbol=self.INVERSE_SYMBOL, settlement_currency=self.ORDER_CURRENCY, margin_type=margin_type
            )

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
