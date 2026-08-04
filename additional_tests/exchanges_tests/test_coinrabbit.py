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
import os

import pytest

import octobot_trading.constants as trading_constants
import additional_tests.exchanges_tests as exchanges_tests
from additional_tests.exchanges_tests import abstract_authenticated_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


def _require_coinrabbit_top_up_creds() -> tuple[str, str]:
    exchanges_tests._load_exchange_creds_env_variables_if_necessary()
    if not os.getenv("COINRABBIT_KEY") or not os.getenv("COINRABBIT_SECRET"):
        pytest.skip("COINRABBIT_KEY and COINRABBIT_SECRET must be set for top-up test")
    user_jwt = os.getenv("COINRABBIT_JWT")
    if not user_jwt:
        pytest.skip("COINRABBIT_JWT must be set for top-up test")
    x_api_key = os.getenv("COINRABBIT_X_API_KEY")
    if not x_api_key:
        pytest.skip("COINRABBIT_X_API_KEY must be set for top-up test")
    return user_jwt, x_api_key


class TestCoinRabbitAuthenticatedExchange(
    abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester
):
    # enter exchange name as a class variable here
    EXCHANGE_NAME = "coinrabbit"
    BASE_NETWORK = "BTC"
    QUOTE_NETWORK = "ETH"
    ORDER_CURRENCY = f"BTC@{BASE_NETWORK}"
    SETTLEMENT_CURRENCY = f"USDT@{QUOTE_NETWORK}"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}"
    ORDER_SIZE = 50  # % of portfolio to include in test orders
    CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = True
    IGNORE_EXCHANGE_TRADE_ID = True  # no fetchMyTrades on CoinRabbit
    VALID_ORDER_ID = "1777764898965454848"
    EXPECT_MISSING_FEE_IN_CANCELLED_ORDERS = False
    TOP_UP_CODE = "usdt"
    TOP_UP_NETWORK = "eth"
    TOP_UP_AMOUNT = "0"


    async def test_get_portfolio(self):
        async with self.local_exchange_manager():
            portfolio = await self.get_portfolio()
            asset = "USDT@ETH"
            assert asset in portfolio
            values = portfolio[asset]
            assert all(
                key in values
                for key in (
                    trading_constants.CONFIG_PORTFOLIO_FREE,
                    trading_constants.CONFIG_PORTFOLIO_USED,
                    trading_constants.CONFIG_PORTFOLIO_TOTAL,
                )
            )
            assert values[trading_constants.CONFIG_PORTFOLIO_TOTAL] > trading_constants.ZERO

    async def test_untradable_symbols(self):
        await super().test_untradable_symbols()
    
    async def test_get_max_open_orders_count(self):
        await super().test_get_max_open_orders_count()

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
        await super().test_api_key_ip_whitelist_error()

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

    # TODO: wait for portfolio settlement (not only order fill) before check_portfolio_changed; fetchOrder closed
    # status from the ccxt fee heuristic does not mean balances have settled (used→free can lag).
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

    async def test_ob_top_up_trading_cell(self):
        if not float(self.TOP_UP_AMOUNT):
            pytest.skip(f"TOP_UP_AMOUNT is empty: {self.TOP_UP_AMOUNT}")
        user_jwt, x_api_key = _require_coinrabbit_top_up_creds()
        async with self.local_exchange_manager():
            client = self.exchange_manager.exchange.connector.client
            assert client.id == "ob_coinrabbit"
            response = await client.ob_top_up_trading_cell(
                self.TOP_UP_CODE,
                self.TOP_UP_AMOUNT,
                self.TOP_UP_NETWORK,
                {"userToken": user_jwt, "xApiKey": x_api_key},
            )
            assert isinstance(response, dict)
            assert response
