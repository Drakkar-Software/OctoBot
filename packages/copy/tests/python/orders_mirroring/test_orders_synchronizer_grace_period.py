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
OrdersSynchronizer mirrored-orphan / late-fill grace period scenarios.

Catalog (extend when a new grace bug appears — add a letter + class):
  A Late fill only — copier filled first; skip upserts; grace window active
  B Deferred tagged orphan — valid price; cancel deferred
  C Orphan + late fill together — both deferred / skip upserts
  D Wrong-price stray during grace — cancel stray; keep valid-price orphan; skip upserts
  E Grace elapsed — cancel tagged orphans; identified False
  F Explicit abort — abort_mirrored_orphan_grace then upserts proceed
  G Grace disabled (grace_seconds <= 0) — immediate orphan cancel; no skip set
  H grace_total >= threshold — immediate cancel + abort log
  I No compliant historical snapshot — immediate cancel
  J Missed historical signals abort — immediate cancel
  K Pair-ratio heuristic fails — orphans cancelled; late-fill continuation if present
  L Missing-mirror bypass — missing count > threshold clears skip / aborts grace
  M Idle / aligned — no skip; episode cleared only after prior defer
  N Duplicate at valid price with grace idle — no grace interference (see reconciliation suite)
  O Duplicate at valid price during grace — stray_only keeps both; upserts skipped
  P Grace keeps mirrored orphan off-grid; cancels untagged wrong-price via synchronize

Functional / grid fixtures: see functional_tests/test_sec_copy_grid_twenty_grace_elapsed.py
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
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
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


