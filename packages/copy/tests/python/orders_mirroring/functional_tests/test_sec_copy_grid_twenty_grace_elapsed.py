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

import octobot_commons.constants as commons_constants
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


@contextlib.asynccontextmanager
async def _passthrough_mirror_sync_available_updates():
    yield


_SEC_COPY_GRID_BTC_USDT = "BTC/USDT"
_SEC_COPY_GRID_MARKET_PRICE = decimal.Decimal("65769.2")
_SEC_COPY_GRID_SKIPPED_LATE_FILL_ORDER_ID = "405e3275-aa3e-4afc-8f85-5fe4e027359d"
_SEC_COPY_GRID_REFERENCE_USDT_TOTAL = decimal.Decimal("506.1087160037")
_SEC_COPY_GRID_REFERENCE_BTC_TOTAL = decimal.Decimal("0.00780859")
_SEC_COPY_GRID_COPIER_USDT_TOTAL = decimal.Decimal("496.207928")
_SEC_COPY_GRID_COPIER_BTC_TOTAL = decimal.Decimal("0.00765234")


def _sec_copy_grid_btc_limit_order(
    order_id: str,
    *,
    side: protocol_models.Side,
    price: float,
    quantity: float,
    created_ts: float,
) -> protocol_models.Order:
    return protocol_models.Order(
        id=order_id,
        symbol=_SEC_COPY_GRID_BTC_USDT,
        price=price,
        quantity=quantity,
        filled=0.0,
        exchange_id=f"exchange-{order_id}",
        side=side,
        type=protocol_models.OrderType.LIMIT,
        trigger_above=side is protocol_models.Side.SELL,
        reduce_only=False,
        is_active=True,
        status=protocol_models.OrderStatus.OPEN,
        created_at=timestamp_util.utc_datetime_from_timestamp(created_ts),
    )


def _sec_copy_grid_twenty_reference_orders() -> list[protocol_models.Order]:
    # Order list and created_at timestamps from secCopy grid 20 production log (2026-06-16).
    grid_june_4 = 1_749_045_562.899
    grid_june_5 = 1_749_157_658.879
    grid_june_12 = 1_749_732_762.463
    grid_june_12_later = 1_749_757_782.704
    grid_june_16_morning = 1_750_056_957.196
    grid_june_16_afternoon = 1_750_088_473.088
    return [
        _sec_copy_grid_btc_limit_order(
            "8930fbf1-d7ea-4e7b-8b6a-a4b577d62e37",
            side=protocol_models.Side.SELL,
            price=68745.57,
            quantity=0.00074,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "8df4d79f-6c66-4a8c-9171-6935b9b136ba",
            side=protocol_models.Side.SELL,
            price=70245.57,
            quantity=0.00072,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "948e71f0-66f4-47c9-8114-24800352e04d",
            side=protocol_models.Side.SELL,
            price=71745.57,
            quantity=0.00071,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "01844572-9ecc-447a-ad3a-7921a25ce43e",
            side=protocol_models.Side.SELL,
            price=73245.57,
            quantity=0.00069,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "2ea19521-a361-4a56-8183-f15add6bcba2",
            side=protocol_models.Side.SELL,
            price=74745.57,
            quantity=0.00068,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "2c52c2ec-0d80-4037-b88b-cc033551e8a9",
            side=protocol_models.Side.SELL,
            price=76245.57,
            quantity=0.00067,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "1462ce5f-6188-4864-b973-0cf87d0f0ad5",
            side=protocol_models.Side.SELL,
            price=77745.57,
            quantity=0.00065,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "bbb58f2c-d1d4-4de6-9916-26a5fd15e44d",
            side=protocol_models.Side.SELL,
            price=79245.57,
            quantity=0.00064,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "dabfe054-a650-4a09-a296-8d22ceb6f664",
            side=protocol_models.Side.BUY,
            price=58245.57,
            quantity=0.00083,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "9a91d975-594d-4816-ab27-ea75620d57d9",
            side=protocol_models.Side.BUY,
            price=56745.57,
            quantity=0.00086,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "5726a555-71fb-4d7d-8c40-65f7827fc8af",
            side=protocol_models.Side.BUY,
            price=55245.57,
            quantity=0.00088,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "115ba645-093e-4b00-91e2-87c84d0f680e",
            side=protocol_models.Side.BUY,
            price=53745.57,
            quantity=0.0009,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "01088c8e-108d-4e9c-9286-377b6197ed1b",
            side=protocol_models.Side.BUY,
            price=52245.57,
            quantity=0.00093,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "d9cefd84-53df-4be2-8ef9-f8af0187010e",
            side=protocol_models.Side.BUY,
            price=50745.57,
            quantity=0.00096,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "0830c3a4-0cb8-4e11-8925-d8f91851de8d",
            side=protocol_models.Side.BUY,
            price=49245.57,
            quantity=0.00099,
            created_ts=grid_june_4,
        ),
        _sec_copy_grid_btc_limit_order(
            "7cf7e7ad-b3e4-4f6a-a2f5-1ecff2cc176f",
            side=protocol_models.Side.BUY,
            price=59745.57,
            quantity=0.00083,
            created_ts=grid_june_5,
        ),
        _sec_copy_grid_btc_limit_order(
            _SEC_COPY_GRID_SKIPPED_LATE_FILL_ORDER_ID,
            side=protocol_models.Side.BUY,
            price=61245.57,
            quantity=0.00024,
            created_ts=grid_june_12,
        ),
        _sec_copy_grid_btc_limit_order(
            "62cc9308-bcb5-4cd1-a3b8-06ea353bc83d",
            side=protocol_models.Side.BUY,
            price=62745.57,
            quantity=0.00078,
            created_ts=grid_june_12_later,
        ),
        _sec_copy_grid_btc_limit_order(
            "40de08e9-6164-4c26-9d29-0dc172723c51",
            side=protocol_models.Side.BUY,
            price=64245.57,
            quantity=0.00078,
            created_ts=grid_june_16_morning,
        ),
        _sec_copy_grid_btc_limit_order(
            "42c05638-6be9-4e95-bbd0-d1dea445a82b",
            side=protocol_models.Side.SELL,
            price=67245.57,
            quantity=0.00077,
            created_ts=grid_june_16_afternoon,
        ),
    ]


