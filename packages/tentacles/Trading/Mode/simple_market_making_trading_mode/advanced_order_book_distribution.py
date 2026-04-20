# Drakkar-Software OctoBot-Tentacles
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
import enum
import typing

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import tentacles.Trading.Mode.market_making_trading_mode.order_book_distribution as order_book_distribution


class OrdersDistribution(enum.Enum):
    LINEAR = "linear"


class FundsDistribution(enum.Enum):
    VALLEY = "valley"
    FLAT = "flat"
    RANDOM = "random"


STABLE = "stable_towards_current_price"
MULTIPLIER = "multiplier"
DEFAULT_TOLERATED_BELLOW_DEPTH_RATIO = decimal.Decimal("0.80")
DEFAULT_TOLERATED_ABOVE_DEPTH_RATIO = decimal.Decimal("1.50")
ALLOWED_MIN_SPREAD_RATIO = decimal.Decimal("0.1")
ALLOWED_MAX_SPREAD_RATIO = decimal.Decimal("0.1")


FundsDistributionStrategyModeMultipliersDetails = {
    FundsDistribution.VALLEY: {
        MULTIPLIER: decimal.Decimal("2"),
        trading_enums.TradeOrderSide.BUY: order_book_distribution.DECREASING,
        trading_enums.TradeOrderSide.SELL: order_book_distribution.DECREASING
    },
    FundsDistribution.FLAT: {
        MULTIPLIER: decimal.Decimal("1"),
        trading_enums.TradeOrderSide.BUY: order_book_distribution.DECREASING,
        trading_enums.TradeOrderSide.SELL: order_book_distribution.DECREASING
    },
    FundsDistribution.RANDOM: {
        MULTIPLIER: decimal.Decimal("0.2"),
        trading_enums.TradeOrderSide.BUY: order_book_distribution.RANDOM,
        trading_enums.TradeOrderSide.SELL: order_book_distribution.RANDOM
    },
}


