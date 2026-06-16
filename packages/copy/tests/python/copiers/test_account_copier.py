#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or
#  (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  OctoBot. If not, see <https://www.gnu.org/licenses/>.
import mock
import pytest

import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums

import octobot_copy.constants as copy_constants
import octobot_copy.copiers.spot_account_copier as spot_account_copier_module
import octobot_copy.entities as copy_entities


pytestmark = pytest.mark.asyncio


def _copied_reference_account() -> protocol_models.CopiedAccount:
    return protocol_models.CopiedAccount(
        version=copy_constants.COPIED_ACCOUNT_VERSION,
        updated_at=0.0,
        copied_assets=[],
        orders=[],
    )


def _market_rebalance_order():
    order = mock.Mock()
    order.order_type = trading_enums.TraderOrderType.BUY_MARKET
    return order


def _limit_rebalance_order():
    order = mock.Mock()
    order.order_type = trading_enums.TraderOrderType.BUY_LIMIT
    return order


class TestAccountCopierCopyAccount:
    async def _run_copy_account(
        self,
        *,
        should_rebalance: bool,
        rebalance_orders: list,
        grace_identified: bool,
    ):
        reference_account = _copied_reference_account()
        exchange_interface = mock.MagicMock()
        exchange_interface.exchange_name = "bitmart"
        exchange_interface.portfolio = mock.MagicMock()
        exchange_interface.portfolio.refresh_portfolio = mock.AsyncMock()
        copy_settings = copy_entities.AccountCopySettings()

        copier = spot_account_copier_module.SpotAccountCopier(
            reference_account,
            exchange_interface,
            copy_settings,
        )
        synchronizer = mock.Mock()
        synchronizer.is_mirrored_orphan_grace_identified_for_reference_orders = mock.Mock(
            return_value=grace_identified
        )
        synchronizer.abort_mirrored_orphan_grace = mock.Mock()
        synchronizer.synchronize = mock.AsyncMock(return_value=[])
        copier._orders_synchronizer = synchronizer

        rebalancer = mock.Mock()
        copier._prepare_rebalance_plan = mock.AsyncMock(
            return_value=(rebalancer, should_rebalance, {})
        )
        copier._run_rebalance = mock.AsyncMock(return_value=rebalance_orders)
        copier._resync_if_mirrored_open_order_grace_period_elapsed = mock.AsyncMock()
        copier._orders_synchronizer.cancel_orders_pending_synchronization = mock.AsyncMock(return_value=0)
        copier._orders_synchronizer.is_mirrored_orphan_grace_blocking_rebalance = mock.Mock(return_value=False)

        await copier.copy_account()
        return synchronizer

    async def test_bypasses_grace_after_market_rebalance_when_grace_identified(self):
        synchronizer = await self._run_copy_account(
            should_rebalance=True,
            rebalance_orders=[_market_rebalance_order()],
            grace_identified=True,
        )
        synchronizer.abort_mirrored_orphan_grace.assert_called_once()
        synchronizer.synchronize.assert_awaited_once()

    async def test_does_not_bypass_after_market_rebalance_when_grace_not_identified(self):
        synchronizer = await self._run_copy_account(
            should_rebalance=True,
            rebalance_orders=[_market_rebalance_order()],
            grace_identified=False,
        )
        synchronizer.abort_mirrored_orphan_grace.assert_not_called()

    async def test_does_not_bypass_grace_when_no_rebalance_orders(self):
        synchronizer = await self._run_copy_account(
            should_rebalance=False,
            rebalance_orders=[],
            grace_identified=True,
        )
        synchronizer.abort_mirrored_orphan_grace.assert_not_called()

    async def test_does_not_bypass_grace_when_rebalance_has_no_market_orders(self):
        synchronizer = await self._run_copy_account(
            should_rebalance=True,
            rebalance_orders=[_limit_rebalance_order()],
            grace_identified=True,
        )
        synchronizer.abort_mirrored_orphan_grace.assert_not_called()
