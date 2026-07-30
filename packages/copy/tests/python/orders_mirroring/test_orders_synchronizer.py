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
import asyncio
import contextlib
import decimal
import logging
import time
import typing

import mock

import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data.orders.order_util as order_util

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_copy.orders_mirroring.mirrored_quantity_compute_result as mirrored_quantity_compute_result
import octobot_copy.orders_mirroring.orders_synchronizer as orders_synchronizer_module


def _copied_account(
    *,
    updated_at: typing.Optional[float] = None,
    copied_assets: typing.Optional[list[protocol_models.CopiedAsset]] = None,
    orders: typing.Optional[list[protocol_models.Order]] = None,
    historical_snapshots: typing.Optional[list[protocol_models.CopiedAccount]] = None,
) -> protocol_models.CopiedAccount:
    return protocol_models.CopiedAccount(
        version=copy_constants.COPIED_ACCOUNT_VERSION,
        updated_at=updated_at if updated_at is not None else time.time(),
        copied_assets=copied_assets or [],
        orders=orders,
        historical_snapshots=historical_snapshots,
    )



def _eth_usdt_pair_assets(
    *,
    eth_ratio: float = 0.25,
    usdt_ratio: float = 0.5,
    eth_value: float = 1.0,
    usdt_value: float = 10000.0,
) -> list[protocol_models.CopiedAsset]:
    return [
        protocol_models.CopiedAsset(name="ETH", total=eth_value, available=eth_value, ratio=eth_ratio),
        protocol_models.CopiedAsset(name="USDT", total=usdt_value, available=usdt_value, ratio=usdt_ratio),
    ]


@contextlib.asynccontextmanager
async def _passthrough_mirror_sync_available_updates():
    yield


def _exchange_interface_stub(*, currency_totals: dict[str, decimal.Decimal], market_price: decimal.Decimal):
    exchange_interface = mock.MagicMock()
    exchange_interface.portfolio.reference_market = "USDT"

    def currency_total(currency: str) -> decimal.Decimal:
        return currency_totals[currency]

    exchange_interface.portfolio.get_currency_portfolio_total = currency_total
    exchange_interface.market.get_potentially_outdated_price = mock.Mock(
        return_value=(market_price, False)
    )
    return exchange_interface


def _replicable_buy_limit_order(
    *,
    order_id: str = "ref-late-1",
    amount: decimal.Decimal = decimal.Decimal("1"),
    price: decimal.Decimal = decimal.Decimal("2000"),
    created_ts: float | None = None,
) -> protocol_models.Order:
    created_ts = created_ts if created_ts is not None else time.time()
    return protocol_models.Order(
        id=order_id,
        symbol="ETH/USDT",
        price=float(price),
        quantity=float(amount),
        filled=0.0,
        exchange_id="ex",
        side=protocol_models.Side.BUY,
        type=protocol_models.OrderType.LIMIT,
        trigger_above=False,
        reduce_only=False,
        is_active=True,
        status=protocol_models.OrderStatus.OPEN,
        created_at=timestamp_util.utc_datetime_from_timestamp(created_ts),
    )


def _replicable_buy_market_order(
    *,
    order_id: str = "ref-market-1",
    amount: decimal.Decimal = decimal.Decimal("1"),
    price: decimal.Decimal = decimal.Decimal("2000"),
) -> protocol_models.Order:
    return protocol_models.Order(
        id=order_id,
        symbol="ETH/USDT",
        price=float(price),
        quantity=float(amount),
        filled=0.0,
        exchange_id="ex",
        side=protocol_models.Side.BUY,
        type=protocol_models.OrderType.MARKET,
        trigger_above=False,
        reduce_only=False,
        is_active=True,
        status=protocol_models.OrderStatus.OPEN,
        created_at=timestamp_util.utc_datetime_from_timestamp(time.time()),
    )


