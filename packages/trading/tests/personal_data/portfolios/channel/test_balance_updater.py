#  Drakkar-Software OctoBot-Trading
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
from mock import patch, Mock, AsyncMock

from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests import event_loop

pytestmark = pytest.mark.asyncio


class TestBalanceUpdater:
    async def test_start(self, backtesting_trader):
        config, exchange_manager, trader = backtesting_trader
        import octobot_trading.exchange_channel as exchange_channel
        import octobot_trading.personal_data.portfolios.channel.balance_updater as balance_updater_module
        
        # Get the balance channel
        balance_channel = exchange_channel.get_chan(
            balance_updater_module.BalanceUpdater.CHANNEL_NAME,
            exchange_manager.id
        )
        
        # Create a BalanceUpdater instance
        updater = balance_updater_module.BalanceUpdater(balance_channel)
        
        # Verify initial state: temporary_expected_portfolio_update_job should not be started
        assert not updater.temporary_expected_portfolio_update_job.is_started
        
        # Verify dependencies are set up correctly
        assert updater.regular_portfolio_update_job in updater.temporary_expected_portfolio_update_job.job_dependencies
        assert updater.temporary_expected_portfolio_update_job in updater.regular_portfolio_update_job.job_dependencies
        
        # Mock both jobs' run methods
        with patch.object(updater.regular_portfolio_update_job, 'run', new=AsyncMock()) as regular_run_mock, \
             patch.object(updater.temporary_expected_portfolio_update_job, 'run', new=AsyncMock()) as temporary_run_mock:
            await updater.start()
            # Verify regular job's run is called
            regular_run_mock.assert_called_once()
            # Verify temporary job's run is NOT called (start() only starts the regular job)
            temporary_run_mock.assert_not_called()
        
        # Verify temporary_expected_portfolio_update_job is still not started after start()
        assert not updater.temporary_expected_portfolio_update_job.is_started
    
    async def test_set_expected_portfolio_update(self, backtesting_trader):
        config, exchange_manager, trader = backtesting_trader
        import octobot_trading.exchange_channel as exchange_channel
        import octobot_trading.personal_data.portfolios.channel.balance_updater as balance_updater_module
        
        # Get the balance channel
        balance_channel = exchange_channel.get_chan(
            balance_updater_module.BalanceUpdater.CHANNEL_NAME,
            exchange_manager.id
        )
        
        # Create a BalanceUpdater instance
        updater = balance_updater_module.BalanceUpdater(balance_channel)
        
        # Ensure the job is not started initially
        assert updater.temporary_expected_portfolio_update_job.is_started is False
        
        # Test setting expected portfolio update to True when not started (should start the temporary job)
        with patch.object(updater.temporary_expected_portfolio_update_job, 'run', new=AsyncMock()) as run_mock:
            await updater.set_expected_portfolio_update(True)
            run_mock.assert_called_once()
        
        # Test setting expected portfolio update to False when started (should stop the temporary job)
        # set is_started to return True
        updater.temporary_expected_portfolio_update_job.is_started = True
        with patch.object(updater.temporary_expected_portfolio_update_job, 'stop', new=Mock()) as stop_mock:
            await updater.set_expected_portfolio_update(False)
            stop_mock.assert_called_once()
        
        # Test setting expected portfolio update to True when already started (should not start again)
        # set is_started to return True
        updater.temporary_expected_portfolio_update_job.is_started = True
        with patch.object(updater.temporary_expected_portfolio_update_job, 'run', new=AsyncMock()) as run_mock:
            await updater.set_expected_portfolio_update(True)
            # Should not call run again since it's already started
            run_mock.assert_not_called()
        
        # Test setting expected portfolio update to False when not started (should not stop)
        updater.temporary_expected_portfolio_update_job.is_started = False
        with patch.object(updater.temporary_expected_portfolio_update_job, 'stop', new=Mock()) as stop_mock:
            await updater.set_expected_portfolio_update(False)
            stop_mock.assert_not_called()
