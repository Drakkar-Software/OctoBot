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
import importlib.util
import pathlib
import time

import mock
import pytest

import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models
import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_copy.exchange as copy_exchange
import octobot_copy.orders_mirroring.orders_synchronizer as orders_synchronizer_module


def _load_copy_tests_python_helpers():
    init_path = pathlib.Path(__file__).resolve().parent.parent / "__init__.py"
    spec = importlib.util.spec_from_file_location("copy_tests_python_helpers", init_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


copy_tests_python_helpers = _load_copy_tests_python_helpers()

pytestmark = pytest.mark.asyncio

_BTC_USDT = "BTC/USDT"
_BTC_PRICE = decimal.Decimal("60000")
_REPLACE_ORDER_ID = "dabfe054-a650-4a09-a296-8d22ceb6f664"
_CREATE_ORDER_ID = "7cf7e7ad-b3e4-4f6a-a2f5-1ecff2cc176f"
# Copier open buy before sync (oversized vs reference target); locks ~19.8 USDT at _BTC_PRICE.
_EXISTING_OPEN_QUANTITY = decimal.Decimal("0.00033")
# Simulates exchange-refresh snapshot: most USDT is locked in open orders, not in available.
_STALE_USDT_AVAILABLE = decimal.Decimal("5")
_COUPLER_USDT_TOTAL = decimal.Decimal("100")
# Scale ratio for buys: copier 100 / reference 1000 → 0.1 (ref 0.002 → copier 0.0002, etc.).
_REFERENCE_USDT_TOTAL = decimal.Decimal("1000")


def _replicable_btc_buy_limit_order(
    *,
    order_id: str,
    quantity: decimal.Decimal,
    price: decimal.Decimal = _BTC_PRICE,
) -> protocol_models.Order:
    return protocol_models.Order(
        id=order_id,
        symbol=_BTC_USDT,
        price=float(price),
        quantity=float(quantity),
        filled=0.0,
        exchange_id="reference-exchange-id",
        side=protocol_models.Side.BUY,
        type=protocol_models.OrderType.LIMIT,
        trigger_above=False,
        reduce_only=False,
        is_active=True,
        status=protocol_models.OrderStatus.OPEN,
        created_at=timestamp_util.utc_datetime_from_timestamp(time.time()),
    )


def _reference_account_with_two_buys() -> protocol_models.CopiedAccount:
    return protocol_models.CopiedAccount(
        version=copy_constants.COPIED_ACCOUNT_VERSION,
        updated_at=time.time(),
        copied_assets=[
            protocol_models.CopiedAsset(name="BTC", total=1.0, available=1.0, ratio=0.5),
            protocol_models.CopiedAsset(
                name="USDT",
                total=float(_REFERENCE_USDT_TOTAL),
                available=float(_REFERENCE_USDT_TOTAL),
                ratio=0.5,
            ),
        ],
        orders=[
            _replicable_btc_buy_limit_order(
                order_id=_REPLACE_ORDER_ID,
                quantity=decimal.Decimal("0.002"),
            ),
            _replicable_btc_buy_limit_order(
                order_id=_CREATE_ORDER_ID,
                quantity=decimal.Decimal("0.0015"),
            ),
        ],
    )


def _open_order_by_id(exchange_manager, order_id: str):
    for order in exchange_manager.exchange_personal_data.orders_manager.get_open_orders():
        if str(order.order_id) == order_id:
            return order
    return None


class TestSynchronize:
    @pytest.mark.parametrize("backtesting_config", ["USDT"], indirect=True)
    async def test_creates_buy_after_downsize_replace_frees_stale_quote(self, live_trading_trader):
        # Live trading keeps portfolio.available frozen until an exchange refresh; mirror sync
        # downsizes existing buys (freeing quote on the exchange) then may create new buys in the
        # same pass. Without mirror_sync_available_updates, the second create still reads stale
        # available and caps quantity too low. This test reproduces that sequence end-to-end.
        _config, exchange_manager, _trader = live_trading_trader
        copy_tests_python_helpers.ensure_traded_symbol_pairs(exchange_manager, (_BTC_USDT,))
        portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

        # Seed copier portfolio and mark price so buy sizing and market checks succeed.
        trading_api.force_set_mark_price(exchange_manager, _BTC_USDT, _BTC_PRICE)
        portfolio_manager.portfolio.update_portfolio_from_balance(
            {
                "BTC": {"available": decimal.Decimal("0.01"), "total": decimal.Decimal("0.01")},
                "USDT": {
                    "available": _COUPLER_USDT_TOTAL,
                    "total": _COUPLER_USDT_TOTAL,
                },
            },
            True,
        )
        portfolio_manager.handle_balance_updated()
        portfolio_manager.portfolio_value_holder.value_converter.missing_currency_data_in_exchange.discard("USDT")
        portfolio_manager.handle_mark_price_update(_BTC_USDT, _BTC_PRICE)

        # One mirrored buy already open on the copier (will be replaced first during synchronize).
        exchange_interface = copy_exchange.ExchangeInterface(exchange_manager)
        await exchange_interface.orders.create_order(
            trading_enums.TraderOrderType.BUY_LIMIT,
            _BTC_USDT,
            _BTC_PRICE,
            _EXISTING_OPEN_QUANTITY,
            _BTC_PRICE,
            tag=copy_constants.MIRRORED_ORDER_TAG,
            order_id=_REPLACE_ORDER_ID,
            wait_for_creation=True,
        )

        # Mimic post-refresh live state: total unchanged, available stuck at the pre-resync value.
        portfolio_manager.portfolio.get_currency_portfolio("USDT").available = _STALE_USDT_AVAILABLE

        # Reference grid: replace_id first (downsize existing buy), then create_id (new buy ~9 USDT).
        reference_account = _reference_account_with_two_buys()
        synchronizer = orders_synchronizer_module.OrdersSynchronizer(
            reference_account,
            exchange_interface,
            copy_entities.AccountCopySettings(),
        )

        # End-of-sync exchange refresh is mocked; assertions are on open orders, not balances.
        refresh_portfolio_mock = mock.AsyncMock(return_value=True)
        with mock.patch.object(
            exchange_interface.portfolio,
            "refresh_portfolio",
            refresh_portfolio_mock,
        ):
            await synchronizer.synchronize()

        refresh_portfolio_mock.assert_awaited_once()

        replace_order = _open_order_by_id(exchange_manager, _REPLACE_ORDER_ID)
        create_order = _open_order_by_id(exchange_manager, _CREATE_ORDER_ID)

        # Replace frees ~7.8 USDT vs old lock; create needs ~9 USDT — only succeeds if available tracked during sync.
        assert replace_order is not None
        assert replace_order.origin_quantity == decimal.Decimal("0.0002")
        assert create_order is not None
        assert create_order.origin_quantity == decimal.Decimal("0.00015")
