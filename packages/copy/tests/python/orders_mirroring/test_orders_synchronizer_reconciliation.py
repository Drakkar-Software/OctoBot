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
"""
OrdersSynchronizer price-level open-order reconciliation cases.

Catalog (extend when a new reconcile bug appears — add Rn + class):
  R1 Wrong-price stray (OAEOCK) — cancel off-grid; keep matched
  R2 Duplicate at same valid price (full) — cancel extras beyond reference count
  R3 Multiple reference orders at same price — do not cancel down to 1 when ref count is 2+
  R4 stray_only mode — cancel wrong-price only; keep same-price duplicates
  R5 Pre-sync + post-sync always — both run; post runs even with no creates/replaces
  R6 Sync cancels untagged stray before upsert
  R7 Replace waits for cancel before create
  R8 Ambiguous map cancels extras
  R9 Late-fill-adjusted count invariant — no error when actual == expected - late_fills
  R10 Invariant does not call reconcile — log only
  R11 Force-abort / public reconcile — full mode
  R12 Grace symbol + wrong-price (D) — stray cancelled under stray_only
  R13 Grace symbol + duplicate (O) — stray_only keeps; full after abort
  R14 Count invariant after wait — no premature ERROR while pending creation
  R15 Grace keeps mirrored orphan off-grid; cancels untagged wrong-price
"""
import asyncio
import contextlib
import decimal
import logging
import time
import typing

import mock

import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_copy.orders_mirroring.mirrored_quantity_compute_result as mirrored_quantity_compute_result
import octobot_copy.orders_mirroring.orders_synchronizer as orders_synchronizer_module


def _copied_account(
    *,
    orders: typing.Optional[list[protocol_models.Order]] = None,
) -> protocol_models.CopiedAccount:
    return protocol_models.CopiedAccount(
        version=copy_constants.COPIED_ACCOUNT_VERSION,
        updated_at=time.time(),
        copied_assets=[
            protocol_models.CopiedAsset(name="BTC", total=1.0, available=1.0, ratio=0.5),
            protocol_models.CopiedAsset(name="USDC", total=10000.0, available=10000.0, ratio=0.5),
        ],
        orders=orders,
    )


@contextlib.asynccontextmanager
async def _passthrough_mirror_sync_available_updates():
    yield


def _exchange_interface_stub(*, currency_totals: dict[str, decimal.Decimal], market_price: decimal.Decimal):
    exchange_interface = mock.MagicMock()
    exchange_interface.portfolio.reference_market = "USDC"
    exchange_interface.portfolio.get_currency_portfolio_total = (
        lambda currency: currency_totals[currency]
    )
    exchange_interface.market.get_potentially_outdated_price = mock.Mock(
        return_value=(market_price, False)
    )
    exchange_interface.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
    return exchange_interface


def _btc_usdc_limit_reference_order(
    *,
    order_id: str,
    side: protocol_models.Side,
    price: decimal.Decimal,
    quantity: decimal.Decimal = decimal.Decimal("0.0001"),
) -> protocol_models.Order:
    return protocol_models.Order(
        id=order_id,
        symbol="BTC/USDC",
        price=float(price),
        quantity=float(quantity),
        filled=0.0,
        exchange_id=f"ref-{order_id[:8]}",
        side=side,
        type=protocol_models.OrderType.LIMIT,
        trigger_above=side is protocol_models.Side.SELL,
        reduce_only=False,
        is_active=True,
        status=protocol_models.OrderStatus.OPEN,
        created_at=timestamp_util.utc_datetime_from_timestamp(time.time()),
    )


def _open_limit_order_stub(
    *,
    order_id: str,
    exchange_order_id: str,
    side: trading_enums.TradeOrderSide,
    quantity: decimal.Decimal,
    price: decimal.Decimal,
    tag: str | None = None,
):
    order_type = (
        trading_enums.TraderOrderType.SELL_LIMIT
        if side is trading_enums.TradeOrderSide.SELL
        else trading_enums.TraderOrderType.BUY_LIMIT
    )
    order = mock.Mock()
    order.order_id = order_id
    order.exchange_order_id = exchange_order_id
    order.symbol = "BTC/USDC"
    order.side = side
    order.origin_quantity = quantity
    order.origin_price = price
    order.order_type = order_type
    order.tag = tag
    order.status = trading_enums.OrderStatus.OPEN
    return order