class TestMarketOrderExclusion:
    def test_replicable_reference_orders_omit_market_include_limit(self):
        limit_order = _replicable_buy_limit_order(order_id="limit-1")
        market_order = _replicable_buy_market_order(order_id="market-1")
        reference = _copied_account(
            orders=[market_order, limit_order],
        )
        exchange_if = mock.MagicMock()
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(),
        )
        replicable = synchronizer._get_replicable_reference_orders()
        assert replicable == [limit_order]

    def test_mirrored_orphan_open_orders_excludes_copier_market_orders(self):
        reference = _copied_account()
        exchange_if = mock.MagicMock()
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(),
        )
        market_mirror = mock.Mock()
        market_mirror.tag = copy_constants.MIRRORED_ORDER_TAG
        market_mirror.order_id = "not-in-reference"
        market_mirror.order_type = trading_enums.TraderOrderType.BUY_MARKET
        limit_mirror = mock.Mock()
        limit_mirror.tag = copy_constants.MIRRORED_ORDER_TAG
        limit_mirror.order_id = "orphan-limit"
        limit_mirror.order_type = trading_enums.TraderOrderType.BUY_LIMIT
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[market_mirror, limit_mirror])
        orphans = synchronizer._mirrored_orphan_open_orders(set())
        assert orphans == [limit_mirror]


class TestMirroredOrderSelfLockCreditCompute:
    """open_mirrored_order credits this line's locked funds so repeat sync does not false quantity mismatch."""

    @staticmethod
    def _mirrored_sell_order(
        *,
        order_id: str,
        symbol: str,
        locked_quantity: decimal.Decimal,
        price: decimal.Decimal,
    ):
        order = mock.Mock()
        order.order_id = order_id
        order.tag = copy_constants.MIRRORED_ORDER_TAG
        order.side = trading_enums.TradeOrderSide.SELL
        order.symbol = symbol
        order.currency = symbol.split("/")[0]
        order.origin_price = price
        order.is_filled = mock.Mock(return_value=False)
        order.get_locked_quantity = mock.Mock(return_value=locked_quantity)
        order.get_computed_fee = mock.Mock(return_value=None)
        return order

    @staticmethod
    def _exchange_interface_for_compute(
        *,
        total_symbol: decimal.Decimal,
        total_market: decimal.Decimal,
        available_symbol: decimal.Decimal,
        available_market: decimal.Decimal,
        mark_price: decimal.Decimal,
        open_mirrored_sell_orders: typing.Optional[list] = None,
    ):
        symbol_market = mock.Mock()
        market_quantity_total = total_market / mark_price if mark_price else trading_constants.ZERO
        market_quantity_available = (
            available_market / mark_price if mark_price else trading_constants.ZERO
        )
        total_row = (
            total_symbol,
            total_market,
            market_quantity_total,
            mark_price,
            symbol_market,
        )
        available_row = (
            available_symbol,
            available_market,
            market_quantity_available,
            mark_price,
            symbol_market,
        )
        exchange_if = mock.MagicMock()
        # Each _compute_mirrored_quantity_type_and_price calls get_pre_order_data twice (TOTAL then AVAILABLE).
        exchange_if.orders.get_pre_order_data = mock.AsyncMock(
            side_effect=[total_row, available_row, total_row, available_row]
        )
        exchange_if.orders.check_and_adapt_order_details_if_necessary = mock.Mock(
            side_effect=lambda symbol, quantity, limit_price: ([(quantity, limit_price)], symbol_market)
        )
        exchange_if.orders.get_order_locked_amount = order_util.get_order_locked_amount
        exchange_if.orders.get_open_orders = mock.Mock(
            return_value=open_mirrored_sell_orders or []
        )
        exchange_if.market.is_market_open_for_order_type = mock.Mock(return_value=True)
        return exchange_if

    def test_buy_open_mirrored_order_adds_locked_quote_to_cap(self):
        mark_price = decimal.Decimal("2000")
        exchange_if = self._exchange_interface_for_compute(
            total_symbol=decimal.Decimal("2"),
            total_market=decimal.Decimal("10000"),
            available_symbol=decimal.Decimal("0.25"),
            available_market=decimal.Decimal("500"),
            mark_price=mark_price,
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            _copied_account(),
            exchange_if,
            copy_entities.AccountCopySettings(),
        )
        open_buy = mock.Mock()
        open_buy.side = trading_enums.TradeOrderSide.BUY
        open_buy.symbol = "ETH/USDT"
        open_buy.origin_price = mark_price
        open_buy.get_locked_quantity = mock.Mock(return_value=decimal.Decimal("0.75"))
        open_buy.get_computed_fee = mock.Mock(return_value=None)

        async def run_compute(open_order):
            return await synchronizer._compute_mirrored_quantity_type_and_price(
                "ETH/USDT",
                trading_enums.TradeOrderSide.BUY,
                decimal.Decimal("1"),
                mark_price,
                trading_enums.TraderOrderType.BUY_LIMIT,
                open_mirrored_order=open_order,
            )

        ideal_without = asyncio.run(run_compute(None)).ideal_quantity
        ideal_with = asyncio.run(run_compute(open_buy)).ideal_quantity
        assert ideal_without == decimal.Decimal("0.25")
        assert ideal_with == decimal.Decimal("1")

    def test_sell_open_mirrored_order_adds_locked_base_to_cap(self):
        mark_price = decimal.Decimal("2000")
        open_sell = self._mirrored_sell_order(
            order_id="open-sell",
            symbol="ETH/USDT",
            locked_quantity=decimal.Decimal("1"),
            price=mark_price,
        )
        sibling_sell = self._mirrored_sell_order(
            order_id="sibling-sell",
            symbol="ETH/USDT",
            locked_quantity=decimal.Decimal("8.95"),
            price=mark_price,
        )
        exchange_if = self._exchange_interface_for_compute(
            total_symbol=decimal.Decimal("10"),
            total_market=decimal.Decimal("10000"),
            available_symbol=decimal.Decimal("0.05"),
            available_market=decimal.Decimal("500"),
            mark_price=mark_price,
            open_mirrored_sell_orders=[open_sell, sibling_sell],
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            _copied_account(),
            exchange_if,
            copy_entities.AccountCopySettings(),
        )

        async def run_compute(open_order, scaled):
            return await synchronizer._compute_mirrored_quantity_type_and_price(
                "ETH/USDT",
                trading_enums.TradeOrderSide.SELL,
                scaled,
                mark_price,
                trading_enums.TraderOrderType.SELL_LIMIT,
                open_mirrored_order=open_order,
            )

        scaled = decimal.Decimal("2")
        ideal_without = asyncio.run(run_compute(None, scaled)).ideal_quantity
        ideal_with = asyncio.run(run_compute(open_sell, scaled)).ideal_quantity
        assert ideal_without == decimal.Decimal("0.05")
        assert ideal_with == decimal.Decimal("1.05")

    def test_new_sell_caps_to_total_minus_sibling_locked_base(self):
        mark_price = decimal.Decimal("60300")
        total_btc = decimal.Decimal("0.00753")
        available_btc = decimal.Decimal("0.00068")
        sibling_locked_btc = total_btc - available_btc
        sibling_sell = self._mirrored_sell_order(
            order_id="sibling-sell",
            symbol="BTC/USDT",
            locked_quantity=sibling_locked_btc,
            price=decimal.Decimal("62188"),
        )
        exchange_if = self._exchange_interface_for_compute(
            total_symbol=total_btc,
            total_market=decimal.Decimal("500"),
            available_symbol=available_btc,
            available_market=decimal.Decimal("15"),
            mark_price=mark_price,
            open_mirrored_sell_orders=[sibling_sell],
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            _copied_account(),
            exchange_if,
            copy_entities.AccountCopySettings(),
        )

        async def run_compute():
            return await synchronizer._compute_mirrored_quantity_type_and_price(
                "BTC/USDT",
                trading_enums.TradeOrderSide.SELL,
                decimal.Decimal("0.00074"),
                decimal.Decimal("61188"),
                trading_enums.TraderOrderType.SELL_LIMIT,
                open_mirrored_order=None,
            )

        assert asyncio.run(run_compute()).ideal_quantity == available_btc