def _reference_account_with_allocations(
    base_ratio: decimal.Decimal,
    quote_ratio: decimal.Decimal,
) -> protocol_models.CopiedAccount:
    return _copied_account(
        copied_assets=[
            protocol_models.CopiedAsset(name="ETH", total=1.0, available=1.0, ratio=float(base_ratio)),
            protocol_models.CopiedAsset(name="USDT", total=10000.0, available=10000.0, ratio=float(quote_ratio)),
        ],
        orders=[],
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


def _order_stub(*, symbol: str, side, quantity: decimal.Decimal, price: decimal.Decimal):
    order = mock.Mock()
    order.symbol = symbol
    order.side = side
    order.origin_quantity = quantity
    order.origin_price = price
    return order


class TestScenarioKPairRatioHeuristic:
    """
    Scenario K — Pair-ratio heuristic helpers and batch eligibility.

    Trigger: orphan or reference pair-leg share setup for grace eligibility checks.
    Expected: share helpers match reference math; batch eligibility False when delta exceeds max.
    """
    def test_reference_pair_leg_share(self):
        reference = _reference_account_with_allocations(
            decimal.Decimal("0.25"),
            decimal.Decimal("0.5"),
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            mock.MagicMock(),
            copy_entities.AccountCopySettings(),
        )
        expected = decimal.Decimal("0.25") / (decimal.Decimal("0.25") + decimal.Decimal("0.5"))
        assert synchronizer._reference_pair_leg_share("ETH/USDT") == expected

    def test_reference_pair_leg_share_missing_quote_returns_one(self):
        reference = _copied_account(
            copied_assets=[
                protocol_models.CopiedAsset(name="ETH", total=1.0, available=1.0, ratio=0.5),
            ],
            orders=[],
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            mock.MagicMock(),
            copy_entities.AccountCopySettings(),
        )
        assert synchronizer._reference_pair_leg_share("ETH/USDT") == trading_constants.ONE

    def test_simulated_pair_share_buy_matches_reference_example(self):
        reference = _reference_account_with_allocations(
            decimal.Decimal("0.25"),
            decimal.Decimal("0.5"),
        )
        currency_totals = {
            "ETH": decimal.Decimal("1"),
            "USDT": decimal.Decimal("10000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(),
        )
        buy_order = _order_stub(
            symbol="ETH/USDT",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("1"),
            price=decimal.Decimal("2000"),
        )
        reference_share = synchronizer._reference_pair_leg_share("ETH/USDT")
        simulated_share = synchronizer._simulated_copier_pair_leg_share_after_orphan_fill(buy_order)
        assert reference_share is not None
        assert simulated_share is not None
        assert simulated_share == reference_share

    def test_batch_eligible_false_when_simulated_share_mismatch(self):
        reference = _reference_account_with_allocations(
            decimal.Decimal("0.5"),
            decimal.Decimal("0.5"),
        )
        currency_totals = {
            "ETH": decimal.Decimal("1"),
            "USDT": decimal.Decimal("10000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(mirrored_orphan_grace_pair_ratio_max_delta=decimal.Decimal("0.02")),
        )
        buy_order = _order_stub(
            symbol="ETH/USDT",
            side=trading_enums.TradeOrderSide.BUY,
            quantity=decimal.Decimal("1"),
            price=decimal.Decimal("2000"),
        )
        assert synchronizer._mirrored_orphan_batch_eligible_for_grace([buy_order]) is False

    def test_simulated_pair_share_sell(self):
        reference = _reference_account_with_allocations(
            decimal.Decimal("1") / decimal.Decimal("6"),
            decimal.Decimal("5") / decimal.Decimal("6"),
        )
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(),
        )
        sell_order = _order_stub(
            symbol="ETH/USDT",
            side=trading_enums.TradeOrderSide.SELL,
            quantity=decimal.Decimal("1"),
            price=decimal.Decimal("2000"),
        )
        reference_share = synchronizer._reference_pair_leg_share("ETH/USDT")
        simulated_share = synchronizer._simulated_copier_pair_leg_share_after_orphan_fill(sell_order)
        assert reference_share is not None
        assert simulated_share is not None
        # Reference leg share uses CopiedAsset.ratio (float round-trip); simulated share is exact Decimal math.
        assert abs(simulated_share - reference_share) <= decimal.Decimal("1e-15")
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


class TestScenarioALateFillOnly:
    """
    Scenario A — Late fill only (heuristic and grace start).

    Trigger: copier holdings match simulated reference fill; no tagged orphans.
    Expected: late-fill heuristic True; grace start resolves when applying late-fill-only grace.
    """
    def test_late_fill_true_when_copier_matches_simulated_reference_fill(self):
        reference = _copied_account(
            copied_assets=_eth_usdt_pair_assets(),
            orders=[],
        )
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(),
        )
        order = _replicable_buy_limit_order()
        assert synchronizer._passes_late_reference_fill_heuristic(order) is True
        assert synchronizer._is_late_reference_fill_for_order(order, []) is True

    def test_late_fill_false_when_new_reference_order_copier_not_yet_filled(self):
        reference = _copied_account(
            copied_assets=_eth_usdt_pair_assets(),
            orders=[],
        )
        currency_totals = {
            "ETH": decimal.Decimal("1"),
            "USDT": decimal.Decimal("10000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(),
        )
        order = _replicable_buy_limit_order()
        assert synchronizer._passes_late_reference_fill_heuristic(order) is False
        assert synchronizer._is_late_reference_fill_for_order(order, []) is False

    def test_grace_started_when_late_fill_only_no_orphans(self):
        assets = _eth_usdt_pair_assets()
        compliant_snapshot = _copied_account(
            updated_at=time.time() - 1.0,
            copied_assets=assets,
            orders=[],
        )
        reference = _copied_account(
            updated_at=time.time(),
            copied_assets=assets,
            orders=[],
            historical_snapshots=[compliant_snapshot],
        )
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        copy_settings = copy_entities.AccountCopySettings(
            mirrored_orphan_cancel_grace_seconds=60.0,
            mirrored_orphan_grace_abort_threshold=3,
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_settings,
        )
        order = _replicable_buy_limit_order()
        replicable = [order]

        async def run_grace():
            return await synchronizer._apply_grace_policy_and_cancel_mirrored_orphans([], replicable)

        asyncio.run(run_grace())
        assert synchronizer.get_mirrored_orphan_grace_started_at() is not None


class TestScenarioMIdleAndEpisodeCleared:
    """
    Scenario M — Idle / aligned episode cleared logging.

    Trigger: grace_total becomes zero after a prior deferral (or never deferred).
    Expected: episode-cleared log only after prior defer; elapsed path does not clear that way.
    """
    _EPISODE_CLEARED_SNIPPET = "Mirrored open-order grace episode cleared"
    _CANCEL_DEFERRED_SNIPPET = "Mirrored orphan cancel deferred"
    _GRACE_ELAPSED_SNIPPET = "Mirrored orphan grace elapsed after"

    def _sync_late_fill_only_defer_setup(self, *, frozen_reference_time: float):
        assets = _eth_usdt_pair_assets()
        compliant_snapshot = _copied_account(
            updated_at=frozen_reference_time - 1.0,
            copied_assets=assets,
            orders=[],
        )
        reference = _copied_account(
            updated_at=frozen_reference_time,
            copied_assets=assets,
            orders=[],
            historical_snapshots=[compliant_snapshot],
        )
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        copy_settings = copy_entities.AccountCopySettings(
            mirrored_orphan_cancel_grace_seconds=60.0,
            mirrored_orphan_grace_abort_threshold=3,
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_settings,
        )
        return synchronizer, _replicable_buy_limit_order()

    def test_idle_no_episode_cleared_log_when_never_deferred(self, caplog):
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            _copied_account(),
            mock.MagicMock(),
            copy_entities.AccountCopySettings(),
        )
        with caplog.at_level(logging.INFO):
            asyncio.run(synchronizer._apply_grace_policy_and_cancel_mirrored_orphans([], []))
        assert self._EPISODE_CLEARED_SNIPPET not in caplog.text

    def test_episode_cleared_log_after_defer_then_grace_total_zero(self, caplog):
        frozen_t0 = 1_700_000_000.0
        synchronizer, order = self._sync_late_fill_only_defer_setup(frozen_reference_time=frozen_t0)
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ):
            with caplog.at_level(logging.INFO):
                asyncio.run(
                    synchronizer._apply_grace_policy_and_cancel_mirrored_orphans([], [order])
                )
        assert self._EPISODE_CLEARED_SNIPPET not in caplog.text
        assert self._CANCEL_DEFERRED_SNIPPET in caplog.text
        assert "ref-late-1" in caplog.text
        assert "late-reference-fill candidate(s):" in caplog.text

        caplog.clear()
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ):
            with caplog.at_level(logging.INFO):
                asyncio.run(synchronizer._apply_grace_policy_and_cancel_mirrored_orphans([], []))
        assert caplog.text.count(self._EPISODE_CLEARED_SNIPPET) == 1

    def test_no_episode_cleared_after_grace_elapsed_flag_reset(self, caplog):
        frozen_t0 = 1_700_000_000.0
        synchronizer, order = self._sync_late_fill_only_defer_setup(frozen_reference_time=frozen_t0)
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ):
            with caplog.at_level(logging.INFO):
                asyncio.run(
                    synchronizer._apply_grace_policy_and_cancel_mirrored_orphans([], [order])
                )
        assert self._CANCEL_DEFERRED_SNIPPET in caplog.text

        caplog.clear()
        elapsed_time = frozen_t0 + 70.0
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=elapsed_time,
        ):
            with caplog.at_level(logging.INFO):
                asyncio.run(
                    synchronizer._apply_grace_policy_and_cancel_mirrored_orphans([], [order])
                )
        assert self._GRACE_ELAPSED_SNIPPET in caplog.text

        caplog.clear()
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=elapsed_time,
        ):
            with caplog.at_level(logging.INFO):
                asyncio.run(synchronizer._apply_grace_policy_and_cancel_mirrored_orphans([], []))
        assert self._EPISODE_CLEARED_SNIPPET not in caplog.text


class TestScenarioAGracePeriodCompletionLogging:
    """
    Scenario A — Late fill sync completion uses grace summary.

    Trigger: synchronize while late-fill grace skips upserts.
    Expected: completion log says Grace period active; not Failed to replicate.
    """
    def _grace_period_synchronize_setup(self, *, frozen_reference_time: float):
        order = _replicable_buy_limit_order()
        assets = _eth_usdt_pair_assets()
        compliant_snapshot = _copied_account(
            updated_at=frozen_reference_time - 1.0,
            copied_assets=assets,
            orders=[],
        )
        reference = _copied_account(
            updated_at=frozen_reference_time,
            copied_assets=assets,
            orders=[order],
            historical_snapshots=[compliant_snapshot],
        )
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        copy_settings = copy_entities.AccountCopySettings(
            mirrored_orphan_cancel_grace_seconds=60.0,
            mirrored_orphan_grace_abort_threshold=3,
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_settings,
        )
        return synchronizer

    def test_completion_uses_grace_summary_not_replication_failure(self, caplog):
        frozen_t0 = 1_700_000_000.0
        synchronizer = self._grace_period_synchronize_setup(frozen_reference_time=frozen_t0)
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ):
            with caplog.at_level(logging.INFO):
                asyncio.run(synchronizer.synchronize())

        completion_logs = [
            record.message
            for record in caplog.records
            if record.message.startswith("Order mirror completed:")
        ]
        assert len(completion_logs) == 1
        completion_message = completion_logs[0]
        assert "Grace period active for" in completion_message
        assert "ref-late-1" in completion_message
        assert "Failed to replicate" not in completion_message