def _synchronizer_with_open_orders(
    *,
    reference_orders: list[protocol_models.Order],
    open_orders: list,
) -> tuple[orders_synchronizer_module.OrdersSynchronizer, mock.MagicMock]:
    reference = _copied_account(orders=reference_orders)
    exchange_if = _exchange_interface_stub(
        currency_totals={
            "BTC": decimal.Decimal("0.01"),
            "USDC": decimal.Decimal("10000"),
        },
        market_price=decimal.Decimal("66326.7"),
    )
    exchange_if.orders.get_open_orders = mock.Mock(return_value=open_orders)
    exchange_if.orders.cancel_order = mock.AsyncMock()
    exchange_if.orders.automatically_synchronize_orders = mock.Mock(return_value=True)
    orders_manager = mock.Mock()
    exchange_if.orders._exchange_manager = mock.Mock()
    exchange_if.orders._exchange_manager.exchange_personal_data.orders_manager = orders_manager
    synchronizer = orders_synchronizer_module.OrdersSynchronizer(
        reference,
        exchange_if,
        copy_entities.AccountCopySettings(),
    )
    return synchronizer, exchange_if


class TestCaseR1WrongPriceStray:
    """
    R1 — Wrong-price stray (OAEOCK-class).

    Trigger: open limit at a price not in reference grid; another open matches a reference level.
    Expected: cancel only the stray; keep the matched order.
    """

    def test_reconcile_cancels_stray_keeps_matched(self):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="2f7c0eac-cd66-42ff-96f6-80b2e6039658",
            side=protocol_models.Side.SELL,
            price=decimal.Decimal("66326.7"),
        )
        stray_order = _open_limit_order_stub(
            order_id="86fc50ab-7bc4-4632-a2e0-2c9128d0ba9e",
            exchange_order_id="OAEOCK-6OQ3C-VDJ6QN",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.0002"),
            price=decimal.Decimal("65326.7"),
            tag=None,
        )
        matched_order = _open_limit_order_stub(
            order_id=str(reference_order.id),
            exchange_order_id="OPXF5Q-6AKBQ-PAJXD2",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.00027"),
            price=decimal.Decimal("66326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[stray_order, matched_order],
        )
        cancelled_count = asyncio.run(
            synchronizer._reconcile_open_orders_with_reference([reference_order])
        )
        assert cancelled_count == 1
        exchange_if.orders.cancel_order.assert_awaited_once_with(stray_order)


class TestCaseR2DuplicateAtSamePriceFull:
    """
    R2 — Duplicate at same valid price (full reconcile).

    Trigger: two opens at one reference price level; reference count is one.
    Expected: cancel the non-preferred duplicate; keep the tagged match.
    """

    def test_reconcile_cancels_duplicate_at_same_price(self):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="28c1394b-dcb7-4f90-8878-4a61827471ca",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        first_duplicate = _open_limit_order_stub(
            order_id="first-bot-id",
            exchange_order_id="O7GDOQ-5ALJT-5QPQE4",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.00009"),
            price=decimal.Decimal("59326.7"),
        )
        second_duplicate = _open_limit_order_stub(
            order_id=str(reference_order.id),
            exchange_order_id="OGE3T6-NDOIV-LR6MZI",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[first_duplicate, second_duplicate],
        )
        cancelled_count = asyncio.run(
            synchronizer._reconcile_open_orders_with_reference([reference_order])
        )
        assert cancelled_count == 1
        exchange_if.orders.cancel_order.assert_awaited_once_with(first_duplicate)


class TestCaseR3MultipleReferenceAtSamePrice:
    """
    R3 — Multiple reference orders at the same price.

    Trigger: two reference orders and two opens at the same price level.
    Expected: cancel count 0; do not cancel down to a single open.
    """

    def test_keeps_two_opens_when_reference_has_two_at_level(self):
        first_ref = _btc_usdc_limit_reference_order(
            order_id="ref-a",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        second_ref = _btc_usdc_limit_reference_order(
            order_id="ref-b",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        first_open = _open_limit_order_stub(
            order_id="ref-a",
            exchange_order_id="EX-A",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        second_open = _open_limit_order_stub(
            order_id="ref-b",
            exchange_order_id="EX-B",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[first_ref, second_ref],
            open_orders=[first_open, second_open],
        )
        cancelled_count = asyncio.run(
            synchronizer._reconcile_open_orders_with_reference([first_ref, second_ref])
        )
        assert cancelled_count == 0
        exchange_if.orders.cancel_order.assert_not_called()


class TestCaseR4StrayOnlyMode:
    """
    R4 — stray_only mode.

    Trigger: wrong-price stray plus same-price duplicate; stray_only_symbols includes the symbol.
    Expected: cancel wrong-price only; keep same-price duplicate.
    """

    def test_stray_only_cancels_wrong_price_keeps_duplicate(self):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="ref-1",
            side=protocol_models.Side.SELL,
            price=decimal.Decimal("66326.7"),
        )
        stray = _open_limit_order_stub(
            order_id="wrong",
            exchange_order_id="OAEOCK-STRAY",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.0002"),
            price=decimal.Decimal("65326.7"),
        )
        preferred = _open_limit_order_stub(
            order_id="ref-1",
            exchange_order_id="MATCHED",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.00027"),
            price=decimal.Decimal("66326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        duplicate = _open_limit_order_stub(
            order_id="dup",
            exchange_order_id="DUP",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.0002"),
            price=decimal.Decimal("66326.7"),
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[stray, preferred, duplicate],
        )
        cancelled_count = asyncio.run(
            synchronizer._reconcile_open_orders_with_reference(
                [reference_order],
                stray_only_symbols={"BTC/USDC"},
            )
        )
        assert cancelled_count == 1
        exchange_if.orders.cancel_order.assert_awaited_once_with(stray)


class TestCaseR5PreAndPostSyncAlways:
    """
    R5 — Pre-sync and post-sync reconcile always.

    Trigger: synchronize with already-synced opens and no creates/replaces.
    Expected: _reconcile_open_orders_with_reference awaited twice.
    """

    def test_post_reconcile_runs_when_no_creates_or_replaces(self):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="ref-1",
            side=protocol_models.Side.SELL,
            price=decimal.Decimal("66326.7"),
        )
        matched = _open_limit_order_stub(
            order_id="ref-1",
            exchange_order_id="MATCHED",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.00027"),
            price=decimal.Decimal("66326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, _exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[matched],
        )
        reconcile_mock = mock.AsyncMock(return_value=0)
        with mock.patch.object(
            synchronizer,
            "_reconcile_open_orders_with_reference",
            reconcile_mock,
        ), mock.patch.object(
            synchronizer,
            "cancel_orders_pending_synchronization",
            mock.AsyncMock(return_value=0),
        ), mock.patch.object(
            synchronizer,
            "_upsert_mirrored_reference_order",
            mock.AsyncMock(return_value=([], 0, 1, None)),
        ):
            asyncio.run(synchronizer.synchronize())
        assert reconcile_mock.await_count == 2


class TestCaseR6SyncCancelsUntaggedStray:
    """
    R6 — Sync cancels untagged stray before upsert.

    Trigger: synchronize with an untagged wrong-price open and a matched mirrored open.
    Expected: cancel the stray once before upserts proceed.
    """

    def test_synchronize_cancels_untagged_stray_before_upsert(self):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="2f7c0eac-cd66-42ff-96f6-80b2e6039658",
            side=protocol_models.Side.SELL,
            price=decimal.Decimal("66326.7"),
        )
        stray_order = _open_limit_order_stub(
            order_id="86fc50ab-7bc4-4632-a2e0-2c9128d0ba9e",
            exchange_order_id="OAEOCK-6OQ3C-VDJ6QN",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.0002"),
            price=decimal.Decimal("65326.7"),
            tag=None,
        )
        matched_order = _open_limit_order_stub(
            order_id=str(reference_order.id),
            exchange_order_id="OPXF5Q-6AKBQ-PAJXD2",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.00027"),
            price=decimal.Decimal("66326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[stray_order, matched_order],
        )
        remaining_open_orders = [stray_order, matched_order]

        def get_open_orders(symbol=None):
            if symbol is None or symbol == "BTC/USDC":
                return list(remaining_open_orders)
            return []

        exchange_if.orders.get_open_orders = mock.Mock(side_effect=get_open_orders)

        async def cancel_side_effect(order):
            if order in remaining_open_orders:
                remaining_open_orders.remove(order)

        exchange_if.orders.cancel_order = mock.AsyncMock(side_effect=cancel_side_effect)
        with mock.patch.object(
            synchronizer,
            "cancel_orders_pending_synchronization",
            mock.AsyncMock(return_value=0),
        ), mock.patch.object(
            synchronizer,
            "_upsert_mirrored_reference_order",
            mock.AsyncMock(return_value=([], 0, 1, None)),
        ):
            asyncio.run(synchronizer.synchronize())
        exchange_if.orders.cancel_order.assert_awaited_once_with(stray_order)


class TestCaseR7ReplaceCancelsThenCreates:
    """
    R7 — Replace cancels then creates.

    Trigger: upsert replace of an existing mirrored limit with quantity mismatch.
    Expected: cancel_order then create_orders (no wait_for_order_absent).
    """

    def test_replace_cancels_then_creates(self):
        reference_order_id = "2f7c0eac-cd66-42ff-96f6-80b2e6039658"
        reference_order = _btc_usdc_limit_reference_order(
            order_id=reference_order_id,
            side=protocol_models.Side.SELL,
            price=decimal.Decimal("66326.7"),
            quantity=decimal.Decimal("0.00027"),
        )
        existing_order = _open_limit_order_stub(
            order_id=reference_order_id,
            exchange_order_id="OAINUR-XFJRB-SKVMUR",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.0003071"),
            price=decimal.Decimal("66326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[existing_order],
        )
        exchange_if.market.get_market_status = mock.Mock(return_value=mock.Mock())
        exchange_if.orders.adapt_order_quantity_and_target_price_for_order_creation = mock.Mock(
            return_value=(decimal.Decimal("66326.7"), decimal.Decimal("0.00027639")),
        )
        exchange_if.orders.create_orders = mock.AsyncMock(return_value=([], False))
        compute_result = mirrored_quantity_compute_result.MirroredQuantityComputeResult(
            ideal_quantity=decimal.Decimal("0.00027639"),
            resolved_trader_order_type=trading_enums.TraderOrderType.SELL_LIMIT,
            limit_price=decimal.Decimal("66326.7"),
            current_price=decimal.Decimal("66326.7"),
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
            asyncio.run(synchronizer._upsert_mirrored_reference_order(reference_order))
        exchange_if.orders.cancel_order.assert_awaited_once_with(existing_order)
        exchange_if.orders.create_orders.assert_awaited_once()


class TestCaseR8AmbiguousMapCancelsExtras:
    """
    R8 — Ambiguous map cancels extras.

    Trigger: two unmapped opens at the reference price for one reference order.
    Expected: relink preferred candidate; cancel the other; warn about ambiguous match.
    """

    def test_ambiguous_candidates_relinks_one_and_cancels_extras(self, caplog):
        caplog.set_level(logging.WARNING)
        reference_order = _btc_usdc_limit_reference_order(
            order_id="28c1394b-dcb7-4f90-8878-4a61827471ca",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        first_candidate = _open_limit_order_stub(
            order_id="first-bot-id",
            exchange_order_id="O7GDOQ-5ALJT-5QPQE4",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.00009"),
            price=decimal.Decimal("59326.7"),
        )
        second_candidate = _open_limit_order_stub(
            order_id="second-bot-id",
            exchange_order_id="OGE3T6-NDOIV-LR6MZI",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[first_candidate, second_candidate],
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
        assert mapped is second_candidate
        assert second_candidate.order_id == str(reference_order.id)
        exchange_if.orders.cancel_order.assert_awaited_once_with(first_candidate)
        assert any("Ambiguous unmapped open order match" in record.message for record in caplog.records)


class TestCaseR9LateFillAdjustedInvariant:
    """
    R9 — Late-fill-adjusted count invariant.

    Trigger: reference open count exceeds copier opens by late-fill candidate count.
    Expected: no open-limit count mismatch error log.
    """

    def test_no_error_when_count_matches_after_late_fill_adjustment(self, caplog):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="ref-late",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        # Copier has zero opens; one late-fill candidate → expected 0.
        synchronizer, _exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[],
        )
        with mock.patch.object(
            synchronizer,
            "_late_reference_fill_candidate_orders",
            return_value=[reference_order],
        ):
            with caplog.at_level(logging.ERROR):
                synchronizer._check_open_limit_order_count_invariant([reference_order])
        assert not any(
            "Open limit order count mismatch" in record.message
            for record in caplog.records
        )


class TestCaseR10InvariantDoesNotReconcile:
    """
    R10 — Invariant logs only; does not reconcile.

    Trigger: actual open count differs from adjusted expected with no late fills.
    Expected: error log; _reconcile_open_orders_with_reference not called.
    """

    def test_mismatch_logs_without_reconcile(self, caplog):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="ref-1",
            side=protocol_models.Side.SELL,
            price=decimal.Decimal("66326.7"),
        )
        stray = _open_limit_order_stub(
            order_id="extra",
            exchange_order_id="EXTRA",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.0002"),
            price=decimal.Decimal("66326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        matched = _open_limit_order_stub(
            order_id="ref-1",
            exchange_order_id="MATCHED",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("0.00027"),
            price=decimal.Decimal("66326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[matched, stray],
        )
        reconcile_spy = mock.AsyncMock(return_value=0)
        with mock.patch.object(
            synchronizer,
            "_reconcile_open_orders_with_reference",
            reconcile_spy,
        ), mock.patch.object(
            synchronizer,
            "_late_reference_fill_candidate_orders",
            return_value=[],
        ):
            with caplog.at_level(logging.ERROR):
                synchronizer._check_open_limit_order_count_invariant([reference_order])
        reconcile_spy.assert_not_called()
        assert any(
            "Open limit order count mismatch" in record.message
            for record in caplog.records
        )


class TestCaseR11ForceAbortFullReconcile:
    """
    R11 — Force-abort / public reconcile uses full mode.

    Trigger: same-price duplicate with stray_only_symbols set, or public reconcile entry.
    Expected: force-abort ignores stray_only and cancels duplicate; public reconcile cancels duplicate.
    """

    def test_force_abort_ignores_stray_only_symbols(self):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="ref-1",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        preferred = _open_limit_order_stub(
            order_id="ref-1",
            exchange_order_id="PREF",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        duplicate = _open_limit_order_stub(
            order_id="dup",
            exchange_order_id="DUP",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.00009"),
            price=decimal.Decimal("59326.7"),
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[preferred, duplicate],
        )
        synchronizer.abort_mirrored_orphan_grace()
        cancelled_count = asyncio.run(
            synchronizer._reconcile_open_orders_with_reference(
                [reference_order],
                stray_only_symbols={"BTC/USDC"},
            )
        )
        assert cancelled_count == 1
        exchange_if.orders.cancel_order.assert_awaited_once_with(duplicate)

    def test_public_reconcile_cancels_duplicate(self):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="ref-1",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        preferred = _open_limit_order_stub(
            order_id="ref-1",
            exchange_order_id="PREF",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        duplicate = _open_limit_order_stub(
            order_id="dup",
            exchange_order_id="DUP",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.00009"),
            price=decimal.Decimal("59326.7"),
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[preferred, duplicate],
        )
        cancelled_count = asyncio.run(synchronizer.reconcile_open_orders_with_reference())
        assert cancelled_count == 1
        exchange_if.orders.cancel_order.assert_awaited_once_with(duplicate)


class TestCaseR12GraceSymbolWrongPrice:
    """
    R12 — Grace symbol + wrong-price stray.

    Trigger: synchronize with grace skip symbols set and an off-grid open.
    Expected: cancel the stray; skip upserts on the grace symbol.
    """

    def test_synchronize_cancels_stray_while_grace_skips_upserts(self, caplog):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="ref-late",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        stray = _open_limit_order_stub(
            order_id="wrong",
            exchange_order_id="OAEOCK",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("50000"),
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[stray],
        )
        open_orders = [stray]

        def get_open_orders(symbol=None):
            if symbol is None or symbol == "BTC/USDC":
                return list(open_orders)
            return []

        exchange_if.orders.get_open_orders = mock.Mock(side_effect=get_open_orders)

        async def cancel_side_effect(order):
            if order in open_orders:
                open_orders.remove(order)

        exchange_if.orders.cancel_order = mock.AsyncMock(side_effect=cancel_side_effect)
        with mock.patch.object(
            synchronizer,
            "_reference_symbols_skipped_while_grace_orphans_uncancelled",
            return_value={"BTC/USDC"},
        ), mock.patch.object(
            synchronizer,
            "_maybe_bypass_grace_for_missing_mirrored_reference_orders",
            side_effect=lambda replicable, skip: skip,
        ), mock.patch.object(
            synchronizer,
            "cancel_orders_pending_synchronization",
            mock.AsyncMock(return_value=0),
        ):
            with caplog.at_level(logging.INFO):
                created = asyncio.run(synchronizer.synchronize())
        assert created == []
        exchange_if.orders.cancel_order.assert_awaited_once_with(stray)
        assert any(
            "Skipped reference mirror upsert" in record.message
            for record in caplog.records
        )


class TestCaseR13GraceSymbolDuplicate:
    """
    R13 — Grace symbol + duplicate at valid price.

    Trigger: two opens at the same reference price; stray_only then force-abort.
    Expected: keep both under stray_only; cancel duplicate after abort (full mode).
    """

    def test_keeps_duplicate_during_grace_cancels_after_abort(self):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="ref-1",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        preferred = _open_limit_order_stub(
            order_id="ref-1",
            exchange_order_id="PREF",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        duplicate = _open_limit_order_stub(
            order_id="dup",
            exchange_order_id="DUP",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.00009"),
            price=decimal.Decimal("59326.7"),
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[preferred, duplicate],
        )
        cancelled_during_grace = asyncio.run(
            synchronizer._reconcile_open_orders_with_reference(
                [reference_order],
                stray_only_symbols={"BTC/USDC"},
            )
        )
        assert cancelled_during_grace == 0
        exchange_if.orders.cancel_order.assert_not_called()
        synchronizer.abort_mirrored_orphan_grace()
        cancelled_after_abort = asyncio.run(
            synchronizer._reconcile_open_orders_with_reference(
                [reference_order],
                stray_only_symbols={"BTC/USDC"},
            )
        )
        assert cancelled_after_abort == 1
        exchange_if.orders.cancel_order.assert_awaited_once_with(duplicate)


class TestCaseR14InvariantAfterWait:
    """
    R14 — Count invariant after wait.

    Trigger: synchronize creates an order while auto-sync is off (wait path used).
    Expected: wait_for_orders_to_open runs before _check_open_limit_order_count_invariant;
    when wait leaves open count matching reference, no mismatch ERROR.
    """

    def test_invariant_after_wait_with_matching_count_logs_no_error(self, caplog):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="ref-1",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        created_open = _open_limit_order_stub(
            order_id="ref-1",
            exchange_order_id="CREATED",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("59326.7"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=[],
        )
        exchange_if.orders.automatically_synchronize_orders = mock.Mock(return_value=False)
        call_order: list[str] = []

        async def wait_side_effect(orders, symbol):
            call_order.append("wait")
            # Promote: after wait, local open book matches reference count.
            exchange_if.orders.get_open_orders = mock.Mock(return_value=[created_open])

        def invariant_side_effect(replicable):
            call_order.append("invariant")
            orders_synchronizer_module.OrdersSynchronizer._check_open_limit_order_count_invariant(
                synchronizer,
                replicable,
            )

        exchange_if.orders.wait_for_orders_to_open = mock.AsyncMock(side_effect=wait_side_effect)
        with mock.patch.object(
            synchronizer,
            "cancel_orders_pending_synchronization",
            mock.AsyncMock(return_value=0),
        ), mock.patch.object(
            synchronizer,
            "_upsert_mirrored_reference_order",
            mock.AsyncMock(return_value=([created_open], 0, 0, None)),
        ), mock.patch.object(
            synchronizer,
            "_reconcile_open_orders_with_reference",
            mock.AsyncMock(return_value=0),
        ), mock.patch.object(
            synchronizer,
            "_check_open_limit_order_count_invariant",
            side_effect=invariant_side_effect,
        ):
            with caplog.at_level(logging.ERROR):
                asyncio.run(synchronizer.synchronize())
        assert call_order == ["wait", "invariant"]
        exchange_if.orders.wait_for_orders_to_open.assert_awaited_once()
        assert not any(
            "Open limit order count mismatch" in record.message
            for record in caplog.records
        )


class TestCaseR15GraceKeepsMirroredOrphanStray:
    """
    R15 — Grace keeps mirrored orphan stray; cancels untagged.

    Trigger: stray_only_symbols set; mirrored orphan at off-grid price + untagged wrong-price open.
    Expected: cancel only the untagged open; keep the mirrored orphan. Force-abort cancels both.
    """

    def test_stray_only_keeps_mirrored_orphan_cancels_untagged(self):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="ref-1",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        mirrored_orphan = _open_limit_order_stub(
            order_id="grid_ref_b1",
            exchange_order_id="ORPHAN",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("50000"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        untagged_stray = _open_limit_order_stub(
            order_id="wrong",
            exchange_order_id="OAEOCK",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("45000"),
        )
        open_orders = [mirrored_orphan, untagged_stray]
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=open_orders,
        )

        def get_open_orders(symbol=None):
            if symbol is None or symbol == "BTC/USDC":
                return list(open_orders)
            return []

        exchange_if.orders.get_open_orders = mock.Mock(side_effect=get_open_orders)

        async def cancel_side_effect(order):
            if order in open_orders:
                open_orders.remove(order)

        exchange_if.orders.cancel_order = mock.AsyncMock(side_effect=cancel_side_effect)
        cancelled_count = asyncio.run(
            synchronizer._reconcile_open_orders_with_reference(
                [reference_order],
                stray_only_symbols={"BTC/USDC"},
            )
        )
        assert cancelled_count == 1
        exchange_if.orders.cancel_order.assert_awaited_once_with(untagged_stray)
        assert mirrored_orphan in open_orders
        assert untagged_stray not in open_orders

    def test_force_abort_cancels_mirrored_orphan_and_untagged(self):
        reference_order = _btc_usdc_limit_reference_order(
            order_id="ref-1",
            side=protocol_models.Side.BUY,
            price=decimal.Decimal("59326.7"),
        )
        mirrored_orphan = _open_limit_order_stub(
            order_id="grid_ref_b1",
            exchange_order_id="ORPHAN",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("50000"),
            tag=copy_constants.MIRRORED_ORDER_TAG,
        )
        untagged_stray = _open_limit_order_stub(
            order_id="wrong",
            exchange_order_id="OAEOCK",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("0.0001"),
            price=decimal.Decimal("45000"),
        )
        open_orders = [mirrored_orphan, untagged_stray]
        synchronizer, exchange_if = _synchronizer_with_open_orders(
            reference_orders=[reference_order],
            open_orders=open_orders,
        )

        def get_open_orders(symbol=None):
            if symbol is None or symbol == "BTC/USDC":
                return list(open_orders)
            return []

        exchange_if.orders.get_open_orders = mock.Mock(side_effect=get_open_orders)

        async def cancel_side_effect(order):
            if order in open_orders:
                open_orders.remove(order)

        exchange_if.orders.cancel_order = mock.AsyncMock(side_effect=cancel_side_effect)
        synchronizer.abort_mirrored_orphan_grace()
        cancelled_count = asyncio.run(
            synchronizer._reconcile_open_orders_with_reference(
                [reference_order],
                stray_only_symbols={"BTC/USDC"},
            )
        )
        assert cancelled_count == 2
        assert exchange_if.orders.cancel_order.await_count == 2
        assert open_orders == []