class TestMirroredOrderSkipLogging:
    @staticmethod
    def _configure_exchange_interface(exchange_if: mock.MagicMock) -> None:
        exchange_if.portfolio.reference_market = "USDT"
        exchange_if.market.get_potentially_outdated_price = mock.Mock(
            return_value=(decimal.Decimal("2000"), False)
        )
        exchange_if.portfolio.get_currency_portfolio_total = mock.Mock(
            side_effect=lambda currency: (
                decimal.Decimal("10000") if currency == "USDT" else decimal.Decimal("1")
            )
        )

    @staticmethod
    def _buy_reference_with_usdt_total(usdt_total: float) -> protocol_models.CopiedAccount:
        return _copied_account(
            copied_assets=[
                protocol_models.CopiedAsset(name="ETH", total=1.0, available=1.0, ratio=0.5),
                protocol_models.CopiedAsset(
                    name="USDT",
                    total=usdt_total,
                    available=usdt_total,
                    ratio=0.5,
                ),
            ],
            orders=[],
        )

    def test_logs_when_scaled_quantity_unavailable(self, caplog):
        caplog.set_level(logging.WARNING)
        limit_order = _replicable_buy_limit_order(order_id="order-scale-fail")
        reference = self._buy_reference_with_usdt_total(0.0)
        exchange_if = mock.MagicMock()
        self._configure_exchange_interface(exchange_if)
        exchange_if.portfolio.get_currency_portfolio_total = mock.Mock(
            return_value=decimal.Decimal("1000")
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])

        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(),
        )

        async def run_upsert():
            return await synchronizer._upsert_mirrored_reference_order(limit_order)

        _, _, _, replication_failure = asyncio.run(run_upsert())
        assert replication_failure is not None
        assert replication_failure.short_reason == "zero_scaled_quantity"
        assert any(
            "zero_scaled_quantity" in record.message and "reference_total=0" in record.message
            for record in caplog.records
        )

    def test_logs_when_buy_capped_to_zero_by_available_quote(self, caplog):
        caplog.set_level(logging.WARNING)
        limit_order = _replicable_buy_limit_order(order_id="order-quote-fail")
        reference = self._buy_reference_with_usdt_total(10000.0)
        mark_price = decimal.Decimal("2000")
        symbol_market = mock.Mock()
        total_row = (
            decimal.Decimal("1"),
            decimal.Decimal("10000"),
            decimal.Decimal("5"),
            mark_price,
            symbol_market,
        )
        available_row = (
            decimal.Decimal("1"),
            trading_constants.ZERO,
            trading_constants.ZERO,
            mark_price,
            symbol_market,
        )
        exchange_if = mock.MagicMock()
        self._configure_exchange_interface(exchange_if)
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        exchange_if.orders.get_pre_order_data = mock.AsyncMock(
            side_effect=[total_row, available_row]
        )
        exchange_if.orders.check_and_adapt_order_details_if_necessary = mock.Mock(
            side_effect=lambda symbol, quantity, limit_price: ([(quantity, limit_price)], symbol_market)
        )
        exchange_if.market.is_market_open_for_order_type = mock.Mock(return_value=True)

        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(),
        )

        async def run_upsert():
            return await synchronizer._upsert_mirrored_reference_order(limit_order)

        _, _, _, replication_failure = asyncio.run(run_upsert())
        assert replication_failure is not None
        assert replication_failure.short_reason == "insufficient_quote"
        assert any(
            "insufficient_quote" in record.message and "available_market_holding=0" in record.message
            for record in caplog.records
        )

    def test_synchronize_summary_lists_failed_replications_with_reason(self, caplog):
        caplog.set_level(logging.INFO)
        first_order = _replicable_buy_limit_order(
            order_id="11111111-1111-1111-1111-111111111111",
            price=decimal.Decimal("50745.57"),
        )
        second_order = _replicable_buy_limit_order(
            order_id="22222222-2222-2222-2222-222222222222",
            price=decimal.Decimal("49245.57"),
        )
        reference = _copied_account(
            copied_assets=[
                protocol_models.CopiedAsset(name="ETH", total=1.0, available=1.0, ratio=0.5),
                protocol_models.CopiedAsset(name="USDT", total=500.0, available=500.0, ratio=0.5),
            ],
            orders=[first_order, second_order],
        )
        mark_price = decimal.Decimal("60000")
        symbol_market = mock.Mock()

        total_row = (
            decimal.Decimal("1"),
            decimal.Decimal("169"),
            decimal.Decimal("0.002"),
            mark_price,
            symbol_market,
        )
        available_row = (
            decimal.Decimal("1"),
            trading_constants.ZERO,
            trading_constants.ZERO,
            mark_price,
            symbol_market,
        )
        pre_order_data_rows = [total_row, available_row] * 4

        exchange_if = mock.MagicMock()
        self._configure_exchange_interface(exchange_if)
        exchange_if.portfolio.get_currency_portfolio_total = mock.Mock(
            side_effect=lambda currency: decimal.Decimal("169") if currency == "USDT" else decimal.Decimal("1")
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        exchange_if.orders.get_pre_order_data = mock.AsyncMock(side_effect=pre_order_data_rows)
        exchange_if.orders.check_and_adapt_order_details_if_necessary = mock.Mock(
            side_effect=lambda symbol, quantity, limit_price: ([(quantity, limit_price)], symbol_market)
        )
        exchange_if.market.is_market_open_for_order_type = mock.Mock(return_value=True)
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates

        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(),
        )
        synchronizer.cancel_orders_pending_synchronization = mock.AsyncMock(return_value=0)

        asyncio.run(synchronizer.synchronize())

        completion_logs = [
            record.message
            for record in caplog.records
            if record.message.startswith("Order mirror completed:")
        ]
        assert len(completion_logs) == 1
        completion_message = completion_logs[0]
        assert "Failed to replicate 2 order(s):" in completion_message
        assert "buy ETH/USDT @ 50745.57 [11111111-1111-1111-1111-111111111111] (insufficient_quote)" in completion_message
        assert "buy ETH/USDT @ 49245.57 [22222222-2222-2222-2222-222222222222] (insufficient_quote)" in completion_message