class TestScenarioAGraceIdentified:
    """
    Scenario A — Grace identified for late-fill window.

    Trigger: late-fill grace active, idle, or wall-clock elapsed.
    Expected: is_mirrored_orphan_grace_identified True only while window active with grace items.
    """
    def _late_fill_grace_synchronizer_setup(
        self,
        *,
        frozen_reference_time: float,
        orders: list[protocol_models.Order],
        copy_settings: typing.Optional[copy_entities.AccountCopySettings] = None,
    ):
        assets = _eth_usdt_pair_assets()
        compliant_snapshot = _copied_account(
            updated_at=frozen_reference_time - 1.0,
            copied_assets=assets,
            orders=[],
        )
        reference = _copied_account(
            updated_at=frozen_reference_time,
            copied_assets=assets,
            orders=orders,
            historical_snapshots=[compliant_snapshot],
        )
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_settings or copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=3,
            ),
        )
        return synchronizer

    def test_true_when_late_fill_grace_window_active(self):
        frozen_t0 = 1_700_000_000.0
        synchronizer = self._late_fill_grace_synchronizer_setup(
            frozen_reference_time=frozen_t0,
            orders=[_replicable_buy_limit_order()],
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ):
            assert synchronizer.is_mirrored_orphan_grace_identified() is True

    def test_false_when_no_grace_items(self):
        reference = _copied_account(
            copied_assets=_eth_usdt_pair_assets(eth_ratio=0.25, usdt_ratio=0.5),
            orders=[_replicable_buy_limit_order()],
        )
        currency_totals = {
            "ETH": decimal.Decimal("1"),
            "USDT": decimal.Decimal("10000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(mirrored_orphan_cancel_grace_seconds=60.0),
        )
        assert synchronizer.is_mirrored_orphan_grace_identified() is False

    def test_false_when_grace_window_elapsed(self):
        frozen_t0 = 1_700_000_000.0
        synchronizer = self._late_fill_grace_synchronizer_setup(
            frozen_reference_time=frozen_t0,
            orders=[_replicable_buy_limit_order()],
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0 + 120.0,
        ):
            assert synchronizer.is_mirrored_orphan_grace_identified() is False


class TestScenarioLCountUnmirroredReferenceOrders:
    """
    Scenario L — Count unmirrored reference orders (bypass counter).

    Trigger: some reference ids have open mirrors, others do not.
    Expected: count equals reference orders without a matching open copier mirror.
    """
    def test_counts_only_reference_orders_without_open_copier_mirror(self):
        first_order = _replicable_buy_limit_order(order_id="mirror-1")
        second_order = _replicable_buy_limit_order(order_id="missing-1")
        reference = _copied_account(orders=[first_order, second_order])
        exchange_if = mock.MagicMock()
        exchange_if.orders.get_open_orders = mock.Mock(
            return_value=[_mirrored_eth_buy_order_stub("mirror-1")]
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(),
        )
        replicable = synchronizer._get_replicable_reference_orders()
        assert synchronizer._count_unmirrored_reference_orders(replicable) == 1


class TestScenarioLMissingMirrorBypass:
    """
    Scenario L — Missing-mirror bypass when count exceeds threshold.

    Trigger: grace active with late fill; many reference orders missing on copier.
    Expected: bypass when missing > threshold; skip upserts when missing equals threshold; no bypass if grace not identified.
    """
    def _grace_active_synchronizer_with_orders(
        self,
        *,
        frozen_reference_time: float,
        orders: list[protocol_models.Order],
        abort_threshold: int,
        late_fill_order_ids: set[str],
    ):
        assets = _eth_usdt_pair_assets()
        compliant_snapshot = _copied_account(
            updated_at=frozen_reference_time - 1.0,
            copied_assets=assets,
            orders=[],
        )
        reference = _copied_account(
            updated_at=frozen_reference_time,
            copied_assets=assets,
            orders=orders,
            historical_snapshots=[compliant_snapshot],
        )
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=abort_threshold,
            ),
        )

        original_is_late_reference_fill = synchronizer._is_late_reference_fill_for_order

        def late_fill_side_effect(order, orphan_orders, reference_state=None):
            if str(order.id) in late_fill_order_ids:
                return original_is_late_reference_fill(order, orphan_orders, reference_state)
            return False

        synchronizer._is_late_reference_fill_for_order = late_fill_side_effect
        return synchronizer

    def test_bypasses_grace_when_missing_exceed_threshold(self, caplog):
        frozen_t0 = 1_700_000_000.0
        orders = [
            _replicable_buy_limit_order(order_id=f"ref-order-{order_index}")
            for order_index in range(3)
        ]
        synchronizer = self._grace_active_synchronizer_with_orders(
            frozen_reference_time=frozen_t0,
            orders=orders,
            abort_threshold=2,
            late_fill_order_ids={"ref-order-0"},
        )
        created_order = mock.Mock()
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ):
            with mock.patch.object(
                synchronizer,
                "_upsert_mirrored_reference_order",
                mock.AsyncMock(return_value=([created_order], 0, 0, None)),
            ):
                with caplog.at_level(logging.INFO):
                    created = asyncio.run(synchronizer.synchronize())

        assert created == [created_order] * 3
        assert any(
            "Bypassing mirrored orphan grace: 3 reference order(s)" in record.message
            for record in caplog.records
        )

    def test_does_not_bypass_when_missing_equals_threshold(self, caplog):
        frozen_t0 = 1_700_000_000.0
        orders = [
            _replicable_buy_limit_order(order_id=f"ref-order-{order_index}")
            for order_index in range(2)
        ]
        synchronizer = self._grace_active_synchronizer_with_orders(
            frozen_reference_time=frozen_t0,
            orders=orders,
            abort_threshold=2,
            late_fill_order_ids={"ref-order-0"},
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ):
            with mock.patch.object(
                synchronizer,
                "_upsert_mirrored_reference_order",
                mock.AsyncMock(return_value=([], 0, 0, None)),
            ):
                with caplog.at_level(logging.INFO):
                    created = asyncio.run(synchronizer.synchronize())

        assert created == []
        assert not any(
            "Bypassing mirrored orphan grace" in record.message
            for record in caplog.records
        )
        assert any(
            "Skipped reference mirror upsert for 2 order(s)" in record.message
            for record in caplog.records
        )

    def test_does_not_bypass_when_grace_not_identified(self, caplog):
        frozen_t0 = 1_700_000_000.0
        orders = [
            _replicable_buy_limit_order(order_id=f"ref-order-{order_index}")
            for order_index in range(2)
        ]
        reference = _copied_account(
            updated_at=frozen_t0,
            copied_assets=_eth_usdt_pair_assets(eth_ratio=0.25, usdt_ratio=0.5),
            orders=orders,
        )
        currency_totals = {
            "ETH": decimal.Decimal("1"),
            "USDT": decimal.Decimal("10000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=2,
            ),
        )
        abort_spy = mock.Mock(wraps=synchronizer.abort_mirrored_orphan_grace)
        synchronizer.abort_mirrored_orphan_grace = abort_spy
        with mock.patch.object(
            synchronizer,
            "_upsert_mirrored_reference_order",
            mock.AsyncMock(return_value=([], 0, 0, None)),
        ):
            with caplog.at_level(logging.INFO):
                asyncio.run(synchronizer.synchronize())

        abort_spy.assert_not_called()
        assert not any(
            "Bypassing mirrored orphan grace" in record.message
            for record in caplog.records
        )