class AdvancedOrderBookDistribution(order_book_distribution.OrderBookDistribution):
    def __init__(
        self,
        bids_count: int,
        asks_count: int,
        min_spread: decimal.Decimal,
        max_spread: decimal.Decimal,
        target_cumulated_volume_percent: decimal.Decimal,
        daily_trading_volume_percent: decimal.Decimal,
        price_distribution: OrdersDistribution,
        funds_distribution: FundsDistribution,
        max_base_budget: typing.Optional[decimal.Decimal] = None,
        max_quote_budget: typing.Optional[decimal.Decimal] = None,
        min_base_budget: typing.Optional[decimal.Decimal] = None,
        min_quote_budget: typing.Optional[decimal.Decimal] = None,
        tolerated_bellow_depth_ratio: decimal.Decimal = DEFAULT_TOLERATED_BELLOW_DEPTH_RATIO,
        tolerated_above_depth_ratio: decimal.Decimal = DEFAULT_TOLERATED_ABOVE_DEPTH_RATIO,
    ):
        super().__init__(bids_count, asks_count, min_spread, max_spread)
        self.target_cumulated_volume_percent: decimal.Decimal = target_cumulated_volume_percent
        self.daily_trading_volume_percent: decimal.Decimal = daily_trading_volume_percent
        self.price_distribution: OrdersDistribution = price_distribution
        self.funds_distribution: FundsDistribution = funds_distribution
        self.max_base_budget: typing.Optional[decimal.Decimal] = max_base_budget
        self.max_quote_budget: typing.Optional[decimal.Decimal] = max_quote_budget
        self.min_base_budget: typing.Optional[decimal.Decimal] = min_base_budget
        self.min_quote_budget: typing.Optional[decimal.Decimal] = min_quote_budget
        self.tolerated_bellow_depth_ratio = tolerated_bellow_depth_ratio
        self.tolerated_above_depth_ratio = tolerated_above_depth_ratio

        self.bids: list[order_book_distribution.BookOrderData] = []
        self.asks: list[order_book_distribution.BookOrderData] = []

    def validate_config(self):
        if self.max_spread <= self.min_spread:
            raise ValueError(
                f"Maximum spread ({float(self.max_spread)}) must be larger than "
                f"minimum spread ({float(self.min_spread)})."
            )
        if self.min_spread / decimal.Decimal("2") > (
            self.target_cumulated_volume_percent / trading_constants.ONE_HUNDRED
        ):
            raise ValueError(
                f"Minimum spread should be smaller than 2x target cumulated volume percent. Minimum spread: "
                f"{float(self.min_spread)} cumulated volume percent: "
                f"{self.target_cumulated_volume_percent / trading_constants.ONE_HUNDRED}"
            )

    def _should_use_artificial_funds(
        self, ideal_total_volume: decimal.Decimal, total_volume: decimal.Decimal,
        side: trading_enums.TradeOrderSide,
        tolerated_bellow_depth_ratio=order_book_distribution.DEFAULT_TOLERATED_BELLOW_DEPTH_RATIO
    ) -> bool:
        min_config_budget = self.get_min_max_budget(side)[0]
        return (
            (min_config_budget and ideal_total_volume < min_config_budget)
            or super()._should_use_artificial_funds(
                ideal_total_volume, total_volume, side, tolerated_bellow_depth_ratio=self.tolerated_bellow_depth_ratio
            )
        )

    def _get_order_prices(
        self, start_price: decimal.Decimal, end_price: decimal.Decimal, orders_count: int
    ) -> list[decimal.Decimal]:
        if orders_count < 2:
            raise ValueError("Orders count must be greater than 2")
        if self.price_distribution is OrdersDistribution.LINEAR:
            # orders evenly distributed between lowest and highest price
            increment = (end_price - start_price) / (orders_count - 1)
            order_prices = [
                start_price + (increment * i)
                for i in range(orders_count)
            ]
        else:
            raise NotImplementedError(f"{self.price_distribution} not implemented")
        return order_prices

    def _get_order_volumes(
        self, side: trading_enums.TradeOrderSide, total_volume: decimal.Decimal, order_prices: list[decimal.Decimal],
        multiplier=decimal.Decimal(1), direction=order_book_distribution.DECREASING
    ) -> list[decimal.Decimal]:
        strategy = FundsDistributionStrategyModeMultipliersDetails[self.funds_distribution]
        return super()._get_order_volumes(
            side, total_volume, order_prices, multiplier=strategy[MULTIPLIER], direction=strategy[side]
        )

    def _are_total_order_volumes_compatible_with_config(
        self,
        closer_to_further_real_orders: list[order_book_distribution.BookOrderData],
        available_funds: decimal.Decimal,
        reference_price: decimal.Decimal,
        daily_volume: decimal.Decimal,
        side: trading_enums.TradeOrderSide,
        trigger_source: str,
        tolerated_bellow_depth_ratio = DEFAULT_TOLERATED_BELLOW_DEPTH_RATIO,
        tolerated_above_depth_ratio = DEFAULT_TOLERATED_ABOVE_DEPTH_RATIO,
    ) -> bool:
        return super()._are_total_order_volumes_compatible_with_config(
            closer_to_further_real_orders, available_funds, reference_price, daily_volume, side, trigger_source,
            self.tolerated_bellow_depth_ratio, self.tolerated_above_depth_ratio
        )

    def _get_total_volume_to_use(
        self, side: trading_enums.TradeOrderSide, reference_price: decimal.Decimal,
        reference_volume: decimal.Decimal, order_prices: list[decimal.Decimal],
        available_funds_base_or_quote: typing.Optional[decimal.Decimal],
        until_depth_threshold_only: bool,
    ) -> decimal.Decimal:
        # 1. get ideal volume
        ideal_total_volume = self._get_ideal_total_volume_to_use(
            side, reference_price, reference_volume, order_prices, until_depth_threshold_only
        )
        max_budget_base_or_quote = available_funds_base_or_quote
        min_config_budget, max_config_budget = self.get_min_max_budget(side)

        # 2. apply min if configured
        if min_config_budget is not None and ideal_total_volume < min_config_budget:
            ideal_total_volume = min_config_budget

        # 3. ensure max is respected
        if max_config_budget is not None:
            if max_budget_base_or_quote is None or max_config_budget < max_budget_base_or_quote:
                max_budget_base_or_quote = max_config_budget
        if max_budget_base_or_quote is not None and ideal_total_volume > max_budget_base_or_quote:
            return max_budget_base_or_quote
        return ideal_total_volume

    def get_min_max_budget(self, side: trading_enums.TradeOrderSide):
        return (
            self.min_quote_budget if side is trading_enums.TradeOrderSide.BUY else self.min_base_budget,
            self.max_quote_budget if side is trading_enums.TradeOrderSide.BUY else self.max_base_budget,
        )

    def _get_market_depth_order_amounts(
        self, orders: list[order_book_distribution.BookOrderData], reference_price: decimal.Decimal
    ) -> list[decimal.Decimal]:
        return [
            order.get_base_amount()
            for order in orders
            if abs(trading_constants.ONE_HUNDRED - (
                order.price * trading_constants.ONE_HUNDRED / reference_price
            )) <= self.target_cumulated_volume_percent
        ]

    def _get_ideal_total_volume_to_use(
        self, side: trading_enums.TradeOrderSide, reference_price: decimal.Decimal,
        reference_volume: decimal.Decimal, order_prices: list[decimal.Decimal],
        until_depth_threshold_only: bool,
        daily_trading_volume_percent=order_book_distribution.DAILY_TRADING_VOLUME_PERCENT
    ) -> decimal.Decimal:
        return super()._get_ideal_total_volume_to_use(
            side, reference_price, reference_volume, order_prices, until_depth_threshold_only,
            daily_trading_volume_percent=self.daily_trading_volume_percent
        )