class TestOrdersSynchronizerWaitForMirroredOrdersOpen:
    def _synchronizer_with_auto_sync(self, auto_sync_enabled: bool):
        reference = _copied_account(
            copied_assets=_eth_usdt_pair_assets(),
            orders=[_replicable_buy_limit_order()],
        )
        exchange_if = _exchange_interface_stub(
            currency_totals={
                "ETH": decimal.Decimal("1"),
                "USDT": decimal.Decimal("10000"),
            },
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        exchange_if.orders.automatically_synchronize_orders = mock.Mock(return_value=auto_sync_enabled)
        exchange_if.orders.wait_for_orders_to_open = mock.AsyncMock()
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(),
        )
        return synchronizer, exchange_if

    def test_waits_for_created_orders_when_auto_sync_disabled(self):
        synchronizer, exchange_if = self._synchronizer_with_auto_sync(False)
        created_order = mock.Mock()
        created_order.symbol = "ETH/USDT"
        with mock.patch.object(
            synchronizer,
            "cancel_orders_pending_synchronization",
            mock.AsyncMock(return_value=0),
        ), mock.patch.object(
            synchronizer,
            "_upsert_mirrored_reference_order",
            mock.AsyncMock(return_value=([created_order], 0, 0, None)),
        ):
            created = asyncio.run(synchronizer.synchronize())

        assert created == [created_order]
        exchange_if.orders.wait_for_orders_to_open.assert_awaited_once_with(
            [created_order],
            "ETH/USDT",
        )

    def test_skips_wait_when_auto_sync_enabled(self):
        synchronizer, exchange_if = self._synchronizer_with_auto_sync(True)
        created_order = mock.Mock()
        created_order.symbol = "ETH/USDT"
        with mock.patch.object(
            synchronizer,
            "cancel_orders_pending_synchronization",
            mock.AsyncMock(return_value=0),
        ), mock.patch.object(
            synchronizer,
            "_upsert_mirrored_reference_order",
            mock.AsyncMock(return_value=([created_order], 0, 0, None)),
        ):
            created = asyncio.run(synchronizer.synchronize())

        assert created == [created_order]
        exchange_if.orders.wait_for_orders_to_open.assert_not_awaited()

    def test_count_invariant_runs_after_wait_when_auto_sync_disabled(self):
        synchronizer, exchange_if = self._synchronizer_with_auto_sync(False)
        created_order = mock.Mock()
        created_order.symbol = "ETH/USDT"
        call_order: list[str] = []

        async def wait_side_effect(orders, symbol):
            call_order.append("wait")

        def invariant_side_effect(replicable):
            call_order.append("invariant")

        exchange_if.orders.wait_for_orders_to_open = mock.AsyncMock(side_effect=wait_side_effect)
        with mock.patch.object(
            synchronizer,
            "cancel_orders_pending_synchronization",
            mock.AsyncMock(return_value=0),
        ), mock.patch.object(
            synchronizer,
            "_upsert_mirrored_reference_order",
            mock.AsyncMock(return_value=([created_order], 0, 0, None)),
        ), mock.patch.object(
            synchronizer,
            "_check_open_limit_order_count_invariant",
            side_effect=invariant_side_effect,
        ):
            asyncio.run(synchronizer.synchronize())
        assert call_order == ["wait", "invariant"]

    def test_count_invariant_runs_when_wait_skipped(self):
        synchronizer, exchange_if = self._synchronizer_with_auto_sync(True)
        created_order = mock.Mock()
        created_order.symbol = "ETH/USDT"
        call_order: list[str] = []

        def invariant_side_effect(replicable):
            call_order.append("invariant")

        with mock.patch.object(
            synchronizer,
            "cancel_orders_pending_synchronization",
            mock.AsyncMock(return_value=0),
        ), mock.patch.object(
            synchronizer,
            "_upsert_mirrored_reference_order",
            mock.AsyncMock(return_value=([created_order], 0, 0, None)),
        ), mock.patch.object(
            synchronizer,
            "_check_open_limit_order_count_invariant",
            side_effect=invariant_side_effect,
        ):
            asyncio.run(synchronizer.synchronize())
        exchange_if.orders.wait_for_orders_to_open.assert_not_awaited()
        assert call_order == ["invariant"]


