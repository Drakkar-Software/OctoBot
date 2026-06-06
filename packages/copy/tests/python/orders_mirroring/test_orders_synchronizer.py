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


class TestOrdersSynchronizerOrphanGraceHeuristic:
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


class TestLateReferenceFillHeuristic:
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


class TestApplyGraceGraceEpisodeClearedLogging:
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


class TestMissedHistoricalSignalsGraceAbort:
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


class TestMirroredOrderSelfLockCreditCompute:
    """open_mirrored_order credits this line's locked funds so repeat sync does not false quantity mismatch."""

    @staticmethod
    def _exchange_interface_for_compute(
        *,
        total_symbol: decimal.Decimal,
        total_market: decimal.Decimal,
        available_symbol: decimal.Decimal,
        available_market: decimal.Decimal,
        mark_price: decimal.Decimal,
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
        exchange_if = self._exchange_interface_for_compute(
            total_symbol=decimal.Decimal("10"),
            total_market=decimal.Decimal("10000"),
            available_symbol=decimal.Decimal("0.05"),
            available_market=decimal.Decimal("500"),
            mark_price=mark_price,
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            _copied_account(),
            exchange_if,
            copy_entities.AccountCopySettings(),
        )
        open_sell = mock.Mock()
        open_sell.side = trading_enums.TradeOrderSide.SELL
        open_sell.symbol = "ETH/USDT"
        open_sell.origin_price = mark_price
        open_sell.get_locked_quantity = mock.Mock(return_value=decimal.Decimal("1"))
        open_sell.get_computed_fee = mock.Mock(return_value=None)

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
        assert ideal_without == decimal.Decimal("2")
        assert ideal_with == decimal.Decimal("1.05")


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
