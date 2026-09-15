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
import time

import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models

import octobot_copy.copiers.formatter as copy_formatter


_REFERENCE_UPDATED_AT = 1710000000.0
_REFERENCE_UPDATED_AT_LABEL = (
    f"{timestamp_util.convert_timestamp_to_datetime(_REFERENCE_UPDATED_AT, local_timezone=False)} UTC"
)


def _copied_asset(
    *,
    name: str = "BTC",
    ratio: float = 1.0,
) -> protocol_models.CopiedAsset:
    return protocol_models.CopiedAsset(
        name=name,
        total=1.0,
        available=1.0,
        ratio=ratio,
    )


def _reference_limit_order(
    *,
    symbol: str = "BTC/USDT",
    price: float = 95000.0,
    side: protocol_models.Side = protocol_models.Side.BUY,
    order_type: protocol_models.OrderType = protocol_models.OrderType.LIMIT,
) -> protocol_models.Order:
    return protocol_models.Order(
        id="reference-order-id",
        symbol=symbol,
        price=price,
        quantity=0.001,
        filled=0.0,
        exchange_id="ex",
        side=side,
        type=order_type,
        trigger_above=False,
        reduce_only=False,
        is_active=True,
        status=protocol_models.OrderStatus.OPEN,
        created_at=timestamp_util.utc_datetime_from_timestamp(time.time()),
    )


def _copied_account(
    *,
    copied_assets: list[protocol_models.CopiedAsset] | None = None,
    orders: list[protocol_models.Order] | None = None,
) -> protocol_models.CopiedAccount:
    return protocol_models.CopiedAccount(
        version="1.0.0",
        updated_at=_REFERENCE_UPDATED_AT,
        copied_assets=copied_assets or [],
        orders=orders,
    )


class TestFormatReferenceAccountUpdatedAt:
    def test_formats_unix_timestamp_as_utc_human_readable_string(self):
        assert copy_formatter._format_reference_account_updated_at(_REFERENCE_UPDATED_AT) == (
            _REFERENCE_UPDATED_AT_LABEL
        )


class TestFormatCopiedAssetEntry:
    def test_formats_name_and_ratio_as_percent(self):
        copied_asset = _copied_asset(name="BTC", ratio=0.5038280454117718)

        entry = copy_formatter._format_copied_asset_entry(copied_asset)

        assert entry == "BTC:50.4%"


class TestFormatReferenceOrderEntry:
    def test_formats_side_symbol_and_price_without_id(self):
        order = _reference_limit_order(symbol="BTC/USDT", price=95000.0)

        entry = copy_formatter._format_reference_order_entry(order)

        assert entry == "buy BTC/USDT@95000.0"
        assert "reference-order-id" not in entry


class TestFormatOrderTypeCountLabel:
    def test_empty_when_no_orders(self):
        assert copy_formatter._format_order_type_count_label([]) == "0"

    def test_mixed_buy_and_sell_limit_orders(self):
        orders = [
            _reference_limit_order(side=protocol_models.Side.BUY),
            _reference_limit_order(side=protocol_models.Side.SELL),
        ]

        label = copy_formatter._format_order_type_count_label(orders)

        assert label == "1 buy_limit,1 sell_limit"

    def test_multiple_orders_of_same_type(self):
        orders = [
            _reference_limit_order(side=protocol_models.Side.BUY),
            _reference_limit_order(side=protocol_models.Side.BUY),
        ]

        label = copy_formatter._format_order_type_count_label(orders)

        assert label == "2 buy_limit"


class TestFormatReferenceAccountSummary:
    def test_assets_only(self):
        reference_account = _copied_account(
            copied_assets=[_copied_asset(name="BTC", ratio=1.0)],
        )

        summary = copy_formatter.format_reference_account_summary(reference_account)

        assert summary == (
            f"v1.0.0@{_REFERENCE_UPDATED_AT_LABEL} assets[1]:BTC:100.0% orders[0]"
        )

    def test_assets_and_orders(self):
        reference_account = _copied_account(
            copied_assets=[
                _copied_asset(name="USDT", ratio=0.49617195458822816),
                _copied_asset(name="BTC", ratio=0.5038280454117718),
            ],
            orders=[
                _reference_limit_order(symbol="BTC/USDT", price=95000.0),
                _reference_limit_order(
                    symbol="ETH/USDT",
                    price=3000.0,
                    side=protocol_models.Side.SELL,
                ),
            ],
        )

        summary = copy_formatter.format_reference_account_summary(reference_account)

        assert summary == (
            f"v1.0.0@{_REFERENCE_UPDATED_AT_LABEL} "
            "assets[2]:USDT:49.6%,BTC:50.4% "
            "orders[1 buy_limit,1 sell_limit]:buy BTC/USDT@95000.0,sell ETH/USDT@3000.0"
        )

    def test_orders_none_shows_zero_count(self):
        reference_account = _copied_account(
            copied_assets=[_copied_asset()],
            orders=None,
        )

        summary = copy_formatter.format_reference_account_summary(reference_account)

        assert summary.endswith("orders[0]")

    def test_truncates_when_more_than_summary_limit(self):
        copied_assets = [
            _copied_asset(name=f"ASSET{asset_index}", ratio=0.1)
            for asset_index in range(copy_formatter.REFERENCE_ACCOUNT_SUMMARY_LIMIT + 1)
        ]
        orders = [
            _reference_limit_order(symbol=f"SYM{order_index}/USDT", price=float(order_index))
            for order_index in range(copy_formatter.REFERENCE_ACCOUNT_SUMMARY_LIMIT + 1)
        ]
        reference_account = _copied_account(copied_assets=copied_assets, orders=orders)

        summary = copy_formatter.format_reference_account_summary(reference_account)

        assert "assets[11]:" in summary
        assert "…+1 more" in summary
        assert "orders[11 buy_limit]:" in summary