def _btc_usdc_buy_limit_reference_order(
    *,
    order_id: str,
    amount: decimal.Decimal = decimal.Decimal("0.0001"),
    price: decimal.Decimal = decimal.Decimal("59326.7"),
) -> protocol_models.Order:
    return protocol_models.Order(
        id=order_id,
        symbol="BTC/USDC",
        price=float(price),
        quantity=float(amount),
        filled=0.0,
        exchange_id="ref-ex",
        side=protocol_models.Side.BUY,
        type=protocol_models.OrderType.LIMIT,
        trigger_above=False,
        reduce_only=False,
        is_active=True,
        status=protocol_models.OrderStatus.OPEN,
        created_at=timestamp_util.utc_datetime_from_timestamp(time.time()),
    )


def _open_limit_order_stub(
    *,
    order_id: str,
    exchange_order_id: str,
    symbol: str = "BTC/USDC",
    side=trading_enums.TradeOrderSide.BUY,
    quantity: decimal.Decimal,
    price: decimal.Decimal,
    tag: str | None = None,
    order_type=trading_enums.TraderOrderType.BUY_LIMIT,
):
    order = mock.Mock()
    order.order_id = order_id
    order.exchange_order_id = exchange_order_id
    order.symbol = symbol
    order.side = side
    order.origin_quantity = quantity
    order.origin_price = price
    order.order_type = order_type
    order.tag = tag
    return order