def _sec_copy_grid_reference_account(*, updated_at: float) -> protocol_models.CopiedAccount:
    return _copied_account(
        updated_at=updated_at,
        copied_assets=[
            protocol_models.CopiedAsset(
                name="USDT",
                total=float(_SEC_COPY_GRID_REFERENCE_USDT_TOTAL),
                available=2.5784974037,
                ratio=0.49617195458822816,
            ),
            protocol_models.CopiedAsset(
                name="BTC",
                total=float(_SEC_COPY_GRID_REFERENCE_BTC_TOTAL),
                available=0.00153859,
                ratio=0.5038280454117718,
            ),
        ],
        orders=_sec_copy_grid_twenty_reference_orders(),
    )


class _SecCopyGridPostRebalanceExchangeState:
    def __init__(self) -> None:
        self.btc_total = trading_constants.ZERO
        self.usdt_total = decimal.Decimal("1000")
        self.btc_available = trading_constants.ZERO
        self.usdt_available = decimal.Decimal("1000")
        self.open_orders: list[mock.Mock] = []
        self.symbol_market = mock.Mock()

    def apply_post_market_rebalance_holdings(self) -> None:
        self.btc_total = _SEC_COPY_GRID_COPIER_BTC_TOTAL
        self.usdt_total = _SEC_COPY_GRID_COPIER_USDT_TOTAL
        self.btc_available = _SEC_COPY_GRID_COPIER_BTC_TOTAL
        self.usdt_available = _SEC_COPY_GRID_COPIER_USDT_TOTAL

    def _pre_order_row(self, *, use_available: bool) -> tuple:
        btc_amount = self.btc_available if use_available else self.btc_total
        usdt_amount = self.usdt_available if use_available else self.usdt_total
        market_quantity = (
            usdt_amount / _SEC_COPY_GRID_MARKET_PRICE
            if _SEC_COPY_GRID_MARKET_PRICE
            else trading_constants.ZERO
        )
        return (
            btc_amount,
            usdt_amount,
            market_quantity,
            _SEC_COPY_GRID_MARKET_PRICE,
            self.symbol_market,
        )

    async def _get_pre_order_data(self, *, symbol: str, timeout, portfolio_type) -> tuple:
        del symbol, timeout
        use_available = portfolio_type is commons_constants.PORTFOLIO_AVAILABLE
        return self._pre_order_row(use_available=use_available)

    async def _create_orders(
        self,
        trader_order_type,
        symbol,
        current_price,
        ideal_quantity,
        market_or_limit_price,
        symbol_market,
        *,
        tag=None,
        order_id=None,
        raise_all_creation_error=False,
    ):
        del current_price, symbol_market, raise_all_creation_error
        if trader_order_type in (
            trading_enums.TraderOrderType.BUY_LIMIT,
            trading_enums.TraderOrderType.BUY_MARKET,
        ):
            trade_side = trading_enums.TradeOrderSide.BUY
            locked_quote = ideal_quantity * market_or_limit_price
            self.usdt_available -= locked_quote
        else:
            trade_side = trading_enums.TradeOrderSide.SELL
            self.btc_available -= ideal_quantity
        created_order = mock.Mock()
        created_order.symbol = symbol
        created_order.order_id = order_id
        created_order.side = trade_side
        created_order.order_type = trader_order_type
        created_order.origin_quantity = ideal_quantity
        created_order.origin_price = market_or_limit_price
        created_order.tag = tag
        created_order.get_locked_quantity = mock.Mock(return_value=ideal_quantity)
        created_order.get_computed_fee = mock.Mock(return_value=None)
        self.open_orders.append(created_order)
        return [created_order], []

    def build_exchange_interface(self) -> mock.MagicMock:
        exchange_if = mock.MagicMock()
        exchange_if.portfolio.reference_market = "USDT"
        exchange_if.portfolio.get_currency_portfolio_total = mock.Mock(
            side_effect=lambda currency: (
                self.usdt_total if currency == "USDT" else self.btc_total
            )
        )
        exchange_if.portfolio.mirror_sync_available_updates = _passthrough_mirror_sync_available_updates
        exchange_if.portfolio.refresh_portfolio = mock.AsyncMock(return_value=True)
        exchange_if.market.get_potentially_outdated_price = mock.Mock(
            return_value=(_SEC_COPY_GRID_MARKET_PRICE, False)
        )
        exchange_if.market.get_market_status = mock.Mock(return_value=self.symbol_market)
        exchange_if.market.is_market_open_for_order_type = mock.Mock(return_value=True)
        exchange_if.orders.get_open_orders = mock.Mock(side_effect=lambda: list(self.open_orders))
        exchange_if.orders.get_pre_order_data = mock.AsyncMock(side_effect=self._get_pre_order_data)
        exchange_if.orders.get_order_locked_amount = order_util.get_order_locked_amount
        exchange_if.orders.adapt_order_quantity_and_target_price_for_order_creation = mock.Mock(
            side_effect=lambda order_type, symbol, quantity, price, adapt_price_for_limit_orders=False: (
                price,
                quantity,
            )
        )
        exchange_if.orders.check_and_adapt_order_details_if_necessary = mock.Mock(
            side_effect=lambda symbol, quantity, limit_price: (
                [(quantity, limit_price)],
                self.symbol_market,
            )
        )
        exchange_if.orders.create_orders = mock.AsyncMock(side_effect=self._create_orders)
        exchange_if.orders.cancel_order = mock.AsyncMock()
        return exchange_if