class TestScenarioLGridTwentyMissingMirrorBypass:
    """
    Scenario L — Grid twenty missing-mirror bypass without rebalance abort.

    Trigger: 20 reference limits, one late-fill candidate, zero open mirrors.
    Expected: synchronize bypasses grace via missing count and upserts all 20.
    """

    def _grid_post_rebalance_grace_synchronizer(self, *, frozen_reference_time: float):
        # 20 reference limits on one symbol (grid); copier has none â€” limits were cancelled before rebalance
        grid_orders = [
            _replicable_buy_limit_order(
                order_id=f"ref-order-{order_index}",
                price=decimal.Decimal("2000") - decimal.Decimal(order_index),
                created_ts=frozen_reference_time,
            )
            for order_index in range(20)
        ]
        assets = _eth_usdt_pair_assets()
        # Compliant historical snapshot: required for grace window / pair-ratio checks
        compliant_snapshot = _copied_account(
            updated_at=frozen_reference_time - 1.0,
            copied_assets=assets,
            orders=[],
        )
        reference = _copied_account(
            updated_at=frozen_reference_time,
            copied_assets=assets,
            orders=grid_orders,
            historical_snapshots=[compliant_snapshot],
        )
        # Postâ€“market-buy copier holdings: skewed vs reference snapshot so late-fill heuristic can match one order
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        # Default abort threshold from production settings
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=2,
            ),
        )
        # Only one late-fill candidate (grace_total=1); mirrors log where 20 missing â‰  20 grace items
        original_is_late_reference_fill = synchronizer._is_late_reference_fill_for_order
        late_fill_order_ids = {"ref-order-0"}

        def late_fill_side_effect(order, orphan_orders, reference_state=None):
            if str(order.id) in late_fill_order_ids:
                return original_is_late_reference_fill(order, orphan_orders, reference_state)
            return False

        synchronizer._is_late_reference_fill_for_order = late_fill_side_effect
        return synchronizer

    def test_creates_twenty_limits_via_missing_mirror_bypass_without_rebalance_abort(self, caplog):
        frozen_t0 = 1_700_000_000.0
        synchronizer = self._grid_post_rebalance_grace_synchronizer(frozen_reference_time=frozen_t0)
        abort_spy = mock.Mock(wraps=synchronizer.abort_mirrored_orphan_grace)
        synchronizer.abort_mirrored_orphan_grace = abort_spy
        upsert_mock = mock.AsyncMock(
            side_effect=lambda order: ([mock.Mock(name=f"created-{order.id}")], 0, 0, None)
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ):
            # Grace is active before sync; no abort_mirrored_orphan_grace() â€” rebalance bypass path not used
            assert synchronizer.is_mirrored_orphan_grace_identified() is True
            with mock.patch.object(synchronizer, "_upsert_mirrored_reference_order", upsert_mock):
                with caplog.at_level(logging.INFO):
                    created = asyncio.run(synchronizer.synchronize())

        # synchronize() alone must bypass grace via missing_count (20) > threshold (2)
        abort_spy.assert_called_once()
        assert upsert_mock.await_count == 20
        # All symbol-level skips cleared after bypass; every limit upserted
        assert len(created) == 20
        assert any(
            "Bypassing mirrored orphan grace: 20 reference order(s) "
            "missing on copier (> abort threshold 2)" in record.message
            for record in caplog.records
        )
        assert not any(
            "Skipped reference mirror upsert for 20 order(s)" in record.message
            for record in caplog.records
        )


class TestScenarioFExplicitAbort:
    """
    Scenario F — Explicit abort_mirrored_orphan_grace.

    Trigger: late-fill grace active; then abort_mirrored_orphan_grace before second sync.
    Expected: first sync skips upserts; second sync after abort creates mirrors.
    """
    def test_manual_abort_allows_upsert_while_grace_active(self, caplog):
        frozen_t0 = 1_700_000_000.0
        assets = _eth_usdt_pair_assets()
        compliant_snapshot = _copied_account(
            updated_at=frozen_t0 - 1.0,
            copied_assets=assets,
            orders=[],
        )
        reference = _copied_account(
            updated_at=frozen_t0,
            copied_assets=assets,
            orders=[_replicable_buy_limit_order()],
            historical_snapshots=[compliant_snapshot],
        )
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[])
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=3,
            ),
        )
        created_order = mock.Mock()
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ):
            with mock.patch.object(
                synchronizer,
                "_upsert_mirrored_reference_order",
                mock.AsyncMock(return_value=([created_order], 0, 0, None)),
            ):
                with caplog.at_level(logging.INFO):
                    blocked_created = asyncio.run(synchronizer.synchronize())
                    synchronizer.abort_mirrored_orphan_grace()
                    allowed_created = asyncio.run(synchronizer.synchronize())

        assert blocked_created == []
        assert allowed_created == [created_order]
        assert any(
            "Skipped reference mirror upsert for 1 order(s)" in record.message
            for record in caplog.records
        )