def _synchronizer_with_open_orders(
    *,
    reference_orders: list[protocol_models.Order],
    open_orders: list,
    currency_totals: dict[str, decimal.Decimal] | None = None,
) -> tuple[orders_synchronizer_module.OrdersSynchronizer, mock.MagicMock]:
    currency_totals = currency_totals or {
        "BTC": decimal.Decimal("0.01"),
        "USDC": decimal.Decimal("10000"),
    }
    reference = _copied_account(
        copied_assets=[
            protocol_models.CopiedAsset(name="BTC", total=1.0, available=1.0, ratio=0.5),
            protocol_models.CopiedAsset(name="USDC", total=10000.0, available=10000.0, ratio=0.5),
        ],
        orders=reference_orders,
    )
    exchange_if = _exchange_interface_stub(
        currency_totals=currency_totals,
        market_price=decimal.Decimal("59326.7"),
    )
    exchange_if.orders.get_open_orders = mock.Mock(return_value=open_orders)
    orders_manager = mock.Mock()
    exchange_if.orders._exchange_manager = mock.Mock()
    exchange_if.orders._exchange_manager.exchange_personal_data.orders_manager = orders_manager
    synchronizer = orders_synchronizer_module.OrdersSynchronizer(
        reference,
        exchange_if,
        copy_entities.AccountCopySettings(),
    )
    return synchronizer, exchange_if