class TestSynchronizeSecCopyGridTwentyGraceElapsedLateFillSkip:
    """
    Reproduces secCopy grid 20 first trigger (OctoBot - Copie (3).log): grace already elapsed,
    post-rebalance copier holdings, 20 reference limits — missing-mirror bypass creates all 20.
    """

    def test_creates_twenty_orders_when_grace_elapsed_after_market_rebalance(self, caplog):
        run_time = 1_781_622_900.0
        grace_seconds = 60.0
        reference_updated_at = 1_781_622_733.2078674
        assert (run_time - reference_updated_at) > grace_seconds

        reference = _sec_copy_grid_reference_account(updated_at=reference_updated_at)
        exchange_state = _SecCopyGridPostRebalanceExchangeState()
        exchange_if = exchange_state.build_exchange_interface()
        copy_settings = copy_entities.AccountCopySettings(
            mirrored_orphan_cancel_grace_seconds=grace_seconds,
            mirrored_orphan_grace_abort_threshold=2,
        )
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference,
            exchange_if,
            copy_settings,
        )

        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.time.time",
            return_value=run_time,
        ):
            # Same sequence as AccountCopier._resync_if_mirrored_open_order_grace_period_elapsed().
            synchronizer.abort_mirrored_orphan_grace()
            assert synchronizer._force_immediate_orphan_cancel_next is True
            # Pre-rebalance copier is 100% USDT (log: portfolio before market buy).
            asyncio.run(synchronizer.cancel_orders_pending_synchronization(None))
            assert synchronizer._force_immediate_orphan_cancel_next is False

            exchange_state.apply_post_market_rebalance_holdings()
            assert synchronizer.is_mirrored_orphan_grace_identified() is False

            with caplog.at_level(logging.INFO):
                created = asyncio.run(synchronizer.synchronize())

        assert len(created) == 20
        assert len(exchange_state.open_orders) == 20
        created_reference_ids = {str(order.order_id) for order in created}
        assert _SEC_COPY_GRID_SKIPPED_LATE_FILL_ORDER_ID in created_reference_ids
        assert synchronizer._find_open_order_by_bot_order_id(
            _SEC_COPY_GRID_SKIPPED_LATE_FILL_ORDER_ID
        ) is not None
        assert not any(
            "Skipping mirrored order creation (late reference fill on copier)" in record.message
            and _SEC_COPY_GRID_SKIPPED_LATE_FILL_ORDER_ID in record.message
            for record in caplog.records
        )
        assert any(
            "Order mirror completed:" in record.message
            and "20 created" in record.message
            for record in caplog.records
        )
        assert any(
            "Bypassing mirrored orphan grace: 20 reference order(s)" in record.message
            for record in caplog.records
        )
        assert not any(
            "Bypassing mirrored orphan grace after market rebalance" in record.message
            for record in caplog.records
        )
