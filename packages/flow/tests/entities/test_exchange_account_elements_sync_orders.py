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

import octobot_flow.entities.accounts.exchange_account_elements as exchange_account_elements_module


def _order_stub(exchange_order_id: str):
    order = mock.Mock()
    order.exchange_order_id = exchange_order_id
    order.is_self_managed = mock.Mock(return_value=False)
    return order


class TestExchangeAccountElementsSyncOrdersFromExchangeManager:
    def test_includes_pending_creation_orders_with_exchange_id(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "kraken"
        open_order = _order_stub("open-order-id")
        pending_order = _order_stub("pending-order-id")
        with mock.patch(
            "octobot_flow.entities.accounts.exchange_account_elements.octobot_trading.api.get_open_orders",
            return_value=[open_order],
        ), mock.patch(
            "octobot_flow.entities.accounts.exchange_account_elements.octobot_trading.api.get_pending_creation_orders",
            return_value=[pending_order],
        ), mock.patch(
            "octobot_flow.entities.accounts.exchange_account_elements.octobot_trading.storage.orders_storage._format_order",
            side_effect=lambda order, _exchange_manager: {"exchange_order_id": order.exchange_order_id},
        ):
            elements = exchange_account_elements_module.ExchangeAccountElements()
            elements.sync_orders_from_exchange_manager(exchange_manager)

        assert len(elements.orders.open_orders) == 2
        stored_exchange_ids = {
            stored_order["exchange_order_id"] for stored_order in elements.orders.open_orders
        }
        assert stored_exchange_ids == {"open-order-id", "pending-order-id"}

    def test_deduplicates_pending_creation_when_already_open(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "kraken"
        shared_exchange_id = "shared-order-id"
        open_order = _order_stub(shared_exchange_id)
        pending_order = _order_stub(shared_exchange_id)
        with mock.patch(
            "octobot_flow.entities.accounts.exchange_account_elements.octobot_trading.api.get_open_orders",
            return_value=[open_order],
        ), mock.patch(
            "octobot_flow.entities.accounts.exchange_account_elements.octobot_trading.api.get_pending_creation_orders",
            return_value=[pending_order],
        ), mock.patch(
            "octobot_flow.entities.accounts.exchange_account_elements.octobot_trading.storage.orders_storage._format_order",
            side_effect=lambda order, _exchange_manager: {"exchange_order_id": order.exchange_order_id},
        ):
            elements = exchange_account_elements_module.ExchangeAccountElements()
            elements.sync_orders_from_exchange_manager(exchange_manager)

        assert len(elements.orders.open_orders) == 1

    def test_skips_pending_creation_without_exchange_id(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "kraken"
        open_order = _order_stub("open-only")
        pending_without_id = _order_stub(None)
        with mock.patch(
            "octobot_flow.entities.accounts.exchange_account_elements.octobot_trading.api.get_open_orders",
            return_value=[open_order],
        ), mock.patch(
            "octobot_flow.entities.accounts.exchange_account_elements.octobot_trading.api.get_pending_creation_orders",
            return_value=[pending_without_id],
        ), mock.patch(
            "octobot_flow.entities.accounts.exchange_account_elements.octobot_trading.storage.orders_storage._format_order",
            side_effect=lambda order, _exchange_manager: {"exchange_order_id": order.exchange_order_id},
        ):
            elements = exchange_account_elements_module.ExchangeAccountElements()
            elements.sync_orders_from_exchange_manager(exchange_manager)

        assert len(elements.orders.open_orders) == 1