class TestOpenOrdersMatchingSymbolSidePrice:
    def test_matches_limit_order_within_price_tolerance(self):
        reference_price = decimal.Decimal("59326.7")
        matching_order = _open_limit_order_stub(
            order_id="wrong-bot-id",
            exchange_order_id="OGE3T6-NDOIV-LR6MZI",
            quantity=decimal.Decimal("0.0001"),
            price=reference_price,
        )
        synchronizer, _exchange_if = _synchronizer_with_open_orders(
            reference_orders=[],
            open_orders=[matching_order],
        )
        candidates = synchronizer._open_orders_matching_symbol_side_price(
            "BTC/USDC",
            trading_enums.TradeOrderSide.BUY,
            reference_price,
            trading_enums.TraderOrderType.BUY_LIMIT,
        )
        assert candidates == [matching_order]

    def test_excludes_wrong_price(self):
        reference_price = decimal.Decimal("59326.7")
        wrong_price_order = _open_limit_order_stub(
            order_id="wrong-bot-id",
            exchange_order_id="OTHER-TXID",
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("58326.7"),
        )
        synchronizer, _exchange_if = _synchronizer_with_open_orders(
            reference_orders=[],
            open_orders=[wrong_price_order],
        )
        candidates = synchronizer._open_orders_matching_symbol_side_price(
            "BTC/USDC",
            trading_enums.TradeOrderSide.BUY,
            reference_price,
            trading_enums.TraderOrderType.BUY_LIMIT,
        )
        assert candidates == []

    def test_excludes_opposite_side(self):
        reference_price = decimal.Decimal("59326.7")
        sell_order = _open_limit_order_stub(
            order_id="sell-id",
            exchange_order_id="SELL-TXID",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.0001"),
            price=reference_price,
            order_type=trading_enums.TraderOrderType.SELL_LIMIT,
        )
        synchronizer, _exchange_if = _synchronizer_with_open_orders(
            reference_orders=[],
            open_orders=[sell_order],
        )
        candidates = synchronizer._open_orders_matching_symbol_side_price(
            "BTC/USDC",
            trading_enums.TradeOrderSide.BUY,
            reference_price,
            trading_enums.TraderOrderType.BUY_LIMIT,
        )
        assert candidates == []

    def test_excludes_market_orders(self):
        reference_price = decimal.Decimal("59326.7")
        market_order = _open_limit_order_stub(
            order_id="market-id",
            exchange_order_id="MARKET-TXID",
            quantity=decimal.Decimal("0.0001"),
            price=reference_price,
            order_type=trading_enums.TraderOrderType.BUY_MARKET,
        )
        synchronizer, _exchange_if = _synchronizer_with_open_orders(
            reference_orders=[],
            open_orders=[market_order],
        )
        candidates = synchronizer._open_orders_matching_symbol_side_price(
            "BTC/USDC",
            trading_enums.TradeOrderSide.BUY,
            reference_price,
            trading_enums.TraderOrderType.BUY_LIMIT,
        )
        assert candidates == []


class TestMapUnmappedOpenOrderForReference:
    def test_returns_none_when_no_candidates(self):
        reference_order = _btc_usdc_buy_limit_reference_order(order_id="28c1394b-dcb7-4f90-8878-4a61827471ca")
        synchronizer, _exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[],
        )
        mapped = asyncio.run(
            synchronizer._map_unmapped_open_order_for_reference(
                reference_order=reference_order,
                reference_order_id=str(reference_order.id),
                side=trading_enums.TradeOrderSide.BUY,
                trader_order_type=trading_enums.TraderOrderType.BUY_LIMIT,
                order_target_price=decimal.Decimal("59326.7"),
                active_reference_ids={str(reference_order.id)},
                scaled_reference_quantity=decimal.Decimal("0.0001"),
            )
        )
        assert mapped is None

    def test_relinks_single_unmapped_candidate(self):
        reference_order = _btc_usdc_buy_limit_reference_order(order_id="28c1394b-dcb7-4f90-8878-4a61827471ca")
        open_order = _open_limit_order_stub(
            order_id="stale-bot-id",
            exchange_order_id="OGE3T6-NDOIV-LR6MZI",
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[open_order],
        )
        mapped = asyncio.run(
            synchronizer._map_unmapped_open_order_for_reference(
                reference_order=reference_order,
                reference_order_id=str(reference_order.id),
                side=trading_enums.TradeOrderSide.BUY,
                trader_order_type=trading_enums.TraderOrderType.BUY_LIMIT,
                order_target_price=decimal.Decimal("59326.7"),
                active_reference_ids={str(reference_order.id)},
                scaled_reference_quantity=decimal.Decimal("0.0001"),
            )
        )
        assert mapped is open_order
        assert open_order.order_id == str(reference_order.id)
        exchange_if.orders._exchange_manager.exchange_personal_data.orders_manager.replace_order.assert_called_once_with(
            "stale-bot-id",
            open_order,
        )

    def test_ambiguous_candidates_relinks_one_and_cancels_extras(self, caplog):
        caplog.set_level(logging.WARNING)
        reference_order = _btc_usdc_buy_limit_reference_order(order_id="28c1394b-dcb7-4f90-8878-4a61827471ca")
        first_candidate = _open_limit_order_stub(
            order_id="first-bot-id",
            exchange_order_id="O7GDOQ-5ALJT-5QPQE4",
            quantity=decimal.Decimal("0.00009"),
            price=decimal.Decimal("59326.7"),
        )
        second_candidate = _open_limit_order_stub(
            order_id="second-bot-id",
            exchange_order_id="OGE3T6-NDOIV-LR6MZI",
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[first_candidate, second_candidate],
        )
        exchange_if.orders.cancel_order = mock.AsyncMock()
        mapped = asyncio.run(
            synchronizer._map_unmapped_open_order_for_reference(
                reference_order=reference_order,
                reference_order_id=str(reference_order.id),
                side=trading_enums.TradeOrderSide.BUY,
                trader_order_type=trading_enums.TraderOrderType.BUY_LIMIT,
                order_target_price=decimal.Decimal("59326.7"),
                active_reference_ids={str(reference_order.id)},
                scaled_reference_quantity=decimal.Decimal("0.0001"),
            )
        )
        assert mapped is second_candidate
        assert second_candidate.order_id == str(reference_order.id)
        exchange_if.orders.cancel_order.assert_awaited_once_with(first_candidate)
        assert any("Ambiguous unmapped open order match" in record.message for record in caplog.records)

    def test_skips_order_claimed_by_another_reference(self):
        reference_order = _btc_usdc_buy_limit_reference_order(order_id="28c1394b-dcb7-4f90-8878-4a61827471ca")
        other_reference_id = "other-reference-id"
        claimed_order = _open_limit_order_stub(
            order_id=other_reference_id,
            exchange_order_id="CLAIMED-TXID",
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, _exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[claimed_order],
        )
        mapped = asyncio.run(
            synchronizer._map_unmapped_open_order_for_reference(
                reference_order=reference_order,
                reference_order_id=str(reference_order.id),
                side=trading_enums.TradeOrderSide.BUY,
                trader_order_type=trading_enums.TraderOrderType.BUY_LIMIT,
                order_target_price=decimal.Decimal("59326.7"),
                active_reference_ids={str(reference_order.id), other_reference_id},
                scaled_reference_quantity=decimal.Decimal("0.0001"),
            )
        )
        assert mapped is None


