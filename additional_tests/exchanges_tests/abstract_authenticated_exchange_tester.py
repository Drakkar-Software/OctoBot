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
import asyncio
import contextlib
import decimal
import time

import mock
import pytest

import octobot_commons.constants as constants
import octobot_commons.symbols as symbols
import octobot_trading.errors as trading_errors
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.personal_data as personal_data
import octobot_trading.personal_data.orders as personal_data_orders
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools
import octobot_trading.util.test_tools.exchange_data as exchange_data_import
import trading_backend.enums
import octobot_tentacles_manager.api as tentacles_manager_api
from additional_tests.exchanges_tests import get_authenticated_exchange_manager

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
    VALID_ORDER_ID = "8bb80a81-27f7-4415-aa50-911ea46d841c"
    ORDER_SIZE = 10  # % of portfolio to include in test orders
    PORTFOLIO_TYPE_FOR_SIZE = trading_constants.CONFIG_PORTFOLIO_FREE
    CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = False
    ORDER_PRICE_DIFF = 20  # % of price difference compared to current price for limit and stop orders
    EXPECT_MISSING_ORDER_FEES_DUE_TO_ORDERS_TOO_OLD_FOR_RECENT_TRADES = False   # when recent trades are limited and
    # closed orders fees are taken from recent trades
    EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION = False
    OPEN_ORDERS_IN_CLOSED_ORDERS = False
    CANCELLED_ORDERS_IN_CLOSED_ORDERS = False
    RECENT_TRADES_UPDATE_TIMEOUT = 15
    MARKET_FILL_TIMEOUT = 15
    OPEN_TIMEOUT = 15
    CANCEL_TIMEOUT = 15
    EDIT_TIMEOUT = 15
    MIN_PORTFOLIO_SIZE = 1
    DUPLICATE_TRADES_RATIO = 0
    SUPPORTS_DOUBLE_BUNDLED_ORDERS = True
    # set true when cancelling any bundled order on exchange would automatically cancel the other(s)
    CANCEL_DOUBLE_BUNDLED_ORDERS_TOGETHER = True
    IGNORE_EXCHANGE_TRADE_ID = False    # set True when trade.exchange_trade_id can't be set
    MAX_TRADE_USD_VALUE = decimal.Decimal(8000)
    MIN_TRADE_USD_VALUE = decimal.Decimal("0.1")
    IS_ACCOUNT_ID_AVAILABLE = True  # set False when get_account_id is not available and should be checked
    EXPECTED_GENERATED_ACCOUNT_ID = False   # set True when account_id can't be fetch and a generated account id is used
    USE_ORDER_OPERATION_TO_CHECK_API_KEY_RIGHTS = False    # set True when api key rights can't be checked using a
    # dedicated api and have to be checked by sending an order operation
    EXPECTED_INVALID_ORDERS_QUANTITY = []   # orders with known invalid quantity exchange order id    (usually legacy)

    # Implement all "test_[name]" methods, call super() to run the test, pass to ignore it.
    # Override the "inner_test_[name]" method to override a test content.
    # Add method call to subclasses to be able to run them independently

    async def test_get_portfolio(self):
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
            assert filtered_markets_portfolio == all_markets_portfolio

    async def inner_test_get_portfolio(self):
        self.check_portfolio_content(await self.get_portfolio())

    def check_portfolio_content(self, portfolio):
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
            assert len(permissions) > 0
            assert trading_backend.enums.APIKeyRights.READING in permissions
            assert trading_backend.enums.APIKeyRights.SPOT_TRADING in permissions
            assert trading_backend.enums.APIKeyRights.FUTURES_TRADING in permissions
            if self.USE_ORDER_OPERATION_TO_CHECK_API_KEY_RIGHTS:
                # failed ? did not use _get_api_key_rights_using_order while expected
                _get_api_key_rights_using_order_mock.assert_called_once()
            else:
                # failed ? used _get_api_key_rights_using_order when not expected
                _get_api_key_rights_using_order_mock.assert_not_called()

    async def test_missing_trading_api_key_permissions(self):
        async with self.local_exchange_manager(identifiers_suffix="_READONLY"):
            await self.inner_test_missing_trading_api_key_permissions()

    async def inner_test_missing_trading_api_key_permissions(self):
        permissions = await self.exchange_manager.exchange_backend._get_api_key_rights()
        # ensure reading permission only are returned
        assert permissions == [trading_backend.enums.APIKeyRights.READING]
        # ensure order operations returns a permission error
        with pytest.raises(trading_errors.AuthenticationError) as err:
            await self.inner_test_create_and_cancel_limit_orders()
        # ensure AuthenticationError is raised when creating order
        assert "inner_test_create_and_cancel_limit_orders#create_limit_order" in str(err)

    async def test_get_not_found_order(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_not_found_order()

    async def inner_test_get_not_found_order(self):
        # Ensures that get_order() returns None when an order is not found, should not raise an error
        non_existing_order = await self.exchange_manager.exchange.get_order(self.VALID_ORDER_ID, self.SYMBOL)
        assert non_existing_order is None

    async def test_create_and_cancel_limit_orders(self):
        async with self.local_exchange_manager():
            await self.inner_test_create_and_cancel_limit_orders()

    async def inner_test_create_and_cancel_limit_orders(self, symbol=None, settlement_currency=None):
        symbol = symbol or self.SYMBOL
        exchange_data = self.get_exchange_data(symbol=symbol)
        settlement_currency = settlement_currency or self.SETTLEMENT_CURRENCY
        price = self.get_order_price(await self.get_price(symbol=symbol), False, symbol=symbol)
        size = self.get_order_size(
            await self.get_portfolio(), price, symbol=symbol, settlement_currency=settlement_currency
        )
        # # DEBUG tools, uncomment to create specific orders
        # symbol = "BTC/USD:BTC"
        # market_status = self.exchange_manager.exchange.get_market_status(symbol)
        # precision = market_status[trading_enums.ExchangeConstantsMarketStatusColumns.PRECISION.value]
        # limits = market_status[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS.value]
        # price = personal_data.decimal_adapt_price(
        #     market_status,
        #     decimal.Decimal("0.1810")
        # )
        # size = personal_data.decimal_adapt_quantity(
        #     market_status,
        #     decimal.Decimal("7")
        # )
        # # end debug tools
        open_orders = await self.get_open_orders(exchange_data)
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

    async def test_create_and_fill_market_orders(self):
        async with self.local_exchange_manager():
            await self.inner_test_create_and_fill_market_orders()

    async def inner_test_create_and_fill_market_orders(self):
        portfolio = await self.get_portfolio()
        current_price = await self.get_price()
        price = self.get_order_price(current_price, False, price_diff=0)
        size = self.get_order_size(portfolio, price)
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
        size = self.get_order_size(await self.get_portfolio(), price)
        open_orders = await self.get_open_orders()
        stop_loss = await self.create_market_stop_loss_order(current_price, price, size,
                                                             trading_enums.TradeOrderSide.SELL)
        self.check_created_stop_order(stop_loss, price, size, trading_enums.TradeOrderSide.SELL)
        stop_loss_from_get_order = await self.get_order(stop_loss.exchange_order_id, stop_loss.symbol)
        self.check_created_stop_order(stop_loss_from_get_order, price, size, trading_enums.TradeOrderSide.SELL)
        assert await self.order_in_open_orders(open_orders, stop_loss)
        await self.cancel_order(stop_loss)
        assert await self.order_not_in_open_orders(open_orders, stop_loss)

    async def test_get_my_recent_trades(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_my_recent_trades()

    async def inner_test_get_my_recent_trades(self):
        trades = await self.get_my_recent_trades()
        assert trades
        self.check_raw_trades(trades)

    async def test_get_closed_orders(self):
        async with self.local_exchange_manager():
            await self.inner_test_get_closed_orders()

    async def inner_test_get_closed_orders(self):
        await self.check_require_closed_orders_from_recent_trades()
        orders = await self.get_closed_orders()
        assert orders
        self.check_raw_closed_orders(orders)

    async def test_edit_limit_order(self):
        # pass if not implemented
        async with self.local_exchange_manager():
            await self.inner_test_edit_limit_order()

    async def inner_test_edit_limit_order(self):
        current_price = await self.get_price()
        portfolio = await self.get_portfolio()
        price = self.get_order_price(current_price, True)
        size = self.get_order_size(portfolio, price)
        open_orders = await self.get_open_orders()
        sell_limit = await self.create_limit_order(price, size, trading_enums.TradeOrderSide.SELL)
        self.check_created_limit_order(sell_limit, price, size, trading_enums.TradeOrderSide.SELL)
        assert await self.order_in_open_orders(open_orders, sell_limit)
        edited_price = self.get_order_price(current_price, True, price_diff=2*self.ORDER_PRICE_DIFF)
        edited_size = self.get_order_size(portfolio, price, order_size=2*self.ORDER_SIZE)
        await self.edit_order(sell_limit,
                              edited_price=edited_price,
                              edited_quantity=edited_size)
        await self.wait_for_edit(sell_limit, edited_size)
        sell_limit = await self.get_order(sell_limit.exchange_order_id, sell_limit.symbol)
        self.check_created_limit_order(sell_limit, edited_price, edited_size, trading_enums.TradeOrderSide.SELL)
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
        size = self.get_order_size(portfolio, price)
        open_orders = await self.get_open_orders()
        stop_loss = await self.create_market_stop_loss_order(current_price, price, size,
                                                             trading_enums.TradeOrderSide.SELL)
        self.check_created_stop_order(stop_loss, price, size, trading_enums.TradeOrderSide.SELL)
        assert await self.order_in_open_orders(open_orders, stop_loss)
        edited_price = self.get_order_price(current_price, False, price_diff=2*self.ORDER_PRICE_DIFF)
        edited_size = self.get_order_size(portfolio, price, order_size=2*self.ORDER_SIZE)
        await self.edit_order(stop_loss,
                              edited_stop_price=edited_price,
                              edited_quantity=edited_size)
        await self.wait_for_edit(stop_loss, edited_size)
        stop_loss = await self.get_order(stop_loss.exchange_order_id, stop_loss.symbol)
        self.check_created_stop_order(stop_loss, edited_price, edited_size, trading_enums.TradeOrderSide.SELL)
        await self.cancel_order(stop_loss)
        assert await self.order_not_in_open_orders(open_orders, stop_loss)

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

    def check_parsed_closed_order(
        self, order: personal_data.Order, incomplete_fee_orders: list, allow_incomplete_fees: bool
    ):
        assert order.symbol
        assert order.timestamp
        assert order.order_type
        assert order.order_type is not trading_enums.TraderOrderType.UNKNOWN.value
        assert order.status
        try:
            assert order.fee
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
            if allow_incomplete_fees and self.EXPECT_MISSING_ORDER_FEES_DUE_TO_ORDERS_TOO_OLD_FOR_RECENT_TRADES:
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
        assert trade.total_cost
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
                assert self.MIN_TRADE_USD_VALUE < trade.total_cost < self.MAX_TRADE_USD_VALUE

    def check_theoretical_cost(self, symbol, quantity, price, cost):
        theoretical_cost = quantity * price
        assert theoretical_cost * decimal.Decimal("0.8") <= cost <= theoretical_cost * decimal.Decimal("1.2")

    async def get_price(self, symbol=None):
        return decimal.Decimal(str(
            (await self.exchange_manager.exchange.get_price_ticker(symbol or self.SYMBOL))[
                trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
            ]
        ))

    @contextlib.asynccontextmanager
    async def local_exchange_manager(self, market_filter=None, identifiers_suffix=None):
        try:
            exchange_tentacle_name = self.EXCHANGE_TENTACLE_NAME or self.EXCHANGE_NAME.capitalize()
            credentials_exchange_name = self.CREDENTIALS_EXCHANGE_NAME or self.EXCHANGE_NAME
            if identifiers_suffix:
                credentials_exchange_name = f"{credentials_exchange_name}{identifiers_suffix}"
            async with get_authenticated_exchange_manager(
                    self.EXCHANGE_NAME,
                    exchange_tentacle_name,
                    self.get_config(),
                    credentials_exchange_name=credentials_exchange_name,
                    market_filter=market_filter
            ) as exchange_manager:
                self.exchange_manager = exchange_manager
                yield
        finally:
            self.exchange_manager = None

    async def get_order(self, exchange_order_id, symbol=None):
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
        return edited_order

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
        if push_on_exchange:
            current_order = await self._create_order_on_exchange(current_order)
        if current_order is None:
            raise AssertionError("Error when creating order")
        return current_order

    async def _create_order_on_exchange(self, order, params=None, expected_creation_error=False):
        # uncomment to bypass self.exchange_manager.trader
        # created_orders = await exchanges_test_tools.create_orders(
        #     self.exchange_manager,
        #     self.get_exchange_data(order.symbol),
        #     [order.to_dict()],
        #     self.OPEN_TIMEOUT
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
        order_size = order_size or self.ORDER_SIZE
        settlement_currency = settlement_currency or self.SETTLEMENT_CURRENCY
        currency_quantity = portfolio[settlement_currency][self.PORTFOLIO_TYPE_FOR_SIZE] \
            * decimal.Decimal(order_size) / trading_constants.ONE_HUNDRED
        symbol = symbols.parse_symbol(symbol or self.SYMBOL)
        if symbol.is_inverse():
            order_quantity = currency_quantity * price
        else:
            order_quantity = currency_quantity / price
        return personal_data.decimal_adapt_quantity(
            self.exchange_manager.exchange.get_market_status(str(symbol)),
            order_quantity
        )

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

    async def get_open_orders(self, exchange_data=None):
        exchange_data = exchange_data or self.get_exchange_data()
        orders = await exchanges_test_tools.get_open_orders(self.exchange_manager, exchange_data)
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
        assert order.origin_price == price
        expected_type = personal_data.BuyLimitOrder \
            if side is trading_enums.TradeOrderSide.BUY else personal_data.SellLimitOrder
        assert isinstance(order, expected_type)

    def check_created_market_order(self, order, size, side):
        self._check_order(order, size, side)
        expected_type = personal_data.BuyMarketOrder \
            if side is trading_enums.TradeOrderSide.BUY else personal_data.SellMarketOrder
        assert isinstance(order, expected_type)

    def check_created_stop_order(self, order, price, size, side):
        self._check_order(order, size, side)
        assert order.origin_price == price
        assert order.side is side
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
            assert size * decimal.Decimal("0.8") <= order.origin_quantity <= size * decimal.Decimal("1.2")
        else:
            assert order.origin_quantity == size
        assert order.side is side
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
            return decimal.Decimal(str(row_order[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value])) \
                   == edited_quantity
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
            await asyncio.sleep(1)
        raise TimeoutError(f"Order not filled/cancelled within {timeout}s: {order} ({validation_func.__name__})")

    async def check_can_get_order(self, order):
        fetched_order = await self.get_order(order.exchange_order_id, order.symbol)
        self.check_created_limit_order(fetched_order, order.origin_price, order.origin_quantity, order.side)

    async def order_in_open_orders(self, previous_open_orders, order, symbol=None):
        open_orders = await self.get_open_orders(self.get_exchange_data(symbol=symbol))
        assert len(open_orders) == len(previous_open_orders) + 1
        for open_order in open_orders:
            if open_order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value] == order.exchange_order_id:
                return True
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

    async def order_not_in_open_orders(self, previous_open_orders, order, symbol=None):
        open_orders = await self.get_open_orders(self.get_exchange_data(symbol=symbol))
        assert len(open_orders) == len(previous_open_orders)
        for open_order in open_orders:
            if open_order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value] == order.exchange_order_id:
                return False
        return True

    async def cancel_order(self, order):
        cancelled_order = order
        if not await self.exchange_manager.trader.cancel_order(order, wait_for_cancelling=False):
            raise AssertionError("cancel_order returned False")
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
                    "id": s, "symbol": s, "info": {}, "time_frame": "1h",
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
