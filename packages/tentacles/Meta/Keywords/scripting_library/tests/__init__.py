#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import pytest
import pytest_asyncio
import mock
import decimal
import sys
import asyncio

import octobot_commons.asyncio_tools as asyncio_tools
import octobot_trading.modes.script_keywords.context_management as context_management
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.enums as enums


@pytest.fixture
def null_context():
    context = context_management.Context(
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )
    yield context


@pytest_asyncio.fixture
async def mock_context(backtesting_trader):
    _, exchange_manager, trader_inst = backtesting_trader
    context = context_management.Context(
        mock.Mock(),
        exchange_manager,
        trader_inst,
        mock.Mock(),
        "BTC/USDT",
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
    )
    context.signal_builder = mock.Mock()
    context.is_trading_signal_emitter = mock.Mock(return_value=False)
    context.orders_writer = mock.Mock(log_many=mock.AsyncMock())
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    # init portfolio with 0.5 BTC, 20 ETH and 30000 USDT and only 0.1 available BTC
    portfolio_manager.portfolio.update_portfolio_from_balance({
        'BTC': {'available': decimal.Decimal("0.1"), 'total': decimal.Decimal("0.5")},
        'ETH': {'available': decimal.Decimal("20"), 'total': decimal.Decimal("20")},
        'USDT': {'available': decimal.Decimal("30000"), 'total': decimal.Decimal("30000")}
    }, True)
    exchange_manager.client_symbols.append("BTC/USDT")
    exchange_manager.client_symbols.append("ETH/USDT")
    exchange_manager.client_symbols.append("ETH/BTC")
    # init prices with BTC/USDT = 40000, ETH/BTC = 0.1 and ETH/USDT = 4000
    portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair["BTC/USDT"] = \
        decimal.Decimal("40000")
    portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair["ETH/USDT"] = \
        decimal.Decimal("4000")
    portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair["ETH/BTC"] = \
        decimal.Decimal("0.1")
    portfolio_manager.handle_balance_updated()
    yield context


@pytest.fixture
def symbol_market():
    return {
        enums.ExchangeConstantsMarketStatusColumns.LIMITS.value: {
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value: 0.5,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value: 100,
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value: 1,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MAX.value: 200
            },
            enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE.value: {
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MIN.value: 0.5,
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MAX.value: 50
            },
        },
        enums.ExchangeConstantsMarketStatusColumns.PRECISION.value: {
            enums.ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value: 8,
            enums.ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value: 8
        }
    }


@pytest.fixture
def event_loop():
    # re-configure async loop each time this fixture is called
    _configure_async_test_loop()
    loop = asyncio.new_event_loop()
    # use ErrorContainer to catch otherwise hidden exceptions occurring in async scheduled tasks
    error_container = asyncio_tools.ErrorContainer()
    loop.set_exception_handler(error_container.exception_handler)
    yield loop
    # will fail if exceptions have been silently raised
    loop.run_until_complete(error_container.check())
    loop.close()


@pytest.fixture
def skip_if_octobot_trading_mocking_disabled(request):
    try:
        with mock.patch.object(trading_exchanges.Trader, "cancel_order", mock.AsyncMock()):
            pass
        # mocking is available
    except TypeError:
        pytest.skip(reason=f"Disabled {request.node.name} [OctoBot-Trading mocks not allowed]")


def _configure_async_test_loop():
    if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
        # use WindowsSelectorEventLoopPolicy to avoid aiohttp connexion close warnings
        # https://github.com/encode/httpx/issues/914#issuecomment-622586610
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# set default values for async loop
_configure_async_test_loop()