def _replicable_buy_limit_order_id(order_id: str) -> protocol_models.Order:
    return _replicable_buy_limit_order(order_id=order_id)


def _mirrored_eth_buy_order_stub(order_id: str) -> mock.Mock:
    mirrored = mock.Mock()
    mirrored.tag = copy_constants.MIRRORED_ORDER_TAG
    mirrored.order_id = order_id
    mirrored.symbol = "ETH/USDT"
    mirrored.side = trading_enums.TradeOrderSide.BUY
    mirrored.origin_price = decimal.Decimal("2000")
    mirrored.origin_quantity = decimal.Decimal("1")
    return mirrored


class TestScenarioJMissedHistoricalSignals:
    """
    Scenario J — Missed historical signals grace abort.

    Trigger: first compliant snapshot index at missed_signals threshold; orphan still open.
    Expected: abort flag True; apply_grace cancels orphan immediately.
    """
    def test_is_aborted_when_first_compliant_snapshot_index_at_threshold(self):
        order_m1 = _replicable_buy_limit_order_id("m1")
        order_m2 = _replicable_buy_limit_order_id("m2")
        assets = _eth_usdt_pair_assets()
        empty_snapshot = _copied_account(
            updated_at=time.time(),
            copied_assets=assets,
            orders=[],
        )
        empty_snapshot_mid = _copied_account(
            updated_at=time.time() - 1.0,
            copied_assets=assets,
            orders=[],
        )
        compliant_snapshot = _copied_account(
            updated_at=time.time() - 5.0,
            copied_assets=assets,
            orders=[order_m1, order_m2],
        )
        live_reference = _copied_account(
            updated_at=time.time(),
            copied_assets=assets,
            orders=[order_m1],
            historical_snapshots=[empty_snapshot, empty_snapshot_mid, compliant_snapshot],
        )
        mirror_m1 = _mirrored_eth_buy_order_stub("m1")
        mirror_m2 = _mirrored_eth_buy_order_stub("m2")
        exchange_if = mock.MagicMock()
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[mirror_m1, mirror_m2])
        exchange_if.portfolio.reference_market = "USDT"
        exchange_if.portfolio.get_currency_portfolio_total = mock.Mock(
            return_value=decimal.Decimal("1")
        )
        exchange_if.market.get_potentially_outdated_price = mock.Mock(
            return_value=(decimal.Decimal("2000"), False)
        )
        copy_settings = copy_entities.AccountCopySettings(
            mirrored_orphan_cancel_grace_seconds=60.0,
            mirrored_orphan_grace_abort_threshold=2,
            missed_signals_grace_abort_threshold=2,
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            live_reference,
            exchange_if,
            copy_settings,
        )
        assert synchronizer.is_mirrored_orphan_grace_aborted_for_missed_historical_signals() is True

    def test_apply_grace_cancels_immediately_when_missed_signals_abort(self):
        order_m1 = _replicable_buy_limit_order_id("m1")
        order_m2 = _replicable_buy_limit_order_id("m2")
        assets = _eth_usdt_pair_assets()
        empty_snapshot = _copied_account(
            updated_at=time.time(),
            copied_assets=assets,
            orders=[],
        )
        empty_snapshot_mid = _copied_account(
            updated_at=time.time() - 1.0,
            copied_assets=assets,
            orders=[],
        )
        compliant_snapshot = _copied_account(
            updated_at=time.time() - 5.0,
            copied_assets=assets,
            orders=[order_m1, order_m2],
        )
        live_reference = _copied_account(
            updated_at=time.time(),
            copied_assets=assets,
            orders=[order_m1],
            historical_snapshots=[empty_snapshot, empty_snapshot_mid, compliant_snapshot],
        )
        mirror_m1 = _mirrored_eth_buy_order_stub("m1")
        mirror_m2 = _mirrored_eth_buy_order_stub("m2")
        exchange_if = mock.MagicMock()
        # Two open mirrors so empty-order snapshots see grace_total>=threshold and stay non-compliant;
        # otherwise a single orphan snapshot "complies" and missed-signals abort never triggers.
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[mirror_m1, mirror_m2])
        exchange_if.orders.cancel_order = mock.AsyncMock()
        exchange_if.portfolio.reference_market = "USDT"
        currency_totals = {
            "ETH": decimal.Decimal("1"),
            "USDT": decimal.Decimal("10000"),
        }
        exchange_if.portfolio.get_currency_portfolio_total = mock.Mock(
            side_effect=lambda currency: currency_totals[currency]
        )
        exchange_if.market.get_potentially_outdated_price = mock.Mock(
            return_value=(decimal.Decimal("2000"), False)
        )
        copy_settings = copy_entities.AccountCopySettings(
            mirrored_orphan_cancel_grace_seconds=60.0,
            mirrored_orphan_grace_abort_threshold=2,
            missed_signals_grace_abort_threshold=2,
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            live_reference,
            exchange_if,
            copy_settings,
        )
        replicable = synchronizer._get_replicable_reference_orders()

        async def run_grace():
            return await synchronizer._apply_grace_policy_and_cancel_mirrored_orphans(
                [mirror_m2],
                replicable,
            )

        asyncio.run(run_grace())
        exchange_if.orders.cancel_order.assert_called_once_with(mirror_m2)


def _mirrored_limit_orphan_stub(
    *,
    order_id: str,
    symbol: str = "ETH/USDT",
    side=trading_enums.TradeOrderSide.BUY,
    price: decimal.Decimal = decimal.Decimal("2000"),
    quantity: decimal.Decimal = decimal.Decimal("1"),
):
    orphan = mock.Mock()
    orphan.tag = copy_constants.MIRRORED_ORDER_TAG
    orphan.order_id = order_id
    orphan.exchange_order_id = f"ex-{order_id}"
    orphan.symbol = symbol
    orphan.side = side
    orphan.origin_price = price
    orphan.origin_quantity = quantity
    orphan.order_type = (
        trading_enums.TraderOrderType.BUY_LIMIT
        if side is trading_enums.TradeOrderSide.BUY
        else trading_enums.TraderOrderType.SELL_LIMIT
    )
    orphan.creation_time = time.time() - 10.0
    orphan.timestamp = orphan.creation_time
    orphan.status = trading_enums.OrderStatus.OPEN
    return orphan


