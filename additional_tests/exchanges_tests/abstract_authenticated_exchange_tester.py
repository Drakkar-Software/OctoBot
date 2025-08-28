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
import asyncio
import contextlib
import decimal
import random
import time
import typing
import ccxt
import mock
import pytest

import octobot_commons.constants as constants
import octobot_commons.enums as commons_enums
import octobot_commons.symbols as symbols
import octobot_commons.configuration as commons_configuration
import octobot_trading.errors as trading_errors
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.personal_data as personal_data
import octobot_trading.personal_data.orders as personal_data_orders
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools
import octobot_trading.util.test_tools.exchange_data as exchange_data_import
import trading_backend.enums
import octobot_tentacles_manager.api as tentacles_manager_api
from additional_tests.exchanges_tests import get_authenticated_exchange_manager, NoProvidedCredentialsError

# always import and load tentacles
import tentacles
tentacles_manager_api.reload_tentacle_info()


class AbstractAuthenticatedExchangeTester:
    # enter exchange name as a class variable here
    EXCHANGE_NAME = None
    CREDENTIALS_EXCHANGE_NAME = None
    EXCHANGE_TENTACLE_NAME = None
    EXCHANGE_TYPE = trading_enums.ExchangeTypes.SPOT.value
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}"
    TIME_FRAME = "1h"
    VALID_ORDER_ID = "8bb80a81-27f7-4415-aa50-911ea46d841c"
    ALLOW_0_MAKER_FEES = False
    SPECIAL_ORDER_TYPES_BY_EXCHANGE_ID: dict[
        str, (
            str, # symbol
            str, # order type key in 'info' dict
            str, # order type found in 'info' dict
            str, # parsed trading_enums.TradeOrderType
            str, # parsed trading_enums.TradeOrderSide
            bool, # trigger above (on higher price than order price)
        )
    ] = {}  # stop loss / take profit and other special order types to be successfully parsed
    # details of an order that exists but can"t be cancelled
    UNCANCELLABLE_ORDER_ID_SYMBOL_TYPE: tuple[str, str, trading_enums.TraderOrderType] = None
    ORDER_SIZE = 10  # % of portfolio to include in test orders
    PORTFOLIO_TYPE_FOR_SIZE = trading_constants.CONFIG_PORTFOLIO_FREE
    CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = False
    ORDER_PRICE_DIFF = 20  # % of price difference compared to current price for limit and stop orders
    EXPECT_MISSING_ORDER_FEES_DUE_TO_ORDERS_TOO_OLD_FOR_RECENT_TRADES = False   # when recent trades are limited and
    # closed orders fees are taken from recent trades
    EXPECT_MISSING_FEE_IN_CANCELLED_ORDERS = True  # when get_cancelled_orders returns None in fee
    EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION = False
    CONVERTS_MARKET_INTO_LIMIT_ORDERS = False   # when market orders are always converted into limit order by the exchange
    OPEN_ORDERS_IN_CLOSED_ORDERS = False
    CANCELLED_ORDERS_IN_CLOSED_ORDERS = False
    EXPECT_FETCH_ORDER_TO_BE_AVAILABLE = True
    RECENT_TRADES_UPDATE_TIMEOUT = 15
    MARKET_FILL_TIMEOUT = 15
    OPEN_TIMEOUT = 15
    # if >0: retry fetching open/cancelled orders when created/cancelled orders are not synchronised instantly
    ORDER_IN_OPEN_AND_CANCELLED_ORDERS_TIMEOUT = 10
    CANCEL_TIMEOUT = 15
    EDIT_TIMEOUT = 15
    MIN_PORTFOLIO_SIZE = 1
    EXPECTED_QUOTE_MIN_ORDER_SIZE = 1   # min quote value of orders to create (used to check market status parsing)
    EXPECT_BALANCE_FILTER_BY_MARKET_STATUS = False  # set true when using filtered market status also filters
    # fetched balance assets
    DUPLICATE_TRADES_RATIO = 0
    SUPPORTS_DOUBLE_BUNDLED_ORDERS = True
    # set true when cancelling any bundled order on exchange would automatically cancel the other(s)
    CANCEL_DOUBLE_BUNDLED_ORDERS_TOGETHER = True
    IGNORE_EXCHANGE_TRADE_ID = False    # set True when trade.exchange_trade_id can't be set
    MAX_TRADE_USD_VALUE = decimal.Decimal(8000)
    MIN_TRADE_USD_VALUE = decimal.Decimal("0.1")
    IS_ACCOUNT_ID_AVAILABLE = True  # set False when get_account_id is not available and should be checked
    IS_AUTHENTICATED_REQUEST_CHECK_AVAILABLE = False    # set True when is_authenticated_request is implemented
    EXPECTED_GENERATED_ACCOUNT_ID = False   # set True when account_id can't be fetch and a generated account id is used
    USE_ORDER_OPERATION_TO_CHECK_API_KEY_RIGHTS = False    # set True when api key rights can't be checked using a
    # dedicated api and have to be checked by sending an order operation
    EXPECTED_INVALID_ORDERS_QUANTITY = []   # orders with known invalid quantity exchange order id    (usually legacy)
    CHECK_EMPTY_ACCOUNT = False  # set True when the account to check has no funds. Warning: does not check order
    # parse/create/fill/cancel or portfolio & trades parsing
    IS_BROKER_ENABLED_ACCOUNT = True # set False when this test account can't generate broker fees
    # set True when this exchange used to have symbols that can't be traded through API (ex: MEXC)
    USED_TO_HAVE_UNTRADABLE_SYMBOL = False
    SUPPORTS_GET_MAX_ORDERS_COUNT = False   # when True, will ensure that default values are not used
    DEFAULT_MAX_DEFAULT_ORDERS_COUNT = trading_constants.DEFAULT_MAX_DEFAULT_ORDERS_COUNT
    DEFAULT_MAX_STOP_ORDERS_COUNT = trading_constants.DEFAULT_MAX_STOP_ORDERS_COUNT

    # Implement all "test_[name]" methods, call super() to run the test, pass to ignore it.
    # Override the "inner_test_[name]" method to override a test content.
    # Add method call to subclasses to be able to run them independently

    async def test_get_portfolio(self):
        # encoded_a = _get_encoded_value("") # tool to get encoded values
        # encoded_b = _get_encoded_value("")
        # encoded_c = _get_encoded_value("")
        async with self.local_exchange_manager():
            await self.inner_test_get_portfolio()

    async def test_get_portfolio_with_market_filter(self):
        # ensure market status are already loaded by another exchange manage and filters are applied
        async with self.local_exchange_manager():
            # get portfolio with all markets
            all_markets_portfolio = await self.get_portfolio()

        # now that market status are cached, test with filters
        async with self.local_exchange_manager(market_filter=self._get_market_filter()):
            # check portfolio fetched with filtered markets (should be equal to the one with all markets)
            filtered_markets_portfolio = await self.get_portfolio()
            if self.EXPECT_BALANCE_FILTER_BY_MARKET_STATUS:
                filtered = {
                    key: val
                    for key, val in all_markets_portfolio.items()
                    if key in symbols.parse_symbol(self.SYMBOL).base_and_quote()
                }
                assert filtered_markets_portfolio == filtered, f"{filtered_markets_portfolio=} != {filtered=}"
            else:
                assert filtered_markets_portfolio == all_markets_portfolio, f"{filtered_markets_portfolio=} != {all_markets_portfolio=}"

    async def inner_test_get_portfolio(self):
        self.check_portfolio_content(await self.get_portfolio())

    def check_portfolio_content(self, portfolio):
        if self.CHECK_EMPTY_ACCOUNT:
            assert portfolio == {}
            return
        assert len(portfolio) >= self.MIN_PORTFOLIO_SIZE
        at_least_one_value = False
        for asset, values in portfolio.items():
            assert all(
                key in values
                for key in (
                    trading_constants.CONFIG_PORTFOLIO_FREE,
                    trading_constants.CONFIG_PORTFOLIO_USED,
                    trading_constants.CONFIG_PORTFOLIO_TOTAL
                )
            )
            if values[trading_constants.CONFIG_PORTFOLIO_TOTAL] > trading_constants.ZERO:
                at_least_one_value = True
        assert at_least_one_value
        # ensure no duplicate
        assert len(set(portfolio)) == len(portfolio)

    async def test_untradable_symbols(self):
        await self.inner_test_untradable_symbols()

    async def inner_test_untradable_symbols(self):
        if not self.USED_TO_HAVE_UNTRADABLE_SYMBOL:
            # nothing to do
            return
        async with self.local_exchange_manager():
            all_symbols = self.exchange_manager.exchange.get_all_available_symbols()
            all_symbols_including_disabled = self.exchange_manager.exchange.get_all_available_symbols(active_only=False)
            disabled = [
                symbol
                for symbol in all_symbols_including_disabled
                if symbol not in all_symbols
            ]
            tradable_symbols = await self.exchange_manager.exchange.get_all_tradable_symbols()
            assert len(all_symbols) > len(tradable_symbols)
            untradable_symbols = [
                symbol
                for symbol in all_symbols
                if symbol not in tradable_symbols
                and symbol.endswith(f"/{self.SETTLEMENT_CURRENCY}")
                and (
                   symbols.parse_symbol(symbol).is_spot()
                   if self.EXCHANGE_TYPE == trading_enums.ExchangeTypes.SPOT.value
                   else symbols.parse_symbol(symbol).is_future()
               )
            ]
            tradable_symbols = [
                symbol
                for symbol in all_symbols
                if symbol in tradable_symbols
                and symbol.endswith(f"/{self.SETTLEMENT_CURRENCY}")
                and (
                   symbols.parse_symbol(symbol).is_spot()
                   if self.EXCHANGE_TYPE == trading_enums.ExchangeTypes.SPOT.value
                   else symbols.parse_symbol(symbol).is_future()
               )
            ]
            # has untradable symbols of this trading type
            assert len(untradable_symbols) > 0
            untradable = [untradable_symbols[0]]
            if disabled:
                print(f"Including {disabled[0]} disabled coin (from {len(disabled)} coins)")
                untradable.append(disabled[0])
            for untradable_symbol in untradable:
                # Public data
                # market status is available
                assert ccxt_constants.CCXT_INFO in self.exchange_manager.exchange.get_market_status(untradable_symbol)
                # fetching ohlcv is ok
                assert len(
                    await self.exchange_manager.exchange.get_symbol_prices(
                        untradable_symbol, commons_enums.TimeFrames(self.TIME_FRAME)
                    )
                ) > 5
                # fetching kline is ok
                kline = await self.exchange_manager.exchange.get_kline_price(
                    untradable_symbol, commons_enums.TimeFrames(self.TIME_FRAME)
                )
                assert len(kline) == 1
                assert len(kline[0]) == 6
                # fetching ticker is ok
                ticker = await self.exchange_manager.exchange.get_price_ticker(untradable_symbol)
                assert ticker
                price = ticker[trading_enums.ExchangeConstantsTickersColumns.CLOSE.value]
                assert price > 0
                # fetching recent trades is ok
                recent_trades = await self.exchange_manager.exchange.get_recent_trades(untradable_symbol)
                assert len(recent_trades) > 1
                # fetching order book is ok
                order_book = await self.exchange_manager.exchange.get_order_book(untradable_symbol)
                assert len(order_book[trading_enums.ExchangeConstantsOrderBookInfoColumns.ASKS.value]) > 0
                # is in all tickers
                all_tickers = await self.exchange_manager.exchange.get_all_currencies_price_ticker()
                assert all_tickers[untradable_symbol][trading_enums.ExchangeConstantsTickersColumns.CLOSE.value] > 0
                # Orders
                # try creating & cancelling orders on 5 random tradable and untradable symbols
                symbols_to_test = 5
                tradable_stepper = random.randint(1, len(tradable_symbols) - 2)
                tradable_indexes = [tradable_stepper * i for i in range(0, symbols_to_test)]
                untradable_stepper = random.randint(1, len(untradable_symbols) - 2)
                untradable_indexes = [untradable_stepper * i for i in range(0, symbols_to_test)]
                to_test_symbols = [
                    tradable_symbols[i % (len(tradable_symbols) - 1)] for i in tradable_indexes
                ] + [
                    untradable_symbols[i % (len(untradable_symbols) - 1)] for i in untradable_indexes
                ]
            for i, symbol in enumerate(to_test_symbols):
                ticker = await self.exchange_manager.exchange.get_price_ticker(symbol)
                price = ticker[trading_enums.ExchangeConstantsTickersColumns.CLOSE.value]
                price = self.get_order_price(decimal.Decimal(str(price)), False, symbol=symbol)
                size = self.get_order_size(
                    await self.get_portfolio(), price, symbol=symbol,
                    settlement_currency=self.SETTLEMENT_CURRENCY
                )
                buy_limit = await self.create_limit_order(
                    price, size, trading_enums.TradeOrderSide.BUY,
                    symbol=symbol
                )
                await self.cancel_order(buy_limit)
                print(f"{i+1}/{len(to_test_symbols)} : {symbol} Create & cancel order OK")

    async def test_get_max_orders_count(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_max_orders_count()

    async def inner_test_get_max_orders_count(self):
        self._test_symbol_max_orders_count(self.SYMBOL)

    def _test_symbol_max_orders_count(self, symbol):
        max_base_order_count = self.exchange_manager.exchange.get_max_orders_count(
            symbol, trading_enums.TraderOrderType.BUY_LIMIT
        )
        max_stop_order_count = self.exchange_manager.exchange.get_max_orders_count(
            symbol, trading_enums.TraderOrderType.STOP_LOSS
        )
        if self.SUPPORTS_GET_MAX_ORDERS_COUNT:
            assert (
                max_base_order_count != self.DEFAULT_MAX_DEFAULT_ORDERS_COUNT
                or max_stop_order_count != self.DEFAULT_MAX_STOP_ORDERS_COUNT
            )
        else:
            assert max_base_order_count == self.DEFAULT_MAX_DEFAULT_ORDERS_COUNT
            assert max_stop_order_count == self.DEFAULT_MAX_STOP_ORDERS_COUNT

    async def test_get_account_id(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_account_id()

    async def inner_test_get_account_id(self):
        if self.IS_ACCOUNT_ID_AVAILABLE:
            account_id = await self.exchange_manager.exchange.get_account_id()
            assert account_id
            assert isinstance(account_id, str)
            if self.EXPECTED_GENERATED_ACCOUNT_ID:
                assert account_id in (trading_constants.DEFAULT_ACCOUNT_ID, trading_constants.DEFAULT_SUBACCOUNT_ID)
            else:
                assert account_id not in (trading_constants.DEFAULT_ACCOUNT_ID, trading_constants.DEFAULT_SUBACCOUNT_ID)
        else:
            with pytest.raises(NotImplementedError):
                await self.exchange_manager.exchange.get_account_id()

    async def test_is_authenticated_request(self):
        rest_exchange_data = {
            "calls": [],
        }
        def _http_proxy_callback_factory(_exchange_manager):
            rest_exchange_data["exchange_manager"] = _exchange_manager
            def proxy_callback(url: str, method: str, headers: dict, body) -> typing.Optional[str]:
                if not self.IS_AUTHENTICATED_REQUEST_CHECK_AVAILABLE:
                    return None
                if "rest_exchange" not in rest_exchange_data:
                    rest_exchange_data["rest_exchange"] = rest_exchange_data["exchange_manager"].exchange
                rest_exchange = rest_exchange_data["rest_exchange"]
                exchange_return_value = rest_exchange.is_authenticated_request(url, method, headers, body)
                rest_exchange_data["calls"].append(
                    ((url, method, headers, body), exchange_return_value)
                )
                # never return any proxy url: no proxy is set but make sure to register each request call
                return None

            return proxy_callback

        async with self.local_exchange_manager(http_proxy_callback_factory=_http_proxy_callback_factory):
            await self.inner_is_authenticated_request(rest_exchange_data)

    async def inner_is_authenticated_request(self, rest_exchange_data):
        if self.IS_AUTHENTICATED_REQUEST_CHECK_AVAILABLE:
            latest_call_indexes = [len(rest_exchange_data["calls"])]
            def get_latest_calls():
                latest_calls = rest_exchange_data["calls"][latest_call_indexes[-1]:]
                latest_call_indexes.append(len(rest_exchange_data["calls"]))
                return latest_calls

            def assert_has_at_least_one_authenticated_call(calls):
                has_authenticated_call = False
                for latest_call in calls:
                    # should be at least 1 authenticated call
                    if latest_call[1] is True:
                        has_authenticated_call = True
                assert has_authenticated_call, f"{calls} should contain at last 1 authenticated call"  # authenticated request

            # 1. test using different values
            assert self.exchange_manager.exchange.is_authenticated_request("", "", {}, None) is False
            assert self.exchange_manager.exchange.is_authenticated_request("", "", {}, "") is False
            assert self.exchange_manager.exchange.is_authenticated_request("", "", {}, b"") is False
            assert self.exchange_manager.exchange.is_authenticated_request(None, None, None, b"") is False

            # 2. make public requests
            assert await self.exchange_manager.exchange.get_symbol_prices(
                self.SYMBOL, commons_enums.TimeFrames.ONE_HOUR
            )
            latest_calls = get_latest_calls()
            for latest_call in latest_calls:
                assert latest_call[1] is False, f"{latest_call} should be NOT authenticated"  # authenticated request
            ticker = await self.exchange_manager.exchange.get_price_ticker(self.SYMBOL)
            assert ticker
            last_price = ticker[trading_enums.ExchangeConstantsTickersColumns.CLOSE.value]
            assert rest_exchange_data["calls"][-1][0][0] != latest_calls[-1][0][0]  # assert latest call's url changed
            latest_calls = get_latest_calls()
            for latest_call in latest_calls:
                assert latest_call[1] is False, f"{latest_call} should be NOT authenticated"  # authenticated request

            # 3. make private requests
            # balance (usually a GET)
            portfolio = await self.get_portfolio()
            if self.CHECK_EMPTY_ACCOUNT:
                assert portfolio == {}
            else:
                assert portfolio
            assert rest_exchange_data["calls"][-1][0][0] != latest_calls[-1][0][0]   # assert latest call's url changed
            latest_calls = get_latest_calls()
            assert_has_at_least_one_authenticated_call(latest_calls)
            # create order (usually a POST)
            price = decimal.Decimal(str(last_price)) * decimal.Decimal("0.7")
            amount = self.get_order_size(
                portfolio, price, symbol=self.SYMBOL, settlement_currency=self.SETTLEMENT_CURRENCY
            ) * 100000
            if amount == 0:
                amount = 100000
            if self.CHECK_EMPTY_ACCOUNT:
                amount = 10
            # (amount is too large, creating buy order will fail)
            with pytest.raises(ccxt.ExchangeError):
                await self.exchange_manager.exchange.connector.create_limit_buy_order(
                    self.SYMBOL, amount, price=price, params={}
                )
            assert rest_exchange_data["calls"][-1][0][0] != latest_calls[-1][0][0]   # assert latest call's url changed
            latest_calls = get_latest_calls()
            assert_has_at_least_one_authenticated_call(latest_calls)
            # cancel order (usually a DELETE)
            with pytest.raises(ccxt.BaseError):
                # use client call directly to avoid any octobot error conversion
                await self.exchange_manager.exchange.connector.client.cancel_order(self.VALID_ORDER_ID, self.SYMBOL)
            assert rest_exchange_data["calls"][-1][0][0] != latest_calls[-1][0][0]   # assert latest call's url changed
            latest_calls = get_latest_calls()
            assert_has_at_least_one_authenticated_call(latest_calls)
        else:
            with pytest.raises(NotImplementedError):
                self.exchange_manager.exchange.is_authenticated_request("", "", {}, None)
            await asyncio.sleep(1.5)  # let initial requests finish to be able to stop exchange manager

    async def test_invalid_api_key_error(self):
        with pytest.raises(trading_errors.AuthenticationError):
            created_exchange = mock.Mock()
            async with self.local_exchange_manager(use_invalid_creds=True):
                created_exchange()
                # should fail
                portfolio = await self.get_portfolio()
                raise AssertionError(f"Did not raise on invalid api keys, fetched portfolio: {portfolio}")
            # ensure self.local_exchange_manager did not raise
            created_exchange.assert_called_once()

    async def test_get_api_key_permissions(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_api_key_permissions()

    async def inner_test_get_api_key_permissions(self):
        origin_get_api_key_rights_using_order = self.exchange_manager.exchange_backend._get_api_key_rights_using_order
        with mock.patch.object(
            self.exchange_manager.exchange_backend,
            "_get_api_key_rights_using_order", mock.AsyncMock(side_effect=origin_get_api_key_rights_using_order)
        ) as _get_api_key_rights_using_order_mock:
            permissions = await self.exchange_manager.exchange_backend._get_api_key_rights()
            self._ensure_required_permissions(permissions)
            if self.USE_ORDER_OPERATION_TO_CHECK_API_KEY_RIGHTS:
                # failed ? did not use _get_api_key_rights_using_order while expected
                _get_api_key_rights_using_order_mock.assert_called_once()
            else:
                # failed ? used _get_api_key_rights_using_order when not expected
                _get_api_key_rights_using_order_mock.assert_not_called()

    def _ensure_required_permissions(self, permissions):
        assert len(permissions) > 0
        assert trading_backend.enums.APIKeyRights.READING in permissions
        assert trading_backend.enums.APIKeyRights.SPOT_TRADING in permissions

    async def test_missing_trading_api_key_permissions(self):
        async with self.local_exchange_manager(identifiers_suffix="_READONLY"):
            await self.inner_test_missing_trading_api_key_permissions()

    async def inner_test_missing_trading_api_key_permissions(self):
        permissions = await self.exchange_manager.exchange_backend._get_api_key_rights()
        # ensure reading permission only are returned
        assert permissions == [trading_backend.enums.APIKeyRights.READING]
        # ensure order operations returns a permission error
        with pytest.raises(trading_errors.AuthenticationError) as err:
            await self.inner_test_create_and_cancel_limit_orders(use_both_margin_types=False)
        # ensure AuthenticationError is raised when creating order
        assert "inner_test_create_and_cancel_limit_orders#create_limit_order" in str(err), (
            f"Expected 'inner_test_create_and_cancel_limit_orders#create_limit_order' in error message, got: {err}"
        )

    async def test_api_key_ip_whitelist_error(self):
        if not self._supports_ip_whitelist_error():
            return
        try:
            with pytest.raises(trading_errors.InvalidAPIKeyIPWhitelistError):
                created_exchange = mock.Mock()
                async with self.local_exchange_manager(identifiers_suffix="_INVALID_IP_WHITELIST"):
                    created_exchange()
                    # should fail
                    portfolio = await self.get_portfolio()
                    raise AssertionError(f"Did not raise on invalid IP whitelist error, fetched portfolio: {portfolio}")
                # ensure self.local_exchange_manager did not raise
                created_exchange.assert_called_once()
        except NoProvidedCredentialsError as err:
            pytest.skip(f"Skipped test_api_key_ip_whitelist_error test: {err}")

    async def test_get_not_found_order(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_not_found_order()

    async def inner_test_get_not_found_order(self):
        # Ensures that get_order() returns None when an order is not found, should not raise an error
        non_existing_order = await self.exchange_manager.exchange.get_order(self.VALID_ORDER_ID, self.SYMBOL)
        assert non_existing_order is None

    async def test_is_valid_account(self):
        async with self.local_exchange_manager():
            await self.inner_test_is_valid_account()

    async def inner_test_is_valid_account(self):
        is_compatible, error = await self.exchange_manager.exchange_backend.is_valid_account(
            always_check_key_rights=True
        )
        assert is_compatible is self.IS_BROKER_ENABLED_ACCOUNT
        if is_compatible:
            assert error is None
        else:
            assert isinstance(error, str)
            assert len(error) > 0


    async def test_get_special_orders(self):
        if self.SPECIAL_ORDER_TYPES_BY_EXCHANGE_ID:
            async with self.local_exchange_manager():
                await self.inner_test_get_special_orders()

    async def inner_test_get_special_orders(self):
        # open_orders = await self.get_open_orders(_symbols=["TAO/USDT"])
        # print(open_orders)  # to print special orders when they are open
        # return
        for exchange_id, order_details in self.SPECIAL_ORDER_TYPES_BY_EXCHANGE_ID.items():
            symbol, info_key, info_type, expected_type, expected_side, expected_trigger_above = order_details
            print(order_details)
            fetched_order = await self.exchange_manager.exchange.get_order(exchange_id, symbol=symbol)
            assert fetched_order is not None
            self._check_fetched_order_dicts([fetched_order])
            # ensure parsing order doesn't crash
            parsed = personal_data.create_order_instance_from_raw(self.exchange_manager.trader, fetched_order)
            assert isinstance(parsed, personal_data.Order)

            assert fetched_order[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value] == symbol
            found_type = fetched_order[ccxt_constants.CCXT_INFO][info_key]
            assert found_type == info_type, f"[{exchange_id}]: {found_type} != {info_type}"
            parsed_type = fetched_order[trading_enums.ExchangeConstantsOrderColumns.TYPE.value]
            assert parsed_type == expected_type, f"[{exchange_id}]: {parsed_type} != {expected_type}"
            assert fetched_order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == expected_side
            if expected_trigger_above is None:
                assert trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value not in fetched_order
            else:
                parsed_trigger_above = fetched_order[trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value]
                assert parsed_trigger_above == expected_trigger_above, (
                    f"[{exchange_id}]: {parsed_trigger_above} != {expected_trigger_above}"
                )
                if isinstance(parsed, personal_data.LimitOrder):
                    assert parsed.trigger_above == parsed_trigger_above
            if expected_type == trading_enums.TradeOrderType.LIMIT.value:
                assert fetched_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] > 0
            elif expected_type == trading_enums.TradeOrderType.STOP_LOSS.value:
                assert fetched_order[trading_enums.ExchangeConstantsOrderColumns.STOP_PRICE.value] > 0
            elif expected_type == trading_enums.TradeOrderType.UNSUPPORTED.value:
                assert isinstance(parsed, personal_data.UnsupportedOrder)
            else:
                # ensure all cases are covered, otherwise there is a problem in order type parsing
                assert expected_type == trading_enums.TradeOrderType.MARKET

    async def test_create_and_cancel_limit_orders(self):
        async with self.local_exchange_manager():
            await self.inner_test_cancel_uncancellable_order()
            await self.inner_test_create_and_cancel_limit_orders()

    async def inner_test_create_and_cancel_limit_orders(self, symbol=None, settlement_currency=None, **kwargs):
        symbol = symbol or self.SYMBOL
        # # DEBUG tools p1, uncomment to create specific orders
        # symbol = "ADA/USDT"
        # # end debug tools
        market_status = self.exchange_manager.exchange.get_market_status(symbol)
        exchange_data = self.get_exchange_data(symbol=symbol)
        settlement_currency = settlement_currency or self.SETTLEMENT_CURRENCY
        price = self.get_order_price(await self.get_price(symbol=symbol), False, symbol=symbol)
        # 1. try with "normal" order size
        default_size = self.get_order_size(
            await self.get_portfolio(), price, symbol=symbol, settlement_currency=settlement_currency
        )
        # self.check_order_size_and_price(default_size, price, symbol=symbol, allow_empty_size=self.CHECK_EMPTY_ACCOUNT)
        enable_min_size_check = False
        enable_min_size_check = True  # FOR TESTS: comment to disable
        if enable_min_size_check:
            # 2. try with minimal order size
            min_size = personal_data.decimal_adapt_quantity(
                market_status,
                # add 25% to min order size to avoid rounding of amount of price ending up just bellow min cost
                decimal.Decimal(str(self.EXPECTED_QUOTE_MIN_ORDER_SIZE)) * (
                    decimal.Decimal("1.25") if symbols.parse_symbol(symbol).is_spot() else decimal.Decimal("1")
                ) / (
                    decimal.Decimal("1") if symbols.parse_symbol(symbol).is_inverse() else price
                )
            )
            # self.check_order_size_and_price(min_size, price, symbol=symbol, allow_empty_size=False)
            size = max(min_size, default_size)
        else:
            size = default_size
        # size = default_size   # to disable
        # # DEBUG tools p2, uncomment to create specific orders
        # precision = market_status[trading_enums.ExchangeConstantsMarketStatusColumns.PRECISION.value]
        # limits = market_status[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS.value]
        # price = personal_data.decimal_adapt_price(
        #     market_status,
        #     decimal.Decimal("0.910")
        # )
        # size = personal_data.decimal_adapt_quantity(
        #     market_status,
        #     decimal.Decimal("5.1")
        # )
        # # end debug tools
        open_orders = await self.get_open_orders(exchange_data)
        cancelled_orders = await self.get_cancelled_orders(exchange_data)
        if self.CHECK_EMPTY_ACCOUNT:
            assert size >= trading_constants.ZERO if enable_min_size_check else size == trading_constants.ZERO
            assert open_orders == []
            assert cancelled_orders == []
            return
        try:
            buy_limit = await self.create_limit_order(price, size, trading_enums.TradeOrderSide.BUY, symbol=symbol)
        except trading_errors.AuthenticationError as err:
            raise trading_errors.AuthenticationError(
                f"inner_test_create_and_cancel_limit_orders#create_limit_order {err}"
            ) from err
        try:
            self.check_created_limit_order(buy_limit, price, size, trading_enums.TradeOrderSide.BUY)
            assert await self.order_in_open_orders(open_orders, buy_limit, symbol=symbol)
            await self.check_can_get_order(buy_limit)
            # assert free portfolio amount is smaller than total amount
            balance = await self.get_portfolio()
            assert balance[settlement_currency][trading_constants.CONFIG_PORTFOLIO_FREE] < \
                   balance[settlement_currency][trading_constants.CONFIG_PORTFOLIO_TOTAL]
        finally:
            # don't leave buy_limit as open order
            await self.cancel_order(buy_limit)
        assert await self.order_not_in_open_orders(open_orders, buy_limit, symbol=symbol)
        assert await self.order_in_cancelled_orders(cancelled_orders, buy_limit, symbol=symbol)

    async def inner_test_cancel_uncancellable_order(self):
        if self.UNCANCELLABLE_ORDER_ID_SYMBOL_TYPE:
            order_id, symbol, order_type = self.UNCANCELLABLE_ORDER_ID_SYMBOL_TYPE
            with pytest.raises(trading_errors.ExchangeOrderCancelError):
                await self.exchange_manager.exchange.cancel_order(order_id, symbol, order_type)

    async def test_create_and_fill_market_orders(self):
        async with self.local_exchange_manager():
            await self.inner_test_create_and_fill_market_orders()

    async def inner_test_create_and_fill_market_orders(self):
        portfolio = await self.get_portfolio()
        current_price = await self.get_price()
        price = self.get_order_price(current_price, False, price_diff=0)
        size = self.get_order_size(portfolio, price)
        if self.CHECK_EMPTY_ACCOUNT:
            assert size == trading_constants.ZERO
            return
        buy_market = await self.create_market_order(current_price, size, trading_enums.TradeOrderSide.BUY)
        post_buy_portfolio = {}
        try:
            self.check_created_market_order(buy_market, size, trading_enums.TradeOrderSide.BUY)
            filled_order = await self.wait_for_fill(buy_market)
            parsed_filled_order = personal_data.create_order_instance_from_raw(
                self.exchange_manager.trader,
                filled_order
            )
            self._check_order(parsed_filled_order, size, trading_enums.TradeOrderSide.BUY)
            await self.wait_for_order_exchange_id_in_trades(parsed_filled_order.exchange_order_id)
            await self.check_require_order_fees_from_trades(
                filled_order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]
            )
            self.check_raw_closed_orders([filled_order])
            post_buy_portfolio = await self.get_portfolio()
            self.check_portfolio_changed(portfolio, post_buy_portfolio, False)
        finally:
            sell_size = self.get_sell_size_from_buy_order(buy_market)
            # sell: reset portfolio
            sell_market = await self.create_market_order(current_price, sell_size, trading_enums.TradeOrderSide.SELL)
            self.check_created_market_order(sell_market, sell_size, trading_enums.TradeOrderSide.SELL)
            await self.wait_for_fill(sell_market)
            post_sell_portfolio = await self.get_portfolio()
            if post_buy_portfolio:
                self.check_portfolio_changed(post_buy_portfolio, post_sell_portfolio, True)

    async def check_require_order_fees_from_trades(self, filled_exchange_order_id, symbol=None):
        symbol = symbol or self.SYMBOL
        order_with_fees = await self.exchange_manager.exchange.get_order(filled_exchange_order_id, symbol)
        assert not trading_exchanges.is_missing_trading_fees(order_with_fees)
        order_maybe_without_fees = \
            await self.exchange_manager.exchange.connector.get_order(filled_exchange_order_id, symbol=symbol)
        if self.exchange_manager.exchange.REQUIRE_ORDER_FEES_FROM_TRADES:
            assert trading_exchanges.is_missing_trading_fees(order_maybe_without_fees)
        else:
            assert not trading_exchanges.is_missing_trading_fees(order_maybe_without_fees)

    async def test_create_and_cancel_stop_orders(self):
        # pass if not implemented
        async with self.local_exchange_manager():
            await self.inner_test_create_and_cancel_stop_orders()

    async def inner_test_create_and_cancel_stop_orders(self):
        current_price = await self.get_price()
        price = self.get_order_price(current_price, False)
        portfolio = await self.get_portfolio()
        size = self.get_order_size(portfolio, price, settlement_currency=self._get_edit_order_settlement_currency())
        open_orders = await self.get_open_orders()
        assert self.exchange_manager.exchange.is_supported_order_type(
            trading_enums.TraderOrderType.STOP_LOSS
        ) is True
        stop_loss = await self.create_market_stop_loss_order(
            current_price, price, size, trading_enums.TradeOrderSide.SELL
        )
        try:
            self.check_created_stop_order(stop_loss, price, size, trading_enums.TradeOrderSide.SELL)
            stop_loss_from_get_order = await self.get_order(stop_loss.exchange_order_id, stop_loss.symbol)
            self.check_created_stop_order(stop_loss_from_get_order, price, size, trading_enums.TradeOrderSide.SELL)
            assert await self.order_in_open_orders(open_orders, stop_loss)
            ## for manual checks
            # print(f"Stop loss on {stop_loss.symbol} ok {stop_loss.origin_quantity} at {stop_loss.origin_price}")
            # await asyncio.sleep(15)
        finally:
            # don't leave stop_loss as open order
            await self.cancel_order(stop_loss)
        assert await self.order_not_in_open_orders(open_orders, stop_loss)

    async def test_get_my_recent_trades(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_my_recent_trades()

    async def inner_test_get_my_recent_trades(self):
        trades = await self.get_my_recent_trades()
        if self.CHECK_EMPTY_ACCOUNT:
            assert trades == []
            return
        assert trades
        self.check_raw_trades(trades)

    async def test_get_closed_orders(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_closed_orders()

    async def inner_test_get_closed_orders(self):
        await self.check_require_closed_orders_from_recent_trades()
        orders = await self.get_closed_orders()
        if self.CHECK_EMPTY_ACCOUNT:
            assert orders == []
            return
        assert orders
        self.check_raw_closed_orders(orders)

    async def test_get_cancelled_orders(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_cancelled_orders()

    async def inner_test_get_cancelled_orders(self):
        if not self.exchange_manager.exchange.SUPPORT_FETCHING_CANCELLED_ORDERS:
            assert not self.exchange_manager.exchange.connector.client.has["fetchCanceledOrders"]
            # use get_closed order, no cancelled order is returned
            assert await self.exchange_manager.exchange.connector.get_cancelled_orders(self.SYMBOL) == []
            with pytest.raises(trading_errors.NotSupported):
                await self.get_cancelled_orders(force_fetch=True)
            return
        orders = await self.get_cancelled_orders()
        if self.CHECK_EMPTY_ACCOUNT:
            assert orders == []
            return
        assert orders
        self.check_raw_cancelled_orders(orders)

    async def test_edit_limit_order(self):
        # pass if not implemented
        async with self.local_exchange_manager():
            await self.inner_test_edit_limit_order()

    async def inner_test_edit_limit_order(self):
        current_price = await self.get_price()
        portfolio = await self.get_portfolio()
        price = self.get_order_price(current_price, True)
        size = self.get_order_size(portfolio, price, settlement_currency=self._get_edit_order_settlement_currency())
        open_orders = await self.get_open_orders()
        sell_limit = None
        try:
            sell_limit = await self.create_limit_order(price, size, trading_enums.TradeOrderSide.SELL)
            self.check_created_limit_order(sell_limit, price, size, trading_enums.TradeOrderSide.SELL)
            assert await self.order_in_open_orders(open_orders, sell_limit)
            edited_price = self.get_order_price(current_price, True, price_diff=2*self.ORDER_PRICE_DIFF)
            edited_size = self.get_order_size(portfolio, price, order_size=2*self.ORDER_SIZE, settlement_currency=self._get_edit_order_settlement_currency())
            sell_limit = await self.edit_order(sell_limit, edited_price=edited_price, edited_quantity=edited_size)
            await self.wait_for_edit(sell_limit, edited_size)
            sell_limit = await self.get_order(sell_limit.exchange_order_id, sell_limit.symbol)
            self.check_created_limit_order(sell_limit, edited_price, edited_size, trading_enums.TradeOrderSide.SELL)
        finally:
            if sell_limit is not None:
                await self.cancel_order(sell_limit)
                assert await self.order_not_in_open_orders(open_orders, sell_limit)

    async def test_edit_stop_order(self):
        # pass if not implemented
        async with self.local_exchange_manager():
            await self.inner_test_edit_stop_order()

    async def inner_test_edit_stop_order(self):
        current_price = await self.get_price()
        portfolio = await self.get_portfolio()
        price = self.get_order_price(current_price, False)
        size = self.get_order_size(portfolio, price, settlement_currency=self._get_edit_order_settlement_currency())
        open_orders = await self.get_open_orders()
        stop_loss = None
        try:
            stop_loss = await self.create_market_stop_loss_order(
                current_price, price, size, trading_enums.TradeOrderSide.SELL
            )
            self.check_created_stop_order(stop_loss, price, size, trading_enums.TradeOrderSide.SELL)
            assert await self.order_in_open_orders(open_orders, stop_loss)
            edited_price = self.get_order_price(current_price, False, price_diff=2*self.ORDER_PRICE_DIFF)
            edited_size = self.get_order_size(portfolio, price, order_size=2*self.ORDER_SIZE, settlement_currency=self._get_edit_order_settlement_currency())
            stop_loss = await self.edit_order(stop_loss, edited_price=edited_price, edited_quantity=edited_size)
            await self.wait_for_edit(stop_loss, edited_size)
            stop_loss = await self.get_order(stop_loss.exchange_order_id, stop_loss.symbol)
            self.check_created_stop_order(stop_loss, edited_price, edited_size, trading_enums.TradeOrderSide.SELL)
        finally:
            if stop_loss is not None:
                await self.cancel_order(stop_loss)
                assert await self.order_not_in_open_orders(open_orders, stop_loss)

    def _get_edit_order_settlement_currency(self):
        return symbols.parse_symbol(self.SYMBOL).base

    async def test_create_single_bundled_orders(self):
        # pass if not implemented
        async with self.local_exchange_manager():
            await self.inner_test_create_single_bundled_orders()

    async def inner_test_create_single_bundled_orders(self):
        await self._test_untriggered_single_bundled_orders()
        await self._test_triggered_simple_bundled_orders()

    async def test_create_double_bundled_orders(self):
        # pass if not implemented
        async with self.local_exchange_manager():
            await self.inner_test_create_double_bundled_orders()

    async def inner_test_create_double_bundled_orders(self):
        await self._test_untriggered_double_bundled_orders()
        await self._test_triggered_double_bundled_orders()

    async def _test_untriggered_single_bundled_orders(self):
        # tests uncreated bundled orders (remain bound to initial order but initial order does not get filled)
        current_price = await self.get_price()
        stop_loss, _ = await self._get_bundled_orders_stop_take_profit(current_price)
        size = stop_loss.origin_quantity
        open_orders = await self.get_open_orders()

        price = personal_data.decimal_adapt_price(
            self.exchange_manager.exchange.get_market_status(self.SYMBOL),
            stop_loss.origin_price * decimal.Decimal(f"{1 + self.ORDER_PRICE_DIFF/2/100}")
        )
        limit_order = await self.create_limit_order(price, size,
                                                    trading_enums.TradeOrderSide.BUY,
                                                    push_on_exchange=False)
        params = await self.bundle_orders(limit_order, stop_loss)
        limit_order = await self._create_order_on_exchange(limit_order, params=params)
        self.check_created_limit_order(limit_order, price, size, trading_enums.TradeOrderSide.BUY)
        # stop and take profit are bundled but not created as long as the initial order is not filled
        additionally_fetched_orders = await self.get_similar_orders_in_open_orders(open_orders, [limit_order])
        assert len(additionally_fetched_orders) == 1  # only created limit_order
        await self.cancel_order(limit_order)
        # limit_order no more in open orders, stop and take profits are not created
        assert len(await self.get_open_orders()) == len(open_orders)

    async def _test_untriggered_double_bundled_orders(self):
        # tests uncreated bundled orders (remain bound to initial order but initial order does not get filled)
        current_price = await self.get_price()
        stop_loss, take_profit = await self._get_bundled_orders_stop_take_profit(current_price)
        size = stop_loss.origin_quantity
        open_orders = await self.get_open_orders()

        price = personal_data.decimal_adapt_price(
            self.exchange_manager.exchange.get_market_status(self.SYMBOL),
            stop_loss.origin_price * decimal.Decimal(f"{1 + self.ORDER_PRICE_DIFF/2/100}")
        )
        limit_order = await self.create_limit_order(price, size,
                                                    trading_enums.TradeOrderSide.BUY,
                                                    push_on_exchange=False)
        params = await self.bundle_orders(limit_order, stop_loss, take_profit=take_profit)
        if not self.SUPPORTS_DOUBLE_BUNDLED_ORDERS:
            await self._create_order_on_exchange(limit_order, params=params, expected_creation_error=True)
            return
        limit_order = await self._create_order_on_exchange(limit_order, params=params)
        self.check_created_limit_order(limit_order, price, size, trading_enums.TradeOrderSide.BUY)
        # stop and take profit are bundled but not created as long as the initial order is not filled
        additionally_fetched_orders = await self.get_similar_orders_in_open_orders(open_orders, [limit_order])
        assert len(additionally_fetched_orders) == 1  # only created limit_order
        await self.cancel_order(limit_order)
        # limit_order no more in open orders, stop and take profits are not created
        assert len(await self.get_open_orders()) == len(open_orders)

    async def _test_triggered_simple_bundled_orders(self):
        #  tests bundled stop loss into open position order
        current_price = await self.get_price()
        stop_loss, _ = await self._get_bundled_orders_stop_take_profit(current_price)
        size = stop_loss.origin_quantity
        open_orders = await self.get_open_orders()
        # created bundled orders
        market_order = await self.create_market_order(current_price, size,
                                                      trading_enums.TradeOrderSide.BUY,
                                                      push_on_exchange=False)
        params = await self.bundle_orders(market_order, stop_loss)
        buy_market = await self._create_order_on_exchange(market_order, params=params)
        self.check_created_market_order(buy_market, size, trading_enums.TradeOrderSide.BUY)
        try:
            await self.wait_for_fill(buy_market)
            created_orders = [stop_loss]
            fetched_conditional_orders = await self.get_similar_orders_in_open_orders(open_orders, created_orders)
            for fetched_conditional_order in fetched_conditional_orders:
                # ensure stop loss / take profit is fetched in open orders
                # ensure stop loss / take profit cancel is working
                await self.cancel_order(fetched_conditional_order)
            for fetched_conditional_order in fetched_conditional_orders:
                assert await self.order_not_in_open_orders(open_orders, fetched_conditional_order)
        finally:
            # close position
            sell_market = await self.create_market_order(current_price, size,
                                                         trading_enums.TradeOrderSide.SELL)
            self.check_created_market_order(sell_market, size, trading_enums.TradeOrderSide.SELL)
            await self.wait_for_fill(sell_market)

    async def _test_triggered_double_bundled_orders(self):
        #  tests bundled stop loss and take profits into open position order
        current_price = await self.get_price()
        stop_loss, take_profit = await self._get_bundled_orders_stop_take_profit(current_price)
        size = stop_loss.origin_quantity
        open_orders = await self.get_open_orders()
        # created bundled orders
        market_order = await self.create_market_order(current_price, size,
                                                      trading_enums.TradeOrderSide.BUY,
                                                      push_on_exchange=False)
        params = await self.bundle_orders(market_order, stop_loss, take_profit=take_profit)
        if not self.SUPPORTS_DOUBLE_BUNDLED_ORDERS:
            await self._create_order_on_exchange(market_order, params=params, expected_creation_error=True)
            return
        buy_market = await self._create_order_on_exchange(market_order, params=params)
        self.check_created_market_order(buy_market, size, trading_enums.TradeOrderSide.BUY)
        try:
            await self.wait_for_fill(buy_market)
            created_orders = [stop_loss, take_profit]
            fetched_conditional_orders = await self.get_similar_orders_in_open_orders(open_orders, created_orders)
            orders_to_cancel = fetched_conditional_orders[0:1] \
                if self.CANCEL_DOUBLE_BUNDLED_ORDERS_TOGETHER else fetched_conditional_orders
            for fetched_conditional_order in orders_to_cancel:
                # ensure stop loss / take profit is fetched in open orders
                # ensure stop loss / take profit cancel is working
                await self.cancel_order(fetched_conditional_order)
            # always ensure that all orders have been cancelled
            for fetched_conditional_order in fetched_conditional_orders:
                assert await self.order_not_in_open_orders(open_orders, fetched_conditional_order)
        finally:
            # close position
            sell_market = await self.create_market_order(current_price, size,
                                                         trading_enums.TradeOrderSide.SELL)
            self.check_created_market_order(sell_market, size, trading_enums.TradeOrderSide.SELL)
            await self.wait_for_fill(sell_market)

    async def bundle_orders(self, initial_order, stop_loss, take_profit=None):
        # bundle stop loss and take profits into open position order
        params = await self.exchange_manager.trader.bundle_chained_order_with_uncreated_order(
            initial_order, stop_loss, False
        )
        # # consider stop loss in param
        stop_loss_included_params_len = len(params)
        assert stop_loss_included_params_len > 0
        if take_profit:
            params.update(
                await self.exchange_manager.trader.bundle_chained_order_with_uncreated_order(
                    initial_order, take_profit, False
                )
            )
            # consider take profit in param
            assert len(params) > stop_loss_included_params_len
        return params

    async def _get_bundled_orders_stop_take_profit(self, current_price):
        stop_loss_price = self.get_order_price(current_price, False)
        take_profit_price = self.get_order_price(current_price, True)
        size = self.get_order_size(await self.get_portfolio(), stop_loss_price)
        stop_loss = await self.create_market_stop_loss_order(current_price, stop_loss_price, size,
                                                             trading_enums.TradeOrderSide.SELL,
                                                             push_on_exchange=False)
        take_profit = await self.create_order(take_profit_price, current_price, size, trading_enums.TradeOrderSide.SELL,
                                              trading_enums.TraderOrderType.TAKE_PROFIT, push_on_exchange=False)
        return (
            stop_loss,
            take_profit,
        )

    async def get_portfolio(self):
        return await exchanges_test_tools.get_portfolio(self.exchange_manager, as_float=False, clear_empty=False)

    async def get_my_recent_trades(self, exchange_data=None):
        exchange_data = exchange_data or self.get_exchange_data()
        return await exchanges_test_tools.get_trades(self.exchange_manager, exchange_data)

    async def get_closed_orders(self, symbol=None):
        return await self.exchange_manager.exchange.get_closed_orders(symbol or self.SYMBOL)

    async def get_cancelled_orders(self, exchange_data=None, force_fetch=False, _symbols=None):
        if not force_fetch and not self.exchange_manager.exchange.SUPPORT_FETCHING_CANCELLED_ORDERS:
            # skipped
            return []
        exchange_data = exchange_data or self.get_exchange_data()
        return await exchanges_test_tools.get_cancelled_orders(self.exchange_manager, exchange_data, symbols=_symbols)

    async def check_require_closed_orders_from_recent_trades(self, symbol=None):
        if self.exchange_manager.exchange.REQUIRE_CLOSED_ORDERS_FROM_RECENT_TRADES:
            with pytest.raises(trading_errors.NotSupported):
                await self.exchange_manager.exchange.connector.get_closed_orders(symbol=symbol or self.SYMBOL)

    def check_duplicate(self, orders_or_trades):
        assert len(orders_or_trades) * (1 - self.DUPLICATE_TRADES_RATIO) <= len({
            f"{o[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]}"
            f"{o.get(trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value)}"
            f"{o[trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value]}"
            f"{o[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value]}"
            f"{o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]}"
            for o in orders_or_trades
        }) <= len(orders_or_trades)

    def check_raw_closed_orders(self, closed_orders):
        self.check_duplicate(closed_orders)
        incomplete_fees_orders = []
        allow_incomplete_fees = len(closed_orders) > 1
        for closed_order in closed_orders:
            self.check_parsed_closed_order(
                personal_data.create_order_instance_from_raw(self.exchange_manager.trader, closed_order),
                incomplete_fees_orders,
                allow_incomplete_fees
            )
        if allow_incomplete_fees and incomplete_fees_orders:
            # at least 2 orders have fees (the 2 recent market orders from market orders tests)
            assert len(closed_orders) - len(incomplete_fees_orders) >= 2

    def check_raw_cancelled_orders(self, cancelled_orders):
        self.check_duplicate(cancelled_orders)
        incomplete_fees_orders = []
        allow_incomplete_fees = False
        for cancelled_order in cancelled_orders:
            assert cancelled_order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] \
                   == trading_enums.OrderStatus.CANCELED.value
            self.check_parsed_closed_order(
                personal_data.create_order_instance_from_raw(self.exchange_manager.trader, cancelled_order),
                incomplete_fees_orders,
                allow_incomplete_fees
            )
        assert not incomplete_fees_orders

    def check_parsed_closed_order(
        self, order: personal_data.Order, incomplete_fee_orders: list,
        allow_incomplete_fees: bool
    ):
        assert order.symbol
        assert order.timestamp
        assert order.order_type
        assert order.order_type is not trading_enums.TraderOrderType.UNKNOWN.value
        assert order.status
        if (
            order.status == trading_enums.OrderStatus.CANCELED and self.EXPECT_MISSING_FEE_IN_CANCELLED_ORDERS
        ):
            assert order.fee is None
        else:
            try:
                assert order.fee, f"Unexpected missing fee: {order.to_dict()}"
                assert isinstance(order.fee[trading_enums.FeePropertyColumns.COST.value], decimal.Decimal)
                has_paid_fees = order.fee[trading_enums.FeePropertyColumns.COST.value] > trading_constants.ZERO
                if has_paid_fees:
                    assert order.fee[trading_enums.FeePropertyColumns.EXCHANGE_ORIGINAL_COST.value] is not None
                else:
                    assert trading_enums.FeePropertyColumns.EXCHANGE_ORIGINAL_COST.value in order.fee
                if has_paid_fees:
                    assert order.fee[trading_enums.FeePropertyColumns.CURRENCY.value] is not None
                else:
                    assert trading_enums.FeePropertyColumns.CURRENCY.value in order.fee
                if self.CANCELLED_ORDERS_IN_CLOSED_ORDERS:
                    # might have been manually added for consistency
                    assert order.fee[trading_enums.FeePropertyColumns.IS_FROM_EXCHANGE.value] in (True, False)
                else:
                    assert order.fee[trading_enums.FeePropertyColumns.IS_FROM_EXCHANGE.value] is True
            except AssertionError:
                if (
                    not order.fee and self.ALLOW_0_MAKER_FEES and
                    order.taker_or_maker == trading_enums.ExchangeConstantsOrderColumns.MAKER.value
                ):
                    incomplete_fee_orders.append(order)
                elif allow_incomplete_fees and self.EXPECT_MISSING_ORDER_FEES_DUE_TO_ORDERS_TOO_OLD_FOR_RECENT_TRADES:
                    incomplete_fee_orders.append(order)
                else:
                    raise
        assert order.order_id
        assert order.exchange_order_id
        assert order.side
        if order.status not in (trading_enums.OrderStatus.REJECTED, trading_enums.OrderStatus.CANCELED):
            assert order.origin_quantity
            if self.OPEN_ORDERS_IN_CLOSED_ORDERS and order.status is trading_enums.OrderStatus.OPEN:
                # when order is open, cost is not full
                return
            if order.exchange_order_id in self.EXPECTED_INVALID_ORDERS_QUANTITY:
                with pytest.raises(AssertionError):
                    self.check_theoretical_cost(
                        symbols.parse_symbol(order.symbol), order.origin_quantity,
                        order.origin_price, order.total_cost
                    )
            else:
                self.check_theoretical_cost(
                    symbols.parse_symbol(order.symbol), order.origin_quantity,
                    order.origin_price, order.total_cost
                )
            if "USD" in order.market:
                assert self.MIN_TRADE_USD_VALUE < order.total_cost < self.MAX_TRADE_USD_VALUE

    def check_raw_trades(self, trades):
        self.check_duplicate(trades)
        for trade in trades:
            self.check_parsed_trade(
                personal_data.create_trade_instance_from_raw(self.exchange_manager.trader, trade)
            )

    def check_parsed_trade(self, trade: personal_data.Trade):
        assert trade.symbol
        assert trade.total_cost > 0
        assert trade.trade_type
        assert trade.trade_type is not trading_enums.TraderOrderType.UNKNOWN
        assert trade.exchange_trade_type is not trading_enums.TradeOrderType.UNKNOWN
        assert trade.status
        assert trade.fee
        assert trade.origin_order_id
        assert trade.exchange_order_id
        if self.IGNORE_EXCHANGE_TRADE_ID:
            assert trade.exchange_trade_id is None
        else:
            assert trade.exchange_trade_id
        assert trade.side
        if trade.status is not trading_enums.OrderStatus.CANCELED:
            assert trade.executed_time
            assert trade.executed_quantity
            self.check_theoretical_cost(
                symbols.parse_symbol(trade.symbol), trade.executed_quantity,
                trade.executed_price, trade.total_cost
            )
            if "USD" in trade.market:
                assert self.MIN_TRADE_USD_VALUE * decimal.Decimal("0.9") < trade.total_cost < self.MAX_TRADE_USD_VALUE, (
                    f"{self.MIN_TRADE_USD_VALUE * decimal.Decimal('0.9')} < {trade.total_cost} < {self.MAX_TRADE_USD_VALUE} "
                    f"is FALSE"
                )

    def check_theoretical_cost(self, symbol, quantity, price, cost):
        theoretical_cost = quantity * price
        assert theoretical_cost * decimal.Decimal("0.8") <= cost <= theoretical_cost * decimal.Decimal("1.2")

    async def get_price(self, symbol=None):
        return decimal.Decimal(str(
            (await self.exchange_manager.exchange.get_price_ticker(symbol or self.SYMBOL))[
                trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
            ]
        ))

    async def get_order(self, exchange_order_id, symbol=None):
        assert self.exchange_manager.exchange.connector.client.has["fetchOrder"] is \
               self.EXPECT_FETCH_ORDER_TO_BE_AVAILABLE
        order = await self.exchange_manager.exchange.get_order(exchange_order_id, symbol or self.SYMBOL)
        self._check_fetched_order_dicts([order])
        return personal_data.create_order_instance_from_raw(self.exchange_manager.trader, order)

    async def edit_order(self, order,
                         edited_quantity: decimal.Decimal = None,
                         edited_price: decimal.Decimal = None,
                         edited_stop_price: decimal.Decimal = None,
                         edited_current_price: decimal.Decimal = None,
                         params: dict = None):
        print(f"editing order: edited_quantity {edited_quantity} edited_price {edited_price} (current order: {order})")
        edited_order = await self.exchange_manager.exchange.edit_order(
            order.exchange_order_id,
            order.order_type,
            order.symbol,
            quantity=order.origin_quantity if edited_quantity is None else edited_quantity,
            price=order.origin_price if edited_price is None else edited_price,
            stop_price=edited_stop_price,
            side=order.side,
            current_price=edited_current_price,
            params=params
        )
        assert edited_order is not None
        return personal_data_orders.order_factory.create_order_instance_from_raw(self.exchange_manager.trader, edited_order)

    async def create_limit_order(self, price, size, side, symbol=None,
                                 push_on_exchange=True):
        order_type = trading_enums.TraderOrderType.BUY_LIMIT \
            if side is trading_enums.TradeOrderSide.BUY else trading_enums.TraderOrderType.SELL_LIMIT
        return await self.create_order(price, price, size, side, order_type,
                                       symbol=symbol, push_on_exchange=push_on_exchange)

    async def create_market_stop_loss_order(self, current_price, stop_price, size, side, symbol=None,
                                            push_on_exchange=True):
        self.exchange_manager.trader.allow_artificial_orders = False
        return await self.create_order(stop_price, current_price, size, side, trading_enums.TraderOrderType.STOP_LOSS,
                                       symbol=symbol, push_on_exchange=push_on_exchange)

    async def create_market_order(self, current_price, size, side, symbol=None,
                                  push_on_exchange=True):
        order_type = trading_enums.TraderOrderType.BUY_MARKET \
            if side is trading_enums.TradeOrderSide.BUY else trading_enums.TraderOrderType.SELL_MARKET
        return await self.create_order(None, current_price, size, side, order_type,
                                       symbol=symbol, push_on_exchange=push_on_exchange)

    async def create_order(self, price, current_price, size, side, order_type,
                           symbol=None, push_on_exchange=True):
        if size == trading_constants.ZERO:
            raise AssertionError(f"Trying to create and order with a size of {size}")
        current_order = personal_data.create_order_instance(
            self.exchange_manager.trader,
            order_type=order_type,
            symbol=symbol or self.SYMBOL,
            current_price=current_price,
            quantity=size,
            price=price,
            side=side,
        )
        assert current_order.is_self_managed() is False # will be a real order: can't be self-managed
        if push_on_exchange:
            current_order = await self._create_order_on_exchange(current_order)
            assert current_order.is_self_managed() is False # is a real order: can't be self-managed
        if current_order is None:
            raise AssertionError("Error when creating order")
        return current_order

    async def _create_order_on_exchange(self, order, params=None, expected_creation_error=False):
        # uncomment to bypass self.exchange_manager.trader
        # created_orders = await exchanges_test_tools.create_orders(
        #     self.exchange_manager,
        #     [order.to_dict()],
        #     self.OPEN_TIMEOUT,
        #     {order.symbol: order.created_last_price}
        # )
        # created_order = created_orders[0]
        created_order = await self.exchange_manager.trader.create_order(order, params=params, wait_for_creation=False)
        if expected_creation_error:
            if created_order is None:
                return None  # expected
            raise AssertionError(
                f"Created order is not None while expected_creation_error is True. The order was created on exchange"
            )
        if created_order is None:
            raise AssertionError(f"Created order is None. input order: {order}, params: {params}")
        if created_order.status is trading_enums.OrderStatus.PENDING_CREATION:
            await self.wait_for_open(created_order)
            return await self.get_order(created_order.exchange_order_id, order.symbol)
        return created_order

    def get_order_size(self, portfolio, price, symbol=None, order_size=None, settlement_currency=None):
        if self.CHECK_EMPTY_ACCOUNT:
            return trading_constants.ZERO
        order_size = order_size or self.ORDER_SIZE
        settlement_currency = settlement_currency or self.SETTLEMENT_CURRENCY
        currency_quantity = portfolio[settlement_currency][self.PORTFOLIO_TYPE_FOR_SIZE] \
            * decimal.Decimal(order_size) / trading_constants.ONE_HUNDRED
        symbol = symbols.parse_symbol(symbol or self.SYMBOL)
        if symbol.is_inverse():
            order_quantity = currency_quantity * price
        elif settlement_currency == symbol.quote:
            order_quantity = currency_quantity / price
        else:
            order_quantity = currency_quantity
        return personal_data.decimal_adapt_quantity(
            self.exchange_manager.exchange.get_market_status(str(symbol)),
            order_quantity
        )

    def check_order_size_and_price(self, size, price, symbol=None, allow_empty_size=False):
        market_status = self.exchange_manager.exchange.get_market_status(str(symbol or self.SYMBOL))
        precision_amount = market_status[
            trading_enums.ExchangeConstantsMarketStatusColumns.PRECISION.value
        ].get(trading_enums.ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value, 0)
        assert 0 <= precision_amount < 10   # is really the number of digits
        assert int(precision_amount) == precision_amount    # is an int
        precision_price = market_status[
            trading_enums.ExchangeConstantsMarketStatusColumns.PRECISION.value
        ].get(trading_enums.ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value, 0)
        assert 0 < precision_price < 10   # is really the number of digits
        assert int(precision_price) == precision_price    # is an int

        assert personal_data_orders.decimal_trunc_with_n_decimal_digits(size, precision_amount) == size
        assert personal_data_orders.decimal_trunc_with_n_decimal_digits(price, precision_price) == price

        # also check using decimal_check_and_adapt_order_details_if_necessary,
        # which is used to create orders in trading modes
        adapted_details = personal_data.decimal_check_and_adapt_order_details_if_necessary(
            size,
            price,
            market_status
        )
        if size == trading_constants.ZERO:
            if allow_empty_size:
                # can happen on empty accounts
                assert adapted_details == []
            else:
                raise AssertionError(f"{size=} but {allow_empty_size=}")
        else:
            cost = size * price
            # will fail if order min size checks are invalid
            assert adapted_details, f"Given size ({size}, cost={cost}) is too small according to parsed exchange rules"
            for order_quantity, order_price in adapted_details:
                assert order_quantity == size # size should not change
                assert order_price == price # price should not change


    def get_sell_size_from_buy_order(self, buy_order):
        sell_size = buy_order.origin_quantity
        if buy_order.fee and buy_order.fee[trading_enums.FeePropertyColumns.CURRENCY.value] == self.ORDER_CURRENCY:
            sell_size = sell_size - buy_order.fee[trading_enums.FeePropertyColumns.COST.value]
        return personal_data.decimal_adapt_quantity(
            self.exchange_manager.exchange.get_market_status(str(buy_order.symbol)),
            sell_size
        )

    def get_order_price(self, price, is_above_price, symbol=None, price_diff=None):
        price_diff = self.ORDER_PRICE_DIFF if price_diff is None else price_diff
        multiplier = 1 + price_diff / 100 if is_above_price else 1 - price_diff / 100
        return personal_data.decimal_adapt_price(
            self.exchange_manager.exchange.get_market_status(symbol or self.SYMBOL),
            price * (decimal.Decimal(str(multiplier)))
        )

    async def get_open_orders(self, exchange_data=None, _symbols=None):
        exchange_data = exchange_data or self.get_exchange_data()
        orders = await exchanges_test_tools.get_open_orders(self.exchange_manager, exchange_data, symbols=_symbols)
        self.check_duplicate(orders)
        self._check_fetched_order_dicts(orders)
        return orders

    def _check_fetched_order_dicts(self, orders: list[dict]):
        for order in orders:
            # unknown orders should not happen
            assert order[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] != \
                   trading_enums.TradeOrderType.UNKNOWN.value
            # unexpected statuses should not happen: ensure status can be parsed
            trading_enums.OrderStatus(order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value])

    def check_created_limit_order(self, order, price, size, side):
        self._check_order(order, size, side)
        assert order.origin_price == price, f"{order.origin_price} != {price}"
        assert isinstance(order.filled_quantity, decimal.Decimal)
        expected_type = personal_data.BuyLimitOrder \
            if side is trading_enums.TradeOrderSide.BUY else personal_data.SellLimitOrder
        assert isinstance(order, expected_type)

    def check_created_market_order(self, order, size, side):
        self._check_order(order, size, side)
        assert isinstance(order.filled_quantity, decimal.Decimal)
        if self.CONVERTS_MARKET_INTO_LIMIT_ORDERS:
            expected_type = personal_data.BuyLimitOrder \
                if side is trading_enums.TradeOrderSide.BUY else personal_data.SellLimitOrder
        else:
            expected_type = personal_data.BuyMarketOrder \
                if side is trading_enums.TradeOrderSide.BUY else personal_data.SellMarketOrder
        assert isinstance(order, expected_type)

    def check_created_stop_order(self, order, price, size, side):
        self._check_order(order, size, side)
        assert order.origin_price == price, f"{order.origin_price=} != {price=}"
        assert isinstance(order.filled_quantity, decimal.Decimal)
        assert order.side is side
        assert order.order_type is trading_enums.TraderOrderType.STOP_LOSS
        assert order.is_self_managed() is False # is real stop loss: NOT self-managed
        expected_type = personal_data.StopLossOrder
        assert isinstance(order, expected_type)

    def check_portfolio_changed(self, previous_portfolio, updated_portfolio, has_increased, symbol=None):
        previous_free_quantity = previous_portfolio[symbol or self.SETTLEMENT_CURRENCY][
            trading_constants.CONFIG_PORTFOLIO_FREE]
        updated_free_quantity = updated_portfolio[symbol or self.SETTLEMENT_CURRENCY][
            trading_constants.CONFIG_PORTFOLIO_FREE]
        if has_increased:
            assert updated_free_quantity > previous_free_quantity
        else:
            assert updated_free_quantity < previous_free_quantity

    def _check_order(self, order, size, side):
        if self.CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES:
            # actual origin_quantity may vary due to quantity conversion for market orders
            assert size * decimal.Decimal("0.8") <= order.origin_quantity <= size * decimal.Decimal("1.2"), (
                f"FALSE: {size * decimal.Decimal('0.8')} <= {order.origin_quantity} <= {size * decimal.Decimal('1.2')}"
            )
        else:
            assert round(order.origin_quantity, 8) == round(size, 8), (
                f"FALSE: {order.origin_quantity} == {size}"
            )
        assert order.exchange_order_id and isinstance(order.exchange_order_id, str)
        assert order.side is side
        assert order.total_cost > trading_constants.ZERO
        assert order.is_open()

    async def wait_for_order_exchange_id_in_trades(self, order_exchange_id):
        if self.IGNORE_EXCHANGE_TRADE_ID:
            return True, ""

        def check_order_exchange_id_in_trades(trades):
            trades_exchange_ids = [
                trade[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]
                for trade in trades
            ]
            if order_exchange_id in trades_exchange_ids:
                return True, ""
            return False, f"{order_exchange_id} is not in recent trades exchange ids ({trades_exchange_ids})"
        return await self._get_recent_trades_until(check_order_exchange_id_in_trades, self.RECENT_TRADES_UPDATE_TIMEOUT)

    async def _get_recent_trades_until(self, validation_func, timeout):
        t0 = time.time()
        message = ""
        recent_trades = []
        iterations = 0
        while time.time() - t0 < timeout:
            recent_trades = await self.get_my_recent_trades()
            iterations += 1
            if recent_trades:
                found, message = validation_func(recent_trades)
                if found:
                    print(f"{self.exchange_manager.exchange_name} {validation_func.__name__} "
                          f"True after {time.time() - t0} seconds ({iterations} iterations).")
                    return recent_trades
            await asyncio.sleep(1)
        raise TimeoutError(
            f"Trade not found within {timeout}s and {len(recent_trades)} trades: ({validation_func.__name__}), "
            f"message: {message}"
        )

    async def wait_for_fill(self, order):
        def parse_is_filled(raw_order):
            return personal_data.parse_order_status(raw_order) in {trading_enums.OrderStatus.FILLED,
                                                                   trading_enums.OrderStatus.CLOSED}
        return await self._get_order_until(order, parse_is_filled, self.MARKET_FILL_TIMEOUT, True)

    def parse_order_is_not_pending(self, raw_order):
        return personal_data.parse_order_status(raw_order) not in (trading_enums.OrderStatus.UNKNOWN, None)

    async def wait_for_open(self, order):
        await self._get_order_until(order, self.parse_order_is_not_pending, self.OPEN_TIMEOUT, True)

    async def wait_for_cancel(self, order):
        return personal_data.create_order_instance_from_raw(
            self.exchange_manager.trader,
            await self._get_order_until(order, personal_data.parse_is_cancelled, self.CANCEL_TIMEOUT, False)
        )

    async def wait_for_edit(self, order, edited_quantity):
        def is_edited(row_order):
            return round(decimal.Decimal(str(row_order[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value])), 8) \
                   == round(edited_quantity, 8)
        await self._get_order_until(order, is_edited, self.EDIT_TIMEOUT, False)

    async def _get_order_until(self, order, validation_func, timeout, can_order_be_not_found_on_exchange):
        allow_not_found_order_on_exchange = \
            can_order_be_not_found_on_exchange \
            and self.exchange_manager.exchange.EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION
        t0 = time.time()
        iterations = 0
        while time.time() - t0 < timeout:
            raw_order = await self.exchange_manager.exchange.get_order(order.exchange_order_id, order.symbol)
            iterations += 1
            if raw_order is None:
                print(f"{self.exchange_manager.exchange_name} {order.order_type} {validation_func.__name__} "
                      f"Order not found after {time.time() - t0} seconds. Order: [{order}]. Raw order: [{raw_order}]")
                if not allow_not_found_order_on_exchange:
                    raise AssertionError(
                        f"exchange.get_order() returned None, which means order is not found on exchange. "
                        f"This should not happen as "
                        f"self.exchange_manager.exchange.EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION is "
                        f"{self.exchange_manager.exchange.EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION} "
                        f"and can_order_be_not_found_on_exchange is {can_order_be_not_found_on_exchange}"
                    )
            elif raw_order and validation_func(raw_order):
                print(f"{self.exchange_manager.exchange_name} {order.order_type} {validation_func.__name__} "
                      f"True after {time.time() - t0} seconds and {iterations} iterations. "
                      f"Order: [{order}]. Raw order: [{raw_order}]")
                return raw_order
            else:
                print(f"{self.exchange_manager.exchange_name} {order.order_type} {validation_func.__name__} "
                      f"False after {time.time() - t0} seconds and {iterations} iterations. "
                      f"Order: [{order}]. Raw order: [{raw_order}]")
            await asyncio.sleep(1)
        raise TimeoutError(f"Order not filled/cancelled within {timeout}s: {order} ({validation_func.__name__})")

    async def check_can_get_order(self, order):
        fetched_order = await self.get_order(order.exchange_order_id, order.symbol)
        self.check_created_limit_order(fetched_order, order.origin_price, order.origin_quantity, order.side)

    async def order_in_fetched_orders(self, method, previous_orders, order, symbol=None, check_presence=True):
        t0 = time.time()
        iterations = 0
        while time.time() - t0 < self.ORDER_IN_OPEN_AND_CANCELLED_ORDERS_TIMEOUT or iterations == 0:
            iterations += 1
            delay_allowed = self.exchange_manager.exchange.CAN_HAVE_DELAYED_OPEN_ORDERS if \
                method is self.get_open_orders else self.exchange_manager.exchange.CAN_HAVE_DELAYED_CANCELLED_ORDERS
            if iterations > 1 and not delay_allowed:
                raise AssertionError(
                    f"{self.exchange_manager.exchange_name} is not expecting to have missing {method.__name__} "
                    f"on first iteration"
                )
            fetched_orders = await method(self.get_exchange_data(symbol=symbol))
            found_order = False
            for fetched_order in fetched_orders:
                if check_presence:
                    if (
                        fetched_order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]
                            == order.exchange_order_id
                    ):
                        print(f"=> {self.exchange_manager.exchange_name} {order.order_type} Order found in {len(fetched_orders)} "
                              f"{method.__name__} after after {time.time() - t0} seconds and {iterations} iterations. "
                              f"Order: [{order}].")
                        # use in as exchanges can have a max amount of fetched elements
                        assert len(fetched_orders) in (len(previous_orders), len(previous_orders) + 1), \
                            f"{len(fetched_orders)} not in {len(previous_orders), len(previous_orders) + 1}"
                        return True
                else:
                    # check order not in open orders
                    if(
                        fetched_order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]
                            == order.exchange_order_id
                    ):
                        print(f"{self.exchange_manager.exchange_name} {order.order_type} "
                              f"Order still found in {len(fetched_orders)} {method.__name__} after {time.time() - t0} seconds "
                              f"and {iterations} iterations. Order: [{order}]")
                        # order found, do not continue
                        found_order = True
                        break
            if check_presence:
                print(f"{self.exchange_manager.exchange_name} {order.order_type} "
                      f"Order sill not found in {len(fetched_orders)} {method.__name__} after {time.time() - t0} seconds "
                      f"and {iterations} iterations. Order: [{order}]")
            elif not found_order:
                print(f"=> {self.exchange_manager.exchange_name} {order.order_type} Order not found"
                      f" in {len(fetched_orders)} {method.__name__} after after {time.time() - t0} seconds "
                      f"and {iterations} iterations. "
                      f"Order: [{order}].")
                assert len(fetched_orders) <= len(previous_orders), f"{len(fetched_orders)} !<= {len(previous_orders)}"
                # order not found
                return True
            await asyncio.sleep(1)
        print(f"Order {'not' if check_presence else 'still'} "
              f"found in {method.__name__} within {self.ORDER_IN_OPEN_AND_CANCELLED_ORDERS_TIMEOUT}s: {order}")
        return False

    async def get_similar_orders_in_open_orders(self, previous_open_orders, orders):
        if not isinstance(orders, list):
            orders = [orders]
        found_orders = []
        open_orders = await self.get_open_orders()
        assert len(open_orders) == len(previous_open_orders) + len(orders)
        for order in orders:
            for open_order in open_orders:
                fetched_order = personal_data_orders.order_factory.create_order_instance_from_raw(
                    self.exchange_manager.trader,
                    open_order
                )
                if personal_data.is_associated_pending_order(order, fetched_order):
                    found_orders.append(fetched_order)
                    break
        if len(found_orders) == len(orders):
            return found_orders
        raise AssertionError(f"Can't find any order similar to {orders}. Found: {found_orders}")

    async def order_in_open_orders(self, previous_open_orders, order, symbol=None):
        return await self.order_in_fetched_orders(
            self.get_open_orders, previous_open_orders, order, symbol, check_presence=True
        )

    async def order_not_in_open_orders(self, previous_open_orders, order, symbol=None):
        return await self.order_in_fetched_orders(
            self.get_open_orders, previous_open_orders, order, symbol, check_presence=False
        )

    async def order_in_cancelled_orders(self, previous_cancelled_orders, order, symbol=None):
        if not self.exchange_manager.exchange.SUPPORT_FETCHING_CANCELLED_ORDERS:
            # skipped
            return True
        return await self.order_in_fetched_orders(
            self.get_cancelled_orders, previous_cancelled_orders, order, symbol, check_presence=True
        )

    async def cancel_order(self, order):
        cancelled_order = order
        if not await self.exchange_manager.trader.cancel_order(order, wait_for_cancelling=False):
            raise AssertionError(f"cancel_order returned False ({order.symbol})")
        if order.status is trading_enums.OrderStatus.PENDING_CANCEL:
            cancelled_order = await self.wait_for_cancel(order)
        assert cancelled_order.status is trading_enums.OrderStatus.CANCELED
        if cancelled_order.state is not None:
            assert cancelled_order.is_cancelled()
        return order

    def get_config(self):
        return {
            constants.CONFIG_EXCHANGES: {
                self.EXCHANGE_NAME: {
                    constants.CONFIG_EXCHANGE_TYPE: self.EXCHANGE_TYPE
                }
            },
            constants.CONFIG_CRYPTO_CURRENCIES: {
                "test-crypto": {
                    constants.CONFIG_CRYPTO_PAIRS: self._get_all_symbols()
                }
            }
        }

    def _get_all_symbols(self):
        return [self.SYMBOL]

    def get_exchange_data(self, symbol=None, all_symbols=None) -> exchange_data_import.ExchangeData:
        _symbols = all_symbols or [symbol or self.SYMBOL]
        return exchange_data_import.ExchangeData(
            auth_details={},
            exchange_details={"name": self.exchange_manager.exchange_name},
            markets=[
                {
                    "id": s, "symbol": s, "info": {}, "time_frame": self.TIME_FRAME,
                    "close": [0], "open": [0], "high": [0], "low": [0], "volume": [0], "time": [0]  # todo
                }
                for s in _symbols
            ]
        )

    def _get_market_filter(self):
        def market_filter(market):
            return (
                market[trading_enums.ExchangeConstantsMarketStatusColumns.SYMBOL.value]
                in (self.SYMBOL, )
            )

        return market_filter

    @contextlib.asynccontextmanager
    async def local_exchange_manager(
        self, market_filter=None, identifiers_suffix=None, use_invalid_creds=False, http_proxy_callback_factory=None
    ):
        try:
            credentials_exchange_name = self.CREDENTIALS_EXCHANGE_NAME or self.EXCHANGE_NAME
            if identifiers_suffix:
                credentials_exchange_name = f"{credentials_exchange_name}{identifiers_suffix}"
            async with get_authenticated_exchange_manager(
                    self.EXCHANGE_NAME,
                    self._get_exchange_tentacle_name(),
                    self.get_config(),
                    credentials_exchange_name=credentials_exchange_name,
                    market_filter=market_filter,
                    use_invalid_creds=use_invalid_creds,
                    http_proxy_callback_factory=http_proxy_callback_factory,
            ) as exchange_manager:
                self.exchange_manager = exchange_manager
                yield
        finally:
            self.exchange_manager = None

    def _get_exchange_tentacle_name(self):
        return self.EXCHANGE_TENTACLE_NAME or self.EXCHANGE_NAME.capitalize()

    def _get_exchange_tentacle_class(self):
        return tentacles_manager_api.get_tentacle_class_from_string(self._get_exchange_tentacle_name())

    def _supports_ip_whitelist_error(self):
        return bool(self._get_exchange_tentacle_class().EXCHANGE_IP_WHITELIST_ERRORS)


def _get_encoded_value(raw) -> str:
    return commons_configuration.encrypt(raw).decode()
