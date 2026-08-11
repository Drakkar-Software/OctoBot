#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.

import mock
import pytest

import octobot_trading.exchanges.traders.trader as trader_module

pytestmark = pytest.mark.asyncio


class TestTraderInitializeImplLogging:
    async def test_does_not_log_enabled_on_when_exchange_only(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "kraken"
        exchange_manager.is_trading = False
        exchange_manager.should_log_exchange_lifecycle_debug = mock.Mock(return_value=False)
        exchange_manager.register_trader = mock.AsyncMock()
        trader = trader_module.Trader({}, exchange_manager)
        trader.is_enabled = True
        trader.logger = mock.Mock()

        await trader.initialize_impl()

        trader.logger.debug.assert_not_called()

    async def test_logs_enabled_on_when_lifecycle_debug_enabled(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "kraken"
        exchange_manager.is_trading = False
        exchange_manager.should_log_exchange_lifecycle_debug = mock.Mock(return_value=True)
        exchange_manager.register_trader = mock.AsyncMock()
        trader = trader_module.Trader({}, exchange_manager)
        trader.is_enabled = True
        trader.logger = mock.Mock()

        await trader.initialize_impl()

        trader.logger.debug.assert_called_once_with("Disabled on kraken")