def _grace_window_reference(
    *,
    frozen_reference_time: float,
    orders: list[protocol_models.Order],
    assets: typing.Optional[list] = None,
):
    pair_assets = assets or _eth_usdt_pair_assets()
    compliant_snapshot = _copied_account(
        updated_at=frozen_reference_time - 1.0,
        copied_assets=pair_assets,
        orders=[],
    )
    return _copied_account(
        updated_at=frozen_reference_time,
        copied_assets=pair_assets,
        orders=orders,
        historical_snapshots=[compliant_snapshot],
    )


class TestScenarioBDeferredTaggedOrphan:
    """
    Scenario B — Deferred tagged orphan at valid reference price.

    Trigger: tagged mirrored_order with bot id not in active reference; price still on grid;
    inside grace window; pair-ratio OK.
    Expected: cancel_order not called for that orphan; symbol upserts skipped.
    """

    def test_orphan_cancel_deferred_while_grace_active(self):
        frozen_t0 = 1_700_000_000.0
        reference_order = _replicable_buy_limit_order(order_id="ref-active-1")
        orphan = _mirrored_limit_orphan_stub(order_id="stale-orphan-1", price=decimal.Decimal("2000"))
        # Pair-ratio eligible: copier holdings match simulated post-orphan-fill vs reference share.
        currency_totals = {
            "ETH": decimal.Decimal("1"),
            "USDT": decimal.Decimal("10000"),
        }
        reference = _grace_window_reference(
            frozen_reference_time=frozen_t0,
            orders=[reference_order],
            assets=_eth_usdt_pair_assets(eth_ratio=0.25, usdt_ratio=0.5),
        )
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[orphan])
        exchange_if.orders.cancel_order = mock.AsyncMock()
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=3,
            ),
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ):
            cancelled = asyncio.run(
                synchronizer._apply_grace_policy_and_cancel_mirrored_orphans(
                    [orphan],
                    synchronizer._get_replicable_reference_orders(),
                )
            )
        assert cancelled == 0
        exchange_if.orders.cancel_order.assert_not_called()


class TestScenarioCOrphanAndLateFillTogether:
    """
    Scenario C — Orphan + late fill together during grace.

    Trigger: tagged orphan and late-fill candidate both under abort threshold; inside grace.
    Expected: orphan cancel deferred; upserts skipped on symbol.
    """

    def test_defer_orphan_and_skip_upserts(self, caplog):
        frozen_t0 = 1_700_000_000.0
        late_fill_order = _replicable_buy_limit_order(order_id="ref-late-1")
        orphan = _mirrored_limit_orphan_stub(order_id="stale-orphan-1", price=decimal.Decimal("2000"))
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        reference = _grace_window_reference(
            frozen_reference_time=frozen_t0,
            orders=[late_fill_order],
        )
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[orphan])
        exchange_if.orders.cancel_order = mock.AsyncMock()
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=3,
            ),
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ), mock.patch.object(
            synchronizer,
            "_mirrored_orphan_batch_eligible_for_grace",
            return_value=True,
        ), mock.patch.object(
            synchronizer,
            "_upsert_mirrored_reference_order",
            mock.AsyncMock(return_value=([], 0, 0, None)),
        ):
            with caplog.at_level(logging.INFO):
                created = asyncio.run(synchronizer.synchronize())
        assert created == []
        exchange_if.orders.cancel_order.assert_not_called()
        assert any(
            "Skipped reference mirror upsert" in record.message
            for record in caplog.records
        )


class TestScenarioDWrongPriceStrayDuringGrace:
    """
    Scenario D — Wrong-price stray during active grace.

    Trigger: late-fill grace active and an open limit at a price not in the reference grid.
    Expected: stray cancelled; upserts still skipped; valid-price opens kept.
    """

    def test_synchronize_cancels_wrong_price_stray_keeps_grace_skip(self, caplog):
        frozen_t0 = 1_700_000_000.0
        reference_order = _replicable_buy_limit_order(order_id="ref-late-1")
        matched = _mirrored_limit_orphan_stub(
            order_id=str(reference_order.id),
            price=decimal.Decimal("2000"),
        )
        stray = _mirrored_limit_orphan_stub(
            order_id="wrong-price-1",
            price=decimal.Decimal("1500"),
        )
        stray.tag = None
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        reference = _grace_window_reference(
            frozen_reference_time=frozen_t0,
            orders=[reference_order],
        )
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        open_orders = [stray, matched]

        def get_open_orders(symbol=None):
            if symbol is None or symbol == "ETH/USDT":
                return list(open_orders)
            return []

        exchange_if.orders.get_open_orders = mock.Mock(side_effect=get_open_orders)

        async def cancel_side_effect(order):
            if order in open_orders:
                open_orders.remove(order)

        exchange_if.orders.cancel_order = mock.AsyncMock(side_effect=cancel_side_effect)
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=3,
            ),
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ), mock.patch.object(
            synchronizer,
            "_reference_symbols_skipped_while_grace_orphans_uncancelled",
            return_value={"ETH/USDT"},
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
        assert matched in open_orders
        assert any(
            "Skipped reference mirror upsert" in record.message
            for record in caplog.records
        )


class TestScenarioEGraceElapsedCancelOrphans:
    """
    Scenario E — Grace elapsed cancels tagged orphans.

    Trigger: tagged orphan still open after grace_seconds from started_at.
    Expected: cancel_order called; grace elapsed log.
    """

    def test_cancels_tagged_orphan_when_grace_elapsed(self, caplog):
        frozen_t0 = 1_700_000_000.0
        reference_order = _replicable_buy_limit_order(order_id="ref-active-1")
        orphan = _mirrored_limit_orphan_stub(order_id="stale-orphan-1")
        currency_totals = {
            "ETH": decimal.Decimal("1"),
            "USDT": decimal.Decimal("10000"),
        }
        reference = _grace_window_reference(
            frozen_reference_time=frozen_t0,
            orders=[reference_order],
            assets=_eth_usdt_pair_assets(eth_ratio=0.25, usdt_ratio=0.5),
        )
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[orphan])
        exchange_if.orders.cancel_order = mock.AsyncMock()
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=3,
            ),
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0 + 70.0,
        ):
            with caplog.at_level(logging.INFO):
                cancelled = asyncio.run(
                    synchronizer._apply_grace_policy_and_cancel_mirrored_orphans(
                        [orphan],
                        synchronizer._get_replicable_reference_orders(),
                    )
                )
        assert cancelled == 1
        exchange_if.orders.cancel_order.assert_awaited_once_with(orphan)
        assert "Mirrored orphan grace elapsed after" in caplog.text


