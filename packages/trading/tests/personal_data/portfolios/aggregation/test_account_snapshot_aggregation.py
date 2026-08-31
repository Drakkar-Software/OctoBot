#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import decimal

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data.portfolios.aggregation.account_snapshot_aggregation as account_snapshot_aggregation_module


class TestSumNumericHoldings:
    def test_sums_decimal_holdings(self):
        result = account_snapshot_aggregation_module.sum_numeric_holdings(
            decimal.Decimal("1.5"),
            decimal.Decimal("2.5"),
        )
        assert result == decimal.Decimal("4.0")


class TestMergePortfolioContents:
    def test_merges_holdings_into_target(self):
        target = {
            "BTC": {"total": 1.0, "available": 1.0},
        }
        source = {
            "BTC": {"total": 0.5},
            "USDT": {"total": 100.0},
        }
        account_snapshot_aggregation_module.merge_portfolio_contents(target, source)
        assert target["BTC"]["total"] == 1.5
        assert target["USDT"]["total"] == 100.0


class TestMergeEnrichedOrdersDeduped:
    def test_dedupes_orders_by_exchange_id(self):
        existing_orders = [
            {
                trading_constants.STORAGE_ORIGIN_VALUE: {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order-1",
                }
            },
        ]
        new_orders = [
            {
                trading_constants.STORAGE_ORIGIN_VALUE: {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order-1",
                },
                "updated": True,
            },
            {
                trading_constants.STORAGE_ORIGIN_VALUE: {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order-2",
                }
            },
        ]
        merged_orders = account_snapshot_aggregation_module.merge_enriched_orders_deduped(
            existing_orders,
            new_orders,
        )
        assert len(merged_orders) == 2
        order_ids = {
            order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value
            ]
            for order in merged_orders
        }
        assert order_ids == {"order-1", "order-2"}
        order_one = next(
            order
            for order in merged_orders
            if order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value
            ] == "order-1"
        )
        assert order_one.get("updated") is True

    def test_keeps_orders_without_exchange_id(self):
        existing_orders = [
            {trading_constants.STORAGE_ORIGIN_VALUE: {}},
        ]
        new_orders = [
            {trading_constants.STORAGE_ORIGIN_VALUE: {}, "from_new": True},
        ]
        merged_orders = account_snapshot_aggregation_module.merge_enriched_orders_deduped(
            existing_orders,
            new_orders,
        )
        assert len(merged_orders) == 2
