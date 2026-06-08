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
import decimal
import time

import mock

import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_copy.constants as copy_constants
import octobot_copy.orders_mirroring.mirrored_order_replication_failure as mirrored_order_replication_failure
import octobot_copy.orders_mirroring.mirrored_order_replication_failure_util as mirrored_order_replication_failure_util


def _reference_limit_order(
    *,
    order_id: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    symbol: str = "ETH/USDT",
    price: float | None = 50745.57,
    quantity: float = 0.001,
    side: protocol_models.Side = protocol_models.Side.BUY,
) -> protocol_models.Order:
    return protocol_models.Order(
        id=order_id,
        symbol=symbol,
        price=price,
        quantity=quantity,
        filled=0.0,
        exchange_id="ex",
        side=side,
        type=protocol_models.OrderType.LIMIT,
        trigger_above=False,
        reduce_only=False,
        is_active=True,
        status=protocol_models.OrderStatus.OPEN,
        created_at=timestamp_util.utc_datetime_from_timestamp(time.time()),
    )


def _copied_account_with_usdt_total(usdt_total: float) -> protocol_models.CopiedAccount:
    return protocol_models.CopiedAccount(
        version=copy_constants.COPIED_ACCOUNT_VERSION,
        updated_at=time.time(),
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


def _failure(
    *,
    order_id: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    short_reason: str = "insufficient_quote",
    side: str = "buy",
    symbol: str = "ETH/USDT",
    price: decimal.Decimal = decimal.Decimal("50745.57"),
) -> mirrored_order_replication_failure.MirroredOrderReplicationFailure:
    return mirrored_order_replication_failure.MirroredOrderReplicationFailure(
        symbol=symbol,
        side=side,
        price=price,
        reference_order_id=order_id,
        short_reason=short_reason,
    )


class TestReplicationFailureFromOrder:
    def test_builds_failure_from_buy_limit_order(self):
        order = _reference_limit_order(
            order_id="11111111-2222-3333-4444-555555555555",
            price=50745.57,
        )

        failure = mirrored_order_replication_failure_util.replication_failure_from_order(
            order,
            "insufficient_quote",
        )

        assert failure.symbol == "ETH/USDT"
        assert failure.side == "buy"
        assert failure.price == decimal.Decimal("50745.57")
        assert failure.reference_order_id == "11111111-2222-3333-4444-555555555555"
        assert failure.short_reason == "insufficient_quote"

    def test_uses_unknown_side_when_order_side_missing(self):
        order = mock.Mock()
        order.symbol = "ETH/USDT"
        order.id = "order-without-side"
        order.price = 2000.0
        order.side = None

        failure = mirrored_order_replication_failure_util.replication_failure_from_order(
            order,
            "zero_scaled_quantity",
        )

        assert failure.side == "unknown"

    def test_zero_price_when_order_price_missing(self):
        order = mock.Mock()
        order.symbol = "ETH/USDT"
        order.id = "order-without-price"
        order.price = ""
        order.side = protocol_models.Side.BUY

        failure = mirrored_order_replication_failure_util.replication_failure_from_order(
            order,
            "zero_scaled_quantity",
        )

        assert failure.price == trading_constants.ZERO


class TestFormatReplicationFailureEntry:
    def test_formats_side_symbol_price_id_and_reason(self):
        failure = _failure()

        entry = mirrored_order_replication_failure_util.format_replication_failure_entry(failure)

        assert entry == (
            "buy ETH/USDT @ 50745.57 [aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee] (insufficient_quote)"
        )


class TestFormatGracePeriodDeferredSummary:
    def test_empty_when_no_grace_failures(self):
        assert mirrored_order_replication_failure_util.format_grace_period_deferred_summary([]) == ""

    def test_single_grace_failure_summary(self):
        failure = _failure(short_reason="grace_period_active")

        summary = mirrored_order_replication_failure_util.format_grace_period_deferred_summary([failure])

        assert summary == (
            "Grace period active for 1 order(s): buy ETH/USDT @ 50745.57 "
            "[aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee] (grace_period_active)."
        )
        assert "Failed to replicate" not in summary

    def test_truncates_beyond_summary_limit(self):
        failures = [
            _failure(
                order_id=f"{index:08d}-0000-0000-0000-000000000000",
                short_reason="grace_period_active",
            )
            for index in range(
                mirrored_order_replication_failure_util.REPLICATION_FAILURES_SUMMARY_LIMIT + 1
            )
        ]

        summary = mirrored_order_replication_failure_util.format_grace_period_deferred_summary(failures)

        assert summary.startswith(
            f"Grace period active for {mirrored_order_replication_failure_util.REPLICATION_FAILURES_SUMMARY_LIMIT + 1} order(s):"
        )
        assert summary.endswith("… and 1 more.")
        assert "Failed to replicate" not in summary


class TestFormatLateReferenceFillCandidatesSummary:
    def test_empty_when_no_orders(self):
        assert mirrored_order_replication_failure_util.format_late_reference_fill_candidates_summary([]) == ""

    def test_formats_reference_order_details(self):
        order = _reference_limit_order(order_id="late-fill-order-1")

        summary = mirrored_order_replication_failure_util.format_late_reference_fill_candidates_summary([order])

        assert summary == (
            "buy ETH/USDT @ 50745.57 [late-fill-order-1] (late_reference_fill_candidate)"
        )


class TestFormatMirroredOrphanOrderEntry:
    def test_formats_copier_orphan_order(self):
        orphan_order = mock.Mock()
        orphan_order.symbol = "ETH/USDT"
        orphan_order.side = trading_enums.TradeOrderSide.SELL
        orphan_order.origin_price = decimal.Decimal("2000")
        orphan_order.order_id = "copier-orphan-1"

        entry = mirrored_order_replication_failure_util.format_mirrored_orphan_order_entry(orphan_order)

        assert entry == "sell ETH/USDT @ 2000 [copier order_id=copier-orphan-1]"


class TestFormatReplicationFailuresSummary:
    def test_empty_when_no_failures(self):
        assert mirrored_order_replication_failure_util.format_replication_failures_summary([]) == ""

    def test_single_failure_summary(self):
        failure = _failure()

        summary = mirrored_order_replication_failure_util.format_replication_failures_summary([failure])

        assert summary == (
            "Failed to replicate 1 order(s): buy ETH/USDT @ 50745.57 "
            "[aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee] (insufficient_quote)."
        )

    def test_truncates_beyond_summary_limit(self):
        failures = [
            _failure(
                order_id=f"{index:08d}-0000-0000-0000-000000000000",
                short_reason="insufficient_quote",
            )
            for index in range(
                mirrored_order_replication_failure_util.REPLICATION_FAILURES_SUMMARY_LIMIT + 1
            )
        ]

        summary = mirrored_order_replication_failure_util.format_replication_failures_summary(failures)

        assert summary.startswith(
            f"Failed to replicate {mirrored_order_replication_failure_util.REPLICATION_FAILURES_SUMMARY_LIMIT + 1} order(s):"
        )
        assert summary.endswith("… and 1 more.")
        assert summary.count("insufficient_quote") == (
            mirrored_order_replication_failure_util.REPLICATION_FAILURES_SUMMARY_LIMIT
        )


class TestLogSkippedMirrorAction:
    def test_logs_warning_with_context(self):
        logger = mock.Mock()
        failure = _failure()

        mirrored_order_replication_failure_util.log_skipped_mirror_action(
            logger,
            failure,
            trader_order_type=trading_enums.TraderOrderType.BUY_LIMIT,
            ideal_quantity=trading_constants.ZERO,
        )

        logger.warning.assert_called_once_with(
            "Skipping mirrored order creation (insufficient_quote): "
            "buy ETH/USDT @ 50745.57 [aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee] (insufficient_quote) "
            "type=TraderOrderType.BUY_LIMIT, ideal_quantity=0"
        )


class TestUpsertFailureReturn:
    def test_returns_empty_batch_and_failure(self):
        logger = mock.Mock()
        order = _reference_limit_order()

        created, replaced_count, already_count, failure = (
            mirrored_order_replication_failure_util.upsert_failure_return(
                logger,
                order,
                "below_min_volume",
                trading_enums.TraderOrderType.BUY_LIMIT,
            )
        )

        assert created == []
        assert replaced_count == 0
        assert already_count == 0
        assert failure.short_reason == "below_min_volume"
        logger.warning.assert_called_once()


class TestMirrorScaleFailureContext:
    def test_buy_uses_quote_currency_totals(self):
        order = _reference_limit_order(quantity=0.002)
        reference_account = _copied_account_with_usdt_total(500.0)
        exchange_interface = mock.MagicMock()
        exchange_interface.portfolio.get_currency_portfolio_total = mock.Mock(
            return_value=decimal.Decimal("169")
        )

        context = mirrored_order_replication_failure_util.mirror_scale_failure_context(
            order,
            "ETH/USDT",
            trading_enums.TradeOrderSide.BUY,
            decimal.Decimal("0.001"),
            reference_account,
            exchange_interface,
        )

        assert context == {
            "scale_currency": "USDT",
            "reference_total": decimal.Decimal("500"),
            "copier_total": decimal.Decimal("169"),
            "reference_order_quantity": decimal.Decimal("0.002"),
            "scaled_quantity": decimal.Decimal("0.001"),
        }
        exchange_interface.portfolio.get_currency_portfolio_total.assert_called_once_with("USDT")

    def test_sell_uses_base_currency_totals(self):
        order = _reference_limit_order(
            quantity=0.003,
            side=protocol_models.Side.SELL,
        )
        reference_account = protocol_models.CopiedAccount(
            version=copy_constants.COPIED_ACCOUNT_VERSION,
            updated_at=time.time(),
            copied_assets=[
                protocol_models.CopiedAsset(name="ETH", total=2.0, available=2.0, ratio=0.5),
                protocol_models.CopiedAsset(name="USDT", total=100.0, available=100.0, ratio=0.5),
            ],
            orders=[],
        )
        exchange_interface = mock.MagicMock()
        exchange_interface.portfolio.get_currency_portfolio_total = mock.Mock(
            return_value=decimal.Decimal("0.5")
        )

        context = mirrored_order_replication_failure_util.mirror_scale_failure_context(
            order,
            "ETH/USDT",
            trading_enums.TradeOrderSide.SELL,
            None,
            reference_account,
            exchange_interface,
        )

        assert context["scale_currency"] == "ETH"
        assert context["reference_total"] == decimal.Decimal("2")
        assert context["copier_total"] == decimal.Decimal("0.5")
        assert context["scaled_quantity"] is None
        exchange_interface.portfolio.get_currency_portfolio_total.assert_called_once_with("ETH")
