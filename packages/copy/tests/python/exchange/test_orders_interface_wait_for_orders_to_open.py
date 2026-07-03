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
import logging

import mock
import pytest

import octobot_trading.enums as trading_enums

import octobot_copy.exchange.orders as orders_module

pytestmark = pytest.mark.asyncio

_EXCHANGE_ID_COLUMN = trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value


def _orders_interface_with_exchange():
    exchange_manager = mock.Mock()
    exchange_manager.exchange_name = "kraken"
    exchange_manager.exchange_personal_data.orders_manager.pending_creation_orders = []
    exchange = mock.AsyncMock()
    exchange_manager.exchange = exchange
    return orders_module.OrdersInterface(exchange_manager, None), exchange_manager, exchange


def _pending_order_stub(*, exchange_order_id: str, symbol: str = "BTC/USDC"):
    order = mock.Mock()
    order.symbol = symbol
    order.exchange_order_id = exchange_order_id
    order.order_id = f"local-{exchange_order_id}"
    pending = True

    def is_pending_creation():
        return pending

    async def on_open(**_kwargs):
        nonlocal pending
        pending = False

    order.is_pending_creation = is_pending_creation
    order.on_open = mock.AsyncMock(side_effect=on_open)
    order.update_from_raw = mock.AsyncMock()
    return order


class TestOrdersInterfaceWaitForOrdersToOpen:
    async def test_returns_immediately_when_no_orders(self):
        orders_interface, _, _ = _orders_interface_with_exchange()
        await orders_interface.wait_for_orders_to_open([], "BTC/USDC")

    async def test_promotes_pending_orders_found_on_exchange(self):
        orders_interface, exchange_manager, exchange = _orders_interface_with_exchange()
        order = _pending_order_stub(exchange_order_id="ex-open-1")
        exchange_manager.exchange_personal_data.orders_manager.pending_creation_orders = [order]

        async def get_open_orders(symbol=None, **kwargs):
            return [{_EXCHANGE_ID_COLUMN: "ex-open-1"}]

        exchange.get_open_orders = get_open_orders

        async def promote_side_effect(promoted_order):
            promoted_order.is_pending_creation = lambda: False

        with mock.patch.object(
            orders_interface,
            "_promote_pending_order_to_open",
            mock.AsyncMock(side_effect=promote_side_effect),
        ) as promote_mock:
            await orders_interface.wait_for_orders_to_open(
                [order],
                "BTC/USDC",
                poll_interval=0.01,
                timeout=1,
            )
        promote_mock.assert_awaited_once_with(order)

    async def test_does_not_call_update_from_raw_when_promoting(self):
        orders_interface, exchange_manager, exchange = _orders_interface_with_exchange()
        order = _pending_order_stub(exchange_order_id="ex-open-2")
        exchange_manager.exchange_personal_data.orders_manager.pending_creation_orders = [order]
        exchange.get_open_orders = mock.AsyncMock(
            return_value=[{_EXCHANGE_ID_COLUMN: "ex-open-2"}],
        )
        await orders_interface.wait_for_orders_to_open(
            [order],
            "BTC/USDC",
            poll_interval=0.01,
            timeout=1,
        )
        order.on_open.assert_awaited()
        order.update_from_raw.assert_not_awaited()

    async def test_logs_warning_on_timeout(self, caplog):
        orders_interface, _, exchange = _orders_interface_with_exchange()
        order = _pending_order_stub(exchange_order_id="ex-still-pending")
        exchange.get_open_orders = mock.AsyncMock(return_value=[])
        with caplog.at_level(logging.WARNING):
            await orders_interface.wait_for_orders_to_open(
                [order],
                "BTC/USDC",
                poll_interval=0.01,
                timeout=0.05,
            )
        assert any(
            "Timed out waiting for 1 mirrored order(s) to open on kraken" in record.message
            for record in caplog.records
        )

    async def test_logs_start_and_completion_when_orders_open(self, caplog):
        orders_interface, exchange_manager, exchange = _orders_interface_with_exchange()
        order = _pending_order_stub(exchange_order_id="ex-open-3")
        exchange_manager.exchange_personal_data.orders_manager.pending_creation_orders = [order]
        exchange.get_open_orders = mock.AsyncMock(
            return_value=[{_EXCHANGE_ID_COLUMN: "ex-open-3"}],
        )
        with caplog.at_level(logging.INFO):
            await orders_interface.wait_for_orders_to_open(
                [order],
                "BTC/USDC",
                poll_interval=0.01,
                timeout=1,
            )
        info_messages = [record.message for record in caplog.records if record.levelno == logging.INFO]
        assert any("Waiting for 1 mirrored order(s) on BTC/USDC to open on kraken" in message for message in info_messages)
        assert any("All 1 mirrored order(s) open on kraken for BTC/USDC after" in message for message in info_messages)

    async def test_logs_promotion_progress(self, caplog):
        orders_interface, exchange_manager, exchange = _orders_interface_with_exchange()
        first_order = _pending_order_stub(exchange_order_id="ex-open-a")
        second_order = _pending_order_stub(exchange_order_id="ex-open-b")
        exchange_manager.exchange_personal_data.orders_manager.pending_creation_orders = [
            first_order,
            second_order,
        ]
        poll_count = 0

        async def get_open_orders(symbol=None, **kwargs):
            nonlocal poll_count
            poll_count += 1
            if poll_count == 1:
                return [{_EXCHANGE_ID_COLUMN: "ex-open-a"}]
            return [{_EXCHANGE_ID_COLUMN: "ex-open-b"}]

        exchange.get_open_orders = get_open_orders
        with caplog.at_level(logging.INFO):
            await orders_interface.wait_for_orders_to_open(
                [first_order, second_order],
                "BTC/USDC",
                poll_interval=0.01,
                timeout=1,
            )
        info_messages = [record.message for record in caplog.records if record.levelno == logging.INFO]
        assert any(
            "Promoted 1 mirrored order(s) to open on kraken for BTC/USDC (1/2 open, 1 remaining)" in message
            for message in info_messages
        )
