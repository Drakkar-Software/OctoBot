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
import decimal
import logging
import time

import mock

import octobot_commons.constants as commons_constants
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_copy.orders_mirroring.orders_synchronizer as orders_synchronizer_module


def _reference_account_with_allocations(
    base_ratio: decimal.Decimal,
    quote_ratio: decimal.Decimal,
) -> copy_entities.Account:
    return copy_entities.Account(
        content={
            "ETH": {
                commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("1"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: base_ratio,
            },
            "USDT": {
                commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("10000"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: quote_ratio,
            },
        },
        orders=[],
    )


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
        reference = copy_entities.Account(
            content={
                "ETH": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("1"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
                },
            },
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
        assert simulated_share == reference_share


def _replicable_buy_limit_order(
    *,
    order_id: str = "ref-late-1",
    amount: decimal.Decimal = decimal.Decimal("1"),
    price: decimal.Decimal = decimal.Decimal("2000"),
) -> dict:
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: {
            trading_enums.ExchangeConstantsOrderColumns.ID.value: order_id,
            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "ETH/USDT",
            trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
            trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
            trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: amount,
            trading_enums.ExchangeConstantsOrderColumns.PRICE.value: price,
            trading_enums.ExchangeConstantsOrderColumns.STATUS.value: trading_enums.OrderStatus.OPEN.value,
        }
    }


def _replicable_buy_market_order(
    *,
    order_id: str = "ref-market-1",
    amount: decimal.Decimal = decimal.Decimal("1"),
    price: decimal.Decimal = decimal.Decimal("2000"),
) -> dict:
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: {
            trading_enums.ExchangeConstantsOrderColumns.ID.value: order_id,
            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "ETH/USDT",
            trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
            trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.MARKET.value,
            trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: amount,
            trading_enums.ExchangeConstantsOrderColumns.PRICE.value: price,
            trading_enums.ExchangeConstantsOrderColumns.STATUS.value: trading_enums.OrderStatus.OPEN.value,
        }
    }


class TestMarketOrderExclusion:
    def test_replicable_reference_orders_omit_market_include_limit(self):
        limit_order = _replicable_buy_limit_order(order_id="limit-1")
        market_order = _replicable_buy_market_order(order_id="market-1")
        reference = copy_entities.Account(
            content={},
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
        reference = copy_entities.Account(content={}, orders=[])
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
        reference = copy_entities.Account(
            content={
                "ETH": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("1"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.25"),
                },
                "USDT": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("10000"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
                },
            },
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
        reference = copy_entities.Account(
            content={
                "ETH": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("1"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.25"),
                },
                "USDT": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("10000"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
                },
            },
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
        compliant_snapshot = copy_entities.Account(
            updated_at=time.time() - 1.0,
            content={
                "ETH": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("1"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.25"),
                },
                "USDT": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("10000"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
                },
            },
            orders=[],
        )
        reference = copy_entities.Account(
            updated_at=time.time(),
            content={
                "ETH": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("1"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.25"),
                },
                "USDT": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("10000"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
                },
            },
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
        compliant_snapshot = copy_entities.Account(
            updated_at=frozen_reference_time - 1.0,
            content={
                "ETH": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("1"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.25"),
                },
                "USDT": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("10000"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
                },
            },
            orders=[],
        )
        reference = copy_entities.Account(
            updated_at=frozen_reference_time,
            content={
                "ETH": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("1"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.25"),
                },
                "USDT": {
                    commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("10000"),
                    copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
                },
            },
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
            copy_entities.Account(content={}, orders=[]),
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


def _replicable_buy_limit_order_id(order_id: str) -> dict:
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
        portfolio = {
            "ETH": {
                commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("1"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.25"),
            },
            "USDT": {
                commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("10000"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
            },
        }
        empty_snapshot = copy_entities.Account(
            updated_at=time.time(),
            content=portfolio,
            orders=[],
        )
        empty_snapshot_mid = copy_entities.Account(
            updated_at=time.time() - 1.0,
            content=portfolio,
            orders=[],
        )
        compliant_snapshot = copy_entities.Account(
            updated_at=time.time() - 5.0,
            content=portfolio,
            orders=[order_m1, order_m2],
        )
        live_reference = copy_entities.Account(
            updated_at=time.time(),
            content=portfolio,
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
        portfolio = {
            "ETH": {
                commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("1"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.25"),
            },
            "USDT": {
                commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("10000"),
                copy_constants.PORTFOLIO_ASSET_ALLOCATION_RATIO: decimal.Decimal("0.5"),
            },
        }
        empty_snapshot = copy_entities.Account(
            updated_at=time.time(),
            content=portfolio,
            orders=[],
        )
        empty_snapshot_mid = copy_entities.Account(
            updated_at=time.time() - 1.0,
            content=portfolio,
            orders=[],
        )
        compliant_snapshot = copy_entities.Account(
            updated_at=time.time() - 5.0,
            content=portfolio,
            orders=[order_m1, order_m2],
        )
        live_reference = copy_entities.Account(
            updated_at=time.time(),
            content=portfolio,
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