class TestScenarioGGraceDisabled:
    """
    Scenario G — Grace disabled (grace_seconds <= 0).

    Trigger: mirrored_orphan_cancel_grace_seconds is 0 with a tagged orphan.
    Expected: immediate orphan cancel; skip symbol set empty.
    """

    def test_immediate_orphan_cancel_when_grace_seconds_zero(self):
        orphan = _mirrored_limit_orphan_stub(order_id="stale-orphan-1")
        reference = _copied_account(
            copied_assets=_eth_usdt_pair_assets(),
            orders=[_replicable_buy_limit_order()],
        )
        exchange_if = _exchange_interface_stub(
            currency_totals={"ETH": decimal.Decimal("1"), "USDT": decimal.Decimal("10000")},
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[orphan])
        exchange_if.orders.cancel_order = mock.AsyncMock()
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(mirrored_orphan_cancel_grace_seconds=0.0),
        )
        cancelled = asyncio.run(
            synchronizer._apply_grace_policy_and_cancel_mirrored_orphans(
                [orphan],
                synchronizer._get_replicable_reference_orders(),
            )
        )
        assert cancelled == 1
        exchange_if.orders.cancel_order.assert_awaited_once_with(orphan)
        assert synchronizer._reference_symbols_skipped_while_grace_orphans_uncancelled(
            synchronizer._get_replicable_reference_orders()
        ) == set()


class TestScenarioHGraceTotalAtOrAboveThreshold:
    """
    Scenario H — grace_total >= abort threshold.

    Trigger: orphan count reaches mirrored_orphan_grace_abort_threshold (empty history).
    Expected: immediate cancel of orphans; threshold abort log.
    """

    def test_cancels_immediately_when_grace_total_reaches_threshold(self, caplog):
        frozen_t0 = 1_700_000_000.0
        orphan_a = _mirrored_limit_orphan_stub(order_id="orphan-a")
        orphan_b = _mirrored_limit_orphan_stub(order_id="orphan-b", price=decimal.Decimal("1999"))
        reference_order = _replicable_buy_limit_order(order_id="ref-1")
        # Empty history: not "invalid"; threshold abort is the path under test.
        reference = _copied_account(
            updated_at=frozen_t0,
            copied_assets=_eth_usdt_pair_assets(eth_ratio=0.25, usdt_ratio=0.5),
            orders=[reference_order],
            historical_snapshots=[],
        )
        exchange_if = _exchange_interface_stub(
            currency_totals={"ETH": decimal.Decimal("1"), "USDT": decimal.Decimal("10000")},
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[orphan_a, orphan_b])
        exchange_if.orders.cancel_order = mock.AsyncMock()
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=2,
            ),
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ), mock.patch.object(
            synchronizer,
            "_mirrored_orphan_batch_eligible_for_grace",
            return_value=True,
        ):
            with caplog.at_level(logging.INFO):
                cancelled = asyncio.run(
                    synchronizer._apply_grace_policy_and_cancel_mirrored_orphans(
                        [orphan_a, orphan_b],
                        synchronizer._get_replicable_reference_orders(),
                    )
                )
        assert cancelled == 2
        assert any(
            "grace item(s) >= threshold" in record.message
            for record in caplog.records
        )


class TestScenarioINoCompliantHistoricalSnapshot:
    """
    Scenario I — No compliant historical snapshot.

    Trigger: non-empty history where no snapshot complies under grace checks.
    Expected: invalid grace; immediate orphan cancel; no-compliant-snapshot log.
    """

    def test_cancels_immediately_when_no_compliant_snapshot(self, caplog):
        orphan = _mirrored_limit_orphan_stub(order_id="orphan-1")
        # History with orders that keep grace_total high vs threshold so nothing complies.
        non_compliant = _copied_account(
            updated_at=time.time() - 1.0,
            copied_assets=_eth_usdt_pair_assets(),
            orders=[],
        )
        live = _copied_account(
            updated_at=time.time(),
            copied_assets=_eth_usdt_pair_assets(),
            orders=[_replicable_buy_limit_order()],
            historical_snapshots=[non_compliant],
        )
        exchange_if = _exchange_interface_stub(
            currency_totals={"ETH": decimal.Decimal("1"), "USDT": decimal.Decimal("10000")},
            market_price=decimal.Decimal("2000"),
        )
        # Two orphans so empty snapshot has grace_total >= threshold and is non-compliant.
        orphan_b = _mirrored_limit_orphan_stub(order_id="orphan-2", price=decimal.Decimal("1999"))
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[orphan, orphan_b])
        exchange_if.orders.cancel_order = mock.AsyncMock()
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            live,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=2,
            ),
        )
        assert synchronizer.is_mirrored_orphan_grace_invalid_no_compliant_snapshot() is True
        with caplog.at_level(logging.INFO):
            cancelled = asyncio.run(
                synchronizer._apply_grace_policy_and_cancel_mirrored_orphans(
                    [orphan, orphan_b],
                    synchronizer._get_replicable_reference_orders(),
                )
            )
        assert cancelled == 2
        assert any(
            "no compliant reference snapshot" in record.message
            for record in caplog.records
        )