class TestRelinkOpenOrderToReference:
    def test_replace_order_tag_and_id_updated(self):
        reference_order_id = "28c1394b-dcb7-4f90-8878-4a61827471ca"
        open_order = _open_limit_order_stub(
            order_id="previous-bot-id",
            exchange_order_id="OGE3T6-NDOIV-LR6MZI",
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=None,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[],
            open_orders=[open_order],
        )
        relinked = synchronizer._relink_open_order_to_reference(open_order, reference_order_id)
        assert relinked.order_id == reference_order_id
        assert relinked.tag == copy_constants.MIRRORED_ORDER_TAG
        exchange_if.orders._exchange_manager.exchange_personal_data.orders_manager.replace_order.assert_called_once_with(
            "previous-bot-id",
            open_order,
        )


class TestUpsertMirroredReferenceOrderMapsBeforeCreate:
    def test_unmapped_same_price_order_is_already_synchronized_without_create(self):
        reference_order_id = "28c1394b-dcb7-4f90-8878-4a61827471ca"
        reference_order = _btc_usdc_buy_limit_reference_order(order_id=reference_order_id)
        open_order = _open_limit_order_stub(
            order_id="stale-bot-id",
            exchange_order_id="OGE3T6-NDOIV-LR6MZI",
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=None,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[open_order],
        )
        exchange_if.orders.create_orders = mock.AsyncMock()
        exchange_if.orders.cancel_order = mock.AsyncMock()
        compute_result = mirrored_quantity_compute_result.MirroredQuantityComputeResult(
            ideal_quantity=decimal.Decimal("0.0001"),
            resolved_trader_order_type=trading_enums.TraderOrderType.BUY_LIMIT,
            limit_price=decimal.Decimal("59326.7"),
            current_price=decimal.Decimal("59326.7"),
        )
        with mock.patch.object(
            synchronizer,
            "_is_late_reference_fill_for_order",
            return_value=False,
        ), mock.patch.object(
            synchronizer,
            "_compute_mirrored_quantity_type_and_price",
            mock.AsyncMock(return_value=compute_result),
        ):
            created, replaced_cancelled, already_synchronized, replication_failure = asyncio.run(
                synchronizer._upsert_mirrored_reference_order(reference_order)
            )
        assert created == []
        assert replaced_cancelled == 0
        assert already_synchronized == 1
        assert replication_failure is None
        exchange_if.orders.create_orders.assert_not_called()
        exchange_if.orders.cancel_order.assert_not_called()
        assert open_order.order_id == reference_order_id