class TestScenarioKApplyGraceWhenPairRatioFails:
    """
    Scenario K — Pair-ratio heuristic fails on apply-grace path.

    Trigger: tagged orphan present; batch pair-ratio eligibility False.
    Expected: orphans cancelled immediately via apply_grace.
    """

    def test_cancels_orphans_when_batch_ineligible(self, caplog):
        orphan = _mirrored_limit_orphan_stub(
            order_id="orphan-1",
            quantity=decimal.Decimal("1"),
            price=decimal.Decimal("2000"),
        )
        reference = _copied_account(
            copied_assets=_eth_usdt_pair_assets(eth_ratio=0.5, usdt_ratio=0.5),
            orders=[_replicable_buy_limit_order()],
            historical_snapshots=[
                _copied_account(
                    updated_at=time.time() - 1.0,
                    copied_assets=_eth_usdt_pair_assets(eth_ratio=0.5, usdt_ratio=0.5),
                    orders=[],
                )
            ],
        )
        # Copier holdings make simulated post-fill share mismatch reference (same as heuristic unit test).
        exchange_if = _exchange_interface_stub(
            currency_totals={"ETH": decimal.Decimal("1"), "USDT": decimal.Decimal("10000")},
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[orphan])
        exchange_if.orders.cancel_order = mock.AsyncMock()
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=3,
                mirrored_orphan_grace_pair_ratio_max_delta=decimal.Decimal("0.02"),
            ),
        )
        assert synchronizer._mirrored_orphan_batch_eligible_for_grace([orphan]) is False
        with caplog.at_level(logging.INFO):
            cancelled = asyncio.run(
                synchronizer._apply_grace_policy_and_cancel_mirrored_orphans(
                    [orphan],
                    synchronizer._get_replicable_reference_orders(),
                )
            )
        assert cancelled == 1
        exchange_if.orders.cancel_order.assert_awaited_once_with(orphan)


class TestScenarioNDuplicateNoGraceCrossRef:
    """
    Scenario N — Duplicate at valid price with grace idle.

    Trigger: open mirrors match active reference ids (no orphan / late-fill grace items).
    Expected: grace not identified; authoritative duplicate cancel coverage is reconciliation R2.
    """

    def test_grace_not_identified_when_mirrors_match_reference(self):
        reference_order = _replicable_buy_limit_order(order_id="ref-1")
        mirror = _mirrored_limit_orphan_stub(order_id="ref-1")
        reference = _copied_account(
            copied_assets=_eth_usdt_pair_assets(eth_ratio=0.25, usdt_ratio=0.5),
            orders=[reference_order],
        )
        exchange_if = _exchange_interface_stub(
            currency_totals={"ETH": decimal.Decimal("1"), "USDT": decimal.Decimal("10000")},
            market_price=decimal.Decimal("2000"),
        )
        exchange_if.orders.get_open_orders = mock.Mock(return_value=[mirror])
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(mirrored_orphan_cancel_grace_seconds=60.0),
        )
        assert synchronizer.is_mirrored_orphan_grace_identified() is False


class TestScenarioODuplicateDuringActiveGrace:
    """
    Scenario O — Duplicate at valid price during grace.

    Trigger: two opens at the same reference price; symbol in grace skip set.
    Expected: reconcile stray_only keeps both; upserts skipped; cancel_order not called.
    """

    def test_synchronize_keeps_same_price_duplicate_during_grace(self, caplog):
        frozen_t0 = 1_700_000_000.0
        reference_order = _replicable_buy_limit_order(order_id="ref-late-1")
        preferred = _mirrored_limit_orphan_stub(order_id="ref-late-1", price=decimal.Decimal("2000"))
        duplicate = _mirrored_limit_orphan_stub(order_id="extra-dup", price=decimal.Decimal("2000"))
        duplicate.tag = None
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        reference = _grace_window_reference(
            frozen_reference_time=frozen_t0,
            orders=[reference_order],
        )
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        open_orders = [preferred, duplicate]

        def get_open_orders(symbol=None):
            if symbol is None or symbol == "ETH/USDT":
                return list(open_orders)
            return []

        exchange_if.orders.get_open_orders = mock.Mock(side_effect=get_open_orders)
        exchange_if.orders.cancel_order = mock.AsyncMock()
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=3,
            ),
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ), mock.patch.object(
            synchronizer,
            "_reference_symbols_skipped_while_grace_orphans_uncancelled",
            return_value={"ETH/USDT"},
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
        exchange_if.orders.cancel_order.assert_not_called()
        assert preferred in open_orders and duplicate in open_orders
        assert any(
            "Skipped reference mirror upsert" in record.message
            for record in caplog.records
        )


class TestScenarioPGraceKeepsMirroredOrphanOffGrid:
    """
    Scenario P — Grace keeps mirrored orphan off-grid; cancels untagged.

    Trigger: grace skip symbols active; matched open + mirrored orphan at off-grid price + untagged stray.
    Expected: synchronize cancels only the untagged stray; mirrored orphan kept; upserts skipped.
    """

    def test_synchronize_keeps_mirrored_orphan_cancels_untagged(self, caplog):
        frozen_t0 = 1_700_000_000.0
        reference_order = _replicable_buy_limit_order(order_id="ref-late-1")
        matched = _mirrored_limit_orphan_stub(
            order_id=str(reference_order.id),
            price=decimal.Decimal("2000"),
        )
        mirrored_orphan = _mirrored_limit_orphan_stub(
            order_id="grid_ref_b1",
            price=decimal.Decimal("1500"),
        )
        untagged_stray = _mirrored_limit_orphan_stub(
            order_id="wrong-price-1",
            price=decimal.Decimal("1400"),
        )
        untagged_stray.tag = None
        currency_totals = {
            "ETH": decimal.Decimal("2"),
            "USDT": decimal.Decimal("8000"),
        }
        reference = _grace_window_reference(
            frozen_reference_time=frozen_t0,
            orders=[reference_order],
        )
        exchange_if = _exchange_interface_stub(
            currency_totals=currency_totals,
            market_price=decimal.Decimal("2000"),
        )
        open_orders = [matched, mirrored_orphan, untagged_stray]

        def get_open_orders(symbol=None):
            if symbol is None or symbol == "ETH/USDT":
                return list(open_orders)
            return []

        exchange_if.orders.get_open_orders = mock.Mock(side_effect=get_open_orders)

        async def cancel_side_effect(order):
            if order in open_orders:
                open_orders.remove(order)

        exchange_if.orders.cancel_order = mock.AsyncMock(side_effect=cancel_side_effect)
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_entities.AccountCopySettings(
                mirrored_orphan_cancel_grace_seconds=60.0,
                mirrored_orphan_grace_abort_threshold=3,
            ),
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=frozen_t0,
        ), mock.patch.object(
            synchronizer,
            "_reference_symbols_skipped_while_grace_orphans_uncancelled",
            return_value={"ETH/USDT"},
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
        exchange_if.orders.cancel_order.assert_awaited_once_with(untagged_stray)
        assert matched in open_orders
        assert mirrored_orphan in open_orders
        assert untagged_stray not in open_orders
        assert any(
            "Skipped reference mirror upsert" in record.message
            for record in caplog.records
        )
