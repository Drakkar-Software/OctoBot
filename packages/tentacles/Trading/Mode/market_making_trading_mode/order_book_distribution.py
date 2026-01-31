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
import copy
import dataclasses
import decimal
import typing
import random

import octobot_commons.logging as commons_logging
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as trading_personal_data


DEFAULT_TOLERATED_BELLOW_DEPTH_RATIO = decimal.Decimal("0.80")
DEFAULT_TOLERATED_ABOVE_DEPTH_RATIO = decimal.Decimal("1.50")
ALLOWED_MIN_SPREAD_RATIO = decimal.Decimal("0.1")
ALLOWED_MAX_SPREAD_RATIO = decimal.Decimal("0.1")
TARGET_CUMULATED_VOLUME_PERCENT: decimal.Decimal = decimal.Decimal(3)
DAILY_TRADING_VOLUME_PERCENT: decimal.Decimal = decimal.Decimal(2)
MAX_HANDLED_BIDS_ORDERS = 5
MAX_HANDLED_ASKS_ORDERS = 5

INCREASING = "increasing_towards_current_price"
DECREASING = "decreasing_towards_current_price"
RANDOM = "random"

# allow up to 10 decimals to avoid floating point precision issues due to percent ratios
_MAX_PRECISION = decimal.Decimal("1.0000000000")

@dataclasses.dataclass
class InferredOrderData:
    ideal_price: decimal.Decimal
    ideal_amount_percent: decimal.Decimal
    current_price: typing.Optional[decimal.Decimal]
    current_origin_amount: typing.Optional[decimal.Decimal]
    final_amount: typing.Optional[decimal.Decimal]
    final_price: typing.Optional[decimal.Decimal]


@dataclasses.dataclass
class BookOrderData:
    price: decimal.Decimal
    amount: decimal.Decimal
    side: trading_enums.TradeOrderSide

    def get_base_amount(self) -> decimal.Decimal:
        return self.amount * self.price if self.side == trading_enums.TradeOrderSide.BUY else self.amount


class FullBookRebalanceRequired(Exception):
    pass


class MissingOrderException(Exception):
    pass


class MissingAllBids(MissingOrderException):
    pass


class MissingAllAsks(MissingOrderException):
    pass


class MissingAllOrders(MissingOrderException):
    pass


class OrderBookDistribution:
    def __init__(
        self,
        bids_count: int,
        asks_count: int,
        min_spread: decimal.Decimal,
        max_spread: decimal.Decimal,
    ):
        self.min_spread: decimal.Decimal = min_spread
        self.max_spread: decimal.Decimal = max_spread
        self.bids_count: int = bids_count
        self.asks_count: int = asks_count

        self.bids: list[BookOrderData] = []
        self.asks: list[BookOrderData] = []

    def get_ideal_total_volume(
        self, side: trading_enums.TradeOrderSide, reference_price: decimal.Decimal,
        daily_base_volume: decimal.Decimal, daily_quote_volume: decimal.Decimal,
    ) -> decimal.Decimal:
        orders_count, start_price, end_price, reference_volume, available_funds = self._get_sided_orders_details(
            side, reference_price, daily_base_volume, daily_quote_volume, None, None, []
        )

        # order prices are sorted from the inside out of the order book (closest to the price first)
        order_prices = self._get_order_prices(start_price, end_price, orders_count)

        return self._get_total_volume_to_use(
            side, reference_price, reference_volume, order_prices, available_funds, False
        )

    def compute_distribution(
        self,
        reference_price: decimal.Decimal,
        daily_base_volume: decimal.Decimal, daily_quote_volume: decimal.Decimal,
        symbol_market: dict,
        available_base: typing.Optional[decimal.Decimal] = None,
        available_quote: typing.Optional[decimal.Decimal] = None,
    ):
        self.bids = self._get_target_orders(
            trading_enums.TradeOrderSide.BUY, reference_price,
            daily_base_volume, daily_quote_volume, available_base, available_quote,
            symbol_market
        )
        self.asks = self._get_target_orders(
            trading_enums.TradeOrderSide.SELL, reference_price,
            daily_base_volume, daily_quote_volume, available_base, available_quote,
            symbol_market
        )
        return self

    def get_shape_distance_from(
        self,
        orders: list[BookOrderData],
        available_base: decimal.Decimal,
        available_quote: decimal.Decimal,
        reference_price: decimal.Decimal,
        daily_base_volume: decimal.Decimal,
        daily_quote_volume: decimal.Decimal,
        trigger_source: str,
    ) -> float:
        """
        Returns a float averaging the distance of each given order relatively to the ideal
        configured order volumes shape
        """
        bids_difference = self._get_sided_orders_distance_from_ideal(
            orders, available_quote, reference_price, daily_quote_volume,
            trading_enums.TradeOrderSide.BUY, trigger_source
        )
        asks_difference = self._get_sided_orders_distance_from_ideal(
            orders, available_base, reference_price, daily_base_volume,
            trading_enums.TradeOrderSide.SELL, trigger_source
        )
        return float(bids_difference + asks_difference) / 2

    def is_spread_according_to_config(self, orders: list[BookOrderData], open_orders: list[trading_personal_data.Order]):
        open_buy_orders = [o for o in open_orders if o.side == trading_enums.TradeOrderSide.BUY]
        open_sell_orders = [o for o in open_orders if o.side == trading_enums.TradeOrderSide.SELL]
        if not (open_buy_orders and open_sell_orders):
            # missing all buy or sell orders (or both)
            if not (open_buy_orders or open_sell_orders):
                raise MissingAllOrders()
            if not open_buy_orders:
                raise MissingAllBids()
            if not open_sell_orders:
                raise MissingAllAsks()
        if not (len(open_buy_orders) == self.bids_count and len(open_sell_orders) == self.asks_count):
            # missing a few orders, spread can't be checked, consider valid
            return True
        buy_orders = get_sorted_sided_orders([o for o in orders if o.side == trading_enums.TradeOrderSide.BUY], True)
        sell_orders = get_sorted_sided_orders([o for o in orders if o.side == trading_enums.TradeOrderSide.SELL], True)
        min_spread = (sell_orders[0].price - buy_orders[0].price)/(
            (sell_orders[0].price + buy_orders[0].price) / decimal.Decimal("2")
        )
        max_spread = (sell_orders[-1].price - buy_orders[-1].price)/(
            (sell_orders[-1].price + buy_orders[-1].price) / decimal.Decimal("2")
        )
        compliant_spread = (
            (
                self.min_spread * (trading_constants.ONE - ALLOWED_MIN_SPREAD_RATIO)
                < min_spread
                < self.min_spread * (trading_constants.ONE + ALLOWED_MIN_SPREAD_RATIO)
            )
            and (
                self.max_spread * (trading_constants.ONE - ALLOWED_MAX_SPREAD_RATIO)
                < max_spread
                < self.max_spread * (trading_constants.ONE + ALLOWED_MAX_SPREAD_RATIO)
            )
        )
        if not compliant_spread:
            self.get_logger().warning(
                f"Spread is beyond configuration: {min_spread=} {self.min_spread=} {max_spread=} {self.max_spread=}"
            )
        return compliant_spread

    def infer_full_order_data_after_swaps(
        self,
        existing_orders: list[BookOrderData],
        outdated_orders: list[trading_personal_data.Order],
        available_base: decimal.Decimal,
        available_quote: decimal.Decimal,
        reference_price: decimal.Decimal,
        daily_base_volume: decimal.Decimal,
        daily_quote_volume: decimal.Decimal,
    ):
        """
        return the target updated list of BookOrderData using existing_orders as the current state of the order book
        and the current configuration
        """
        buy_orders = [o for o in existing_orders if o.side == trading_enums.TradeOrderSide.BUY]
        sell_orders = [o for o in existing_orders if o.side == trading_enums.TradeOrderSide.SELL]
        updated_existing_orders = copy.copy(existing_orders)
        if len(buy_orders) < len(sell_orders):
            # missing buy orders: create missing buy order based on current sell orders
            adapted_buy_orders = self._infer_sided_order_data_after_swaps(
                updated_existing_orders, outdated_orders, available_quote, reference_price,
                daily_quote_volume, trading_enums.TradeOrderSide.BUY
            )
            updated_existing_orders = [o for o in existing_orders if o.side != trading_enums.TradeOrderSide.BUY]
            # compute sell orders based on adapted buy orders
            updated_existing_orders += adapted_buy_orders
            adapted_sell_orders = self._infer_sided_order_data_after_swaps(
                updated_existing_orders, outdated_orders, available_base, reference_price,
                daily_base_volume, trading_enums.TradeOrderSide.SELL
            )
        else:
            # missing sell orders (or both sides): create missing sell order based on current buy orders
            adapted_sell_orders = self._infer_sided_order_data_after_swaps(
                updated_existing_orders, outdated_orders, available_base, reference_price,
                daily_base_volume, trading_enums.TradeOrderSide.SELL
            )
            updated_existing_orders = [o for o in existing_orders if o.side != trading_enums.TradeOrderSide.SELL]
            # compute sell orders based on adapted buy orders
            updated_existing_orders += adapted_sell_orders
            adapted_buy_orders = self._infer_sided_order_data_after_swaps(
                updated_existing_orders, outdated_orders, available_quote, reference_price,
                daily_quote_volume, trading_enums.TradeOrderSide.BUY
            )
        return adapted_buy_orders + adapted_sell_orders

    def _get_sided_orders_distance_from_ideal(
        self,
        orders: list[BookOrderData],
        available_funds: decimal.Decimal,
        reference_price: decimal.Decimal,
        daily_volume: decimal.Decimal,
        side: trading_enums.TradeOrderSide,
        trigger_source: str,
    ):
        # shape distance is computed using the average % difference from the ideal shape of the book
        closer_to_further_real_orders = get_sorted_sided_orders(
            [o for o in orders if o.side == side], True
        )
        ideal_orders_count = self.bids_count if side == trading_enums.TradeOrderSide.BUY else self.asks_count
        if not closer_to_further_real_orders:
            if ideal_orders_count > 0:
                self.get_logger().info(
                    f"0 {side.name} open orders, required: {ideal_orders_count} refresh required "
                    f"[trigger source: {trigger_source}]"
                )
                return 1
            return 0
        if not self._are_total_order_volumes_compatible_with_config(
            closer_to_further_real_orders, available_funds, reference_price,daily_volume, side, trigger_source
        ):
            return 1
        min_amount, max_amount = (
            min(closer_to_further_real_orders[0].amount, closer_to_further_real_orders[-1].amount),
            max(closer_to_further_real_orders[0].amount, closer_to_further_real_orders[-1].amount)
        )
        ideal_prices = self._get_order_prices(decimal.Decimal(0), trading_constants.ONE_HUNDRED, ideal_orders_count)
        raw_ideal_amounts = self._get_order_volumes(side, trading_constants.ONE_HUNDRED, ideal_prices)
        min_ideal_amount, max_ideal_amount = min(raw_ideal_amounts), max(raw_ideal_amounts)
        if max_amount == trading_constants.ZERO or max_ideal_amount == trading_constants.ZERO:
            # impossible to compute distance
            self.get_logger().info(
                f"Incompatible total amounts on {side.name} side: {max_amount=}, {max_ideal_amount=}, refresh required "
                f"[trigger source: {trigger_source}]"
            )
            return 1
        # align amounts between 0 and 100 to be able to compare
        real_amounts = [
            decimal.Decimal(str((o.amount - min_amount) * trading_constants.ONE_HUNDRED / max_amount))
            for o in closer_to_further_real_orders
        ]
        ideal_amounts = [
            (a - min_ideal_amount) * trading_constants.ONE_HUNDRED / max_ideal_amount
            for a in raw_ideal_amounts
        ]
        distances = []
        for i, ideal_amount in enumerate(ideal_amounts):
            try:
                distances.append(abs(ideal_amount - real_amounts[i]) / trading_constants.ONE_HUNDRED)
            except IndexError:
                # missing price
                distances.append(trading_constants.ZERO)
        if len(real_amounts) > len(ideal_amounts):
            # real orders that should not be open
            distances += [decimal.Decimal(1)] * (len(real_amounts) - len(ideal_amounts))
        return (sum(distances) / len(distances)) if distances else 0

    def _should_use_artificial_funds(
        self, ideal_total_volume: decimal.Decimal, total_volume: decimal.Decimal,
        side: trading_enums.TradeOrderSide, tolerated_bellow_depth_ratio=DEFAULT_TOLERATED_BELLOW_DEPTH_RATIO
    ) -> bool:
        return ideal_total_volume * tolerated_bellow_depth_ratio > total_volume

    def _are_total_order_volumes_compatible_with_config(
        self,
        closer_to_further_real_orders: list[BookOrderData],
        available_funds: decimal.Decimal,
        reference_price: decimal.Decimal,
        daily_volume: decimal.Decimal,
        side: trading_enums.TradeOrderSide,
        trigger_source: str,
        tolerated_bellow_depth_ratio = DEFAULT_TOLERATED_BELLOW_DEPTH_RATIO,
        tolerated_above_depth_ratio = DEFAULT_TOLERATED_ABOVE_DEPTH_RATIO,
    ) -> bool:
        order_prices = [o.price for o in closer_to_further_real_orders]
        ideal_total_volume = self._get_ideal_total_volume_to_use(
            side, reference_price, daily_volume, order_prices, False
        )
        total_volume = self._get_total_volume_to_use(
            side, reference_price, daily_volume, order_prices, available_funds, False
        )
        if self._should_use_artificial_funds(ideal_total_volume, total_volume, side):
            # case 1. not enough funds and compliant config to use ideal volume: check all orders total amount
            #   against available funds (taken into account in total_volume)
            # case 2. enough funds and non-compliant config to use ideal volume: check all orders total amount
            #   against target config (taken into account in total_volume)
            # case 3. both cases 1. and 2. => same outcome
            theoretical_used_funds = total_volume
            current_used_funds = sum(
                order.get_base_amount()
                for order in closer_to_further_real_orders
            )
            required_source = "available funds or config"
        else:
            # case 4: enough funds and compliant config to use ideal volume: check orders market_depth_size
            #   against total volume before market depth threshold
            theoretical_used_funds = self._get_total_volume_to_use(
                side, reference_price, daily_volume, order_prices, available_funds, True
            )
            current_used_funds = sum(
                amount
                for amount in self._get_market_depth_order_amounts(closer_to_further_real_orders, reference_price)
            )
            required_source = "ideal funds according to config and trading volume"
        if current_used_funds < theoretical_used_funds * tolerated_bellow_depth_ratio:
            self.get_logger().warning(
                f"{side.name} order book depth is not reached, refresh required. "
                f"Volume in orders: {current_used_funds}, required: {theoretical_used_funds} (from {required_source}) "
                f"[trigger source: {trigger_source}]"
            )
            return False
        if current_used_funds > theoretical_used_funds * tolerated_above_depth_ratio:
            self.get_logger().warning(
                f"{side.name} order book depth is exceeded by more than "
                f"{tolerated_above_depth_ratio * trading_constants.ONE_HUNDRED - trading_constants.ONE_HUNDRED}%, "
                f"refresh required. Volume in orders: {current_used_funds}, required: {theoretical_used_funds} "
                f"(from {required_source}) "
                f"[trigger source: {trigger_source}]"
            )
            return False
        return True

    def _get_target_orders(
        self, side: trading_enums.TradeOrderSide, reference_price: decimal.Decimal,
        daily_base_volume: decimal.Decimal, daily_quote_volume: decimal.Decimal,
        available_base: typing.Optional[decimal.Decimal], available_quote: typing.Optional[decimal.Decimal],
        symbol_market: dict
    ) -> list[BookOrderData]:
        orders_count, start_price, end_price, reference_volume, available_funds = self._get_sided_orders_details(
            side, reference_price, daily_base_volume, daily_quote_volume, available_base, available_quote, []
        )

        # order prices are sorted from the inside out of the order book (closest to the price first)
        order_prices = self._get_order_prices(start_price, end_price, orders_count)

        total_volume = self._get_total_volume_to_use(
            side, reference_price, reference_volume, order_prices, available_funds, False
        )
        # order volumes are sorted from the inside out of the order book (closest to the price first)
        order_volumes = self._get_order_volumes(side, total_volume, order_prices)
        if side is trading_enums.TradeOrderSide.BUY:
            # convert quote volume into base
            order_volumes = [
                (volume / order_price) if order_price else volume
                for volume, order_price in zip(order_volumes, order_prices)
            ]

        if len(order_prices) != len(order_volumes):
            raise ValueError(f"order_prices and order_volumes should have the same size")

        return [
            BookOrderData(
                trading_personal_data.decimal_adapt_price(symbol_market, price),
                trading_personal_data.decimal_adapt_quantity(symbol_market, volume),
                side,
            )
            for price, volume in zip(order_prices, order_volumes)
        ]

    def can_create_at_least_one_order(self, sides: list[trading_enums.TradeOrderSide], symbol_market: dict) -> bool:
        for side in sides:
            orders = self.bids if side == trading_enums.TradeOrderSide.BUY else self.asks
            if not self._is_at_least_one_order_valid(orders, symbol_market):
                return False
        return True

    def _is_at_least_one_order_valid(self, orders: list[BookOrderData], symbol_market: dict) -> bool:
        for order in orders:
            if trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                order.amount,
                order.price,
                symbol_market
            ):
                return True
        return False

    def validate_config(self):
        if self.asks_count > MAX_HANDLED_ASKS_ORDERS:
            raise ValueError(
                f"A maximum of {MAX_HANDLED_ASKS_ORDERS} asks is supported"
            )
        if self.bids_count > MAX_HANDLED_BIDS_ORDERS:
            raise ValueError(
                f"A maximum of {MAX_HANDLED_BIDS_ORDERS} bids is supported"
            )
        if self.max_spread <= self.min_spread:
            raise ValueError(
                f"Maximum spread ({float(self.max_spread)}) must be larger than "
                f"minimum spread ({float(self.min_spread)})."
            )
        allowed_min_spread = decimal.Decimal("2") * TARGET_CUMULATED_VOLUME_PERCENT / trading_constants.ONE_HUNDRED
        if self.min_spread > allowed_min_spread:
            raise ValueError(
                f"Minimum spread should be smaller than {allowed_min_spread}. "
                f"Minimum spread: {float(self.min_spread)}"
            )

    def _get_sided_orders_details(
        self, side: trading_enums.TradeOrderSide, reference_price: decimal.Decimal,
        daily_base_volume: decimal.Decimal, daily_quote_volume: decimal.Decimal,
        available_base: typing.Optional[decimal.Decimal], available_quote: typing.Optional[decimal.Decimal],
        other_side_orders: list[BookOrderData]
    ):
        self.validate_config()
        # reverse when other side is BUY, therefore current side is sell
        first_other_side_price = get_sorted_sided_orders(
            other_side_orders, True
        )[0] if other_side_orders else None
        order_book_price_range = reference_price * (self.max_spread - self.min_spread) / decimal.Decimal("2")
        flat_min_spread = reference_price * self.min_spread
        if side is trading_enums.TradeOrderSide.BUY:
            orders_count = self.bids_count
            if first_other_side_price is None or first_other_side_price.price - flat_min_spread > reference_price:
                start_price = reference_price - (flat_min_spread / 2)
            else:
                start_price = first_other_side_price.price - flat_min_spread
            end_price = start_price - order_book_price_range
            reference_volume = daily_quote_volume
            available_funds = available_quote
        else:
            orders_count = self.asks_count
            if first_other_side_price is None or first_other_side_price.price + flat_min_spread < reference_price:
                start_price = reference_price + (flat_min_spread / 2)
            else:
                start_price = first_other_side_price.price + flat_min_spread
            end_price = start_price + order_book_price_range
            reference_volume = daily_base_volume
            available_funds = available_base
        return orders_count, start_price, end_price, reference_volume, available_funds

    def _get_order_prices(
        self, start_price: decimal.Decimal, end_price: decimal.Decimal, orders_count: int
    ) -> list[decimal.Decimal]:
        if orders_count < 2:
            raise ValueError("Orders count must be greater than 2")
        increment = (end_price - start_price) / (orders_count - 1)
        return [
            start_price + (increment * i)
            for i in range(orders_count)
        ]

    def _infer_sided_order_data_after_swaps(
        self,
        existing_orders: list[BookOrderData],
        outdated_orders: list[trading_personal_data.Order],
        available_funds: decimal.Decimal,
        reference_price: decimal.Decimal,
        reference_volume: decimal.Decimal,
        side: trading_enums.TradeOrderSide
    ) -> list[BookOrderData]:
        if not existing_orders and not outdated_orders:
            # nothing to adapt: return ideal orders
            return self.bids if side == trading_enums.TradeOrderSide.BUY else self.asks
        closer_to_further_orders = get_sorted_sided_orders(
            [o for o in existing_orders if o.side == side], True
        )
        other_side_orders = [o for o in existing_orders if o.side != side]
        orders_count, ideal_start_price, ideal_end_price, _, _ = self._get_sided_orders_details(
            side, reference_price,
            trading_constants.ZERO, trading_constants.ZERO,
            trading_constants.ZERO, trading_constants.ZERO,
            other_side_orders,
        )
        ideal_prices = self._get_order_prices(ideal_start_price, ideal_end_price, orders_count)
        ideal_amount_percents = self._get_order_volumes(side, trading_constants.ONE_HUNDRED, ideal_prices)
        adapted_orders_data = []
        existing_order_index = 0
        moving_window_price_ratio = decimal.Decimal("1.5")
        for i in range(0, len(ideal_prices)):
            ideal_price = ideal_prices[i]
            inferred_order_data = InferredOrderData(
                ideal_price, ideal_amount_percents[i], None, None, None, ideal_price
            )
            previous_ideal_price = ideal_prices[i - 1] if i > 0 else reference_price
            next_ideal_price = ideal_prices[i + 1] if i < len(ideal_prices) - 1 else None
            window_min = ideal_price - (
                abs(ideal_price - previous_ideal_price) / (
                    moving_window_price_ratio if i > 0 else decimal.Decimal(1)
                )
            )
            window_max = ideal_price + (
                (abs(next_ideal_price - ideal_price) / moving_window_price_ratio)
                if next_ideal_price is not None
                # fallback to previous price increment
                else abs(ideal_price - previous_ideal_price)
            )
            # for each ideal price, check if an equivalent exists in current prices
            candidate_existing_order_index = existing_order_index
            found_order = False
            while not found_order and len(closer_to_further_orders) > candidate_existing_order_index:
                current_order = closer_to_further_orders[candidate_existing_order_index]
                if window_min <= current_order.price <= window_max:
                    # price and amount are found: keep them
                    inferred_order_data.current_price = current_order.price
                    inferred_order_data.final_price = current_order.price
                    inferred_order_data.current_origin_amount = current_order.amount
                    inferred_order_data.final_amount = current_order.amount
                    found_order = True
                candidate_existing_order_index += 1
                if found_order:
                    # skip existing order from checked orders
                    existing_order_index = candidate_existing_order_index
                else:
                    # price is missing: it will have to be added
                    pass
            adapted_orders_data.append(inferred_order_data)

        self._adapt_inferred_order_amounts(
            adapted_orders_data, existing_orders, outdated_orders,
            available_funds, reference_price, reference_volume, side
        )

        return [
            BookOrderData(order.final_price, order.final_amount, side)
            for order in adapted_orders_data
        ]

    def _adapt_inferred_order_amounts(
        self,
        adapted_orders_data: list[InferredOrderData],
        existing_orders: list[BookOrderData],
        outdated_orders: list[trading_personal_data.Order],
        available_funds: decimal.Decimal,
        reference_price: decimal.Decimal,
        reference_volume: decimal.Decimal,
        side: trading_enums.TradeOrderSide
    ):
        if not any(d.final_amount is None for d in adapted_orders_data):
            # nothing to adapt
            return
        # order.filled_quantity is not handled in simulator
        available_funds_after_outdated_orders_in_quote_or_base = available_funds + sum(
            (order.origin_quantity - (
                trading_constants.ZERO if order.trader.simulate else order.filled_quantity
            )) * order.origin_price
            if side == trading_enums.TradeOrderSide.BUY else (order.origin_quantity - (
                trading_constants.ZERO if order.trader.simulate else order.filled_quantity
            ))
            for order in outdated_orders
            if order.side == side
        )
        # index missing final amounts
        reused_order_prices = [
            order.final_price
            for order in adapted_orders_data
            if order.current_origin_amount is not None
        ]
        cancelled_orders = [
            order
            for order in existing_orders
            if order.side == side and order.price not in reused_order_prices
        ]
        available_funds_after_cancelled_orders_in_quote_or_base = sum([
            (order.price * order.amount) if order.side == trading_enums.TradeOrderSide.BUY else order.amount
            for order in cancelled_orders
        ])
        total_available_amount_in_quote_or_base = (
            available_funds_after_outdated_orders_in_quote_or_base
            + available_funds_after_cancelled_orders_in_quote_or_base
        )
        base_total_available_amount = (
            total_available_amount_in_quote_or_base / reference_price
            if side == trading_enums.TradeOrderSide.BUY else total_available_amount_in_quote_or_base
        )

        # infer missing order amounts using found order and ideal percents
        if base_inferred_amounts := [
            o.current_origin_amount * trading_constants.ONE_HUNDRED / o.ideal_amount_percent
            for o in adapted_orders_data
            if o.current_origin_amount is not None
        ]:
            # use existing orders when possible
            base_inferred_amount_total_used_amount = sum(base_inferred_amounts) / len(base_inferred_amounts)
        else:
            # otherwise use config
            order_prices = [
                order.final_price
                for order in adapted_orders_data
            ]
            inferred_amount_total_used_amount_in_quote_or_base = self._get_total_volume_to_use(
                side, reference_price, reference_volume, order_prices, total_available_amount_in_quote_or_base,
                False
            )
            base_inferred_amount_total_used_amount = (
                inferred_amount_total_used_amount_in_quote_or_base / reference_price
                if side == trading_enums.TradeOrderSide.BUY else inferred_amount_total_used_amount_in_quote_or_base
            )

        # get total amount in current orders
        amount_in_orders = sum(
            o.current_origin_amount
            for o in adapted_orders_data
            if o.current_origin_amount is not None
        )
        # compute missing amount
        base_missing_amount = base_inferred_amount_total_used_amount - amount_in_orders
        if base_missing_amount < trading_constants.ZERO:
            # Means that required amount is lower than current open amount even though orders are missing. This
            # usually means that trading volume decreased and therefore less quantity is now required.
            # In this case, a full order book refresh is required
            raise FullBookRebalanceRequired(
                f"Too much funds in order book: missing amount in orders is < 0: {base_missing_amount}: "
                f"{base_inferred_amount_total_used_amount=} "
                f"{amount_in_orders=} {adapted_orders_data=}"
            )
        # if enough funds: use new %, otherwise adapt max to be available amount "splitable" between orders to create
        base_usable_total_amount = base_missing_amount
        if base_total_available_amount < base_missing_amount:
            # default to available funds if base_missing_amount is not available
            base_usable_total_amount = base_total_available_amount
        splittable_base_missing_amount = base_usable_total_amount / sum(
            inferred_data.ideal_amount_percent / trading_constants.ONE_HUNDRED
            for inferred_data in adapted_orders_data
            if inferred_data.current_origin_amount is None
        )

        for inferred_data in adapted_orders_data:
            if inferred_data.current_origin_amount is None:
                inferred_data.final_amount = (
                    inferred_data.ideal_amount_percent / trading_constants.ONE_HUNDRED * splittable_base_missing_amount
                )

    def _get_order_volumes(
        self, side: trading_enums.TradeOrderSide, total_volume: decimal.Decimal, order_prices: list[decimal.Decimal],
        multiplier=decimal.Decimal(1), direction: typing.Union[DECREASING, INCREASING, RANDOM] = DECREASING
    ) -> list[decimal.Decimal]:
        orders_count = len(order_prices)
        if orders_count < 2:
            raise ValueError("Orders count must be greater than 2")
        decimal_orders_count = decimal.Decimal(str(orders_count))
        if direction in (INCREASING, DECREASING):
            average_order_size = total_volume / decimal_orders_count
            max_size_delta = average_order_size * (multiplier - 1)
            increment = max_size_delta / decimal_orders_count
            # base_vol + base_vol + increment + base_vol + 2 x increment + .... = total_volume
            # order_count: 1 => 0 = 0 increment
            # order_count: 2 => 0 + 1 = 1 increments
            # order_count: 3 => 0 + 1 + 2 = 3 increments
            # order_count: 4 => 0 + 1 + 2 + 3 = 6 increments
            # order_count: 5 => 0 + 1 + 2 + 3 + 4 = 10 increments
            total_increments = sum(i for i in range(orders_count))
            base_vol = (total_volume - (total_increments * increment)) / decimal_orders_count

            iterator = range(orders_count) if DECREASING else range(orders_count - 1, 0, -1)
            # DECREASING : order are smaller when closer to the reference price
            # INCREASING : order are larger when closer to the reference price
            order_volumes = [
                base_vol + (increment * decimal.Decimal(str(i)))
                for i in iterator
            ]
        elif direction == RANDOM:
            min_multiplier = float(trading_constants.ONE - (multiplier))
            max_multiplier = float(trading_constants.ONE + (multiplier))
            multipliers = [random.uniform(min_multiplier, max_multiplier) for _ in range(orders_count)]
            total_multiplier = sum(multipliers)
            order_volumes = [
                total_volume * decimal.Decimal(str(multiplier / total_multiplier))
                for multiplier in multipliers
            ]
        else:
            raise NotImplementedError(f"{direction} not implemented")
        return order_volumes

    def _get_total_volume_to_use(
        self, side: trading_enums.TradeOrderSide, reference_price: decimal.Decimal,
        reference_volume: decimal.Decimal, order_prices: list[decimal.Decimal],
        available_funds_base_or_quote: typing.Optional[decimal.Decimal],
        until_depth_threshold_only: bool,
    ) -> decimal.Decimal:
        ideal_total_volume = self._get_ideal_total_volume_to_use(
            side, reference_price, reference_volume, order_prices, until_depth_threshold_only
        )
        if available_funds_base_or_quote is not None and ideal_total_volume > available_funds_base_or_quote:
            return available_funds_base_or_quote
        return ideal_total_volume

    def _get_market_depth_order_amounts(
        self, orders: list[BookOrderData], reference_price: decimal.Decimal
    ) -> list[decimal.Decimal]:
        return [
            order.get_base_amount()
            for order in orders
            if abs(trading_constants.ONE_HUNDRED - (
                order.price * trading_constants.ONE_HUNDRED / reference_price
            )) <= TARGET_CUMULATED_VOLUME_PERCENT
        ]

    def _get_ideal_total_volume_to_use(
        self, side: trading_enums.TradeOrderSide, reference_price: decimal.Decimal,
        reference_volume: decimal.Decimal, order_prices: list[decimal.Decimal],
        until_depth_threshold_only: bool,
        daily_trading_volume_percent=DAILY_TRADING_VOLUME_PERCENT
    ) -> decimal.Decimal:
        # ideal volume contains daily_trading_volume_percent of daily_volume
        # within the first target_cumulated_volume_percent of the order book
        target_before_threshold_volume = (
            reference_volume * daily_trading_volume_percent / trading_constants.ONE_HUNDRED
        )
        if until_depth_threshold_only:
            self.get_logger().info(f"{target_before_threshold_volume=} {daily_trading_volume_percent=}")
            return target_before_threshold_volume
        counted_orders = len(self._get_market_depth_order_amounts([
            BookOrderData(price, trading_constants.ZERO, side)
            for price in order_prices
        ], reference_price))
        # goal: the first (closes to reference price) counted_orders orders have a volume of target_volume

        # use a percent-based volume profile to figure out the total required volume
        reference_order_volumes = self._get_order_volumes(side, trading_constants.ONE_HUNDRED, order_prices)
        # volume_before_threshold = % of traded volume that is contained before threshold
        percent_volume_before_threshold = sum(
            percent_volume
            for percent_volume in reference_order_volumes[:counted_orders]
        )
        if percent_volume_before_threshold == trading_constants.ZERO:
            if not reference_order_volumes:
                raise ValueError(f"Error: reference_order_volumes can't be empty. {order_prices=}")
            percent_volume_before_threshold = reference_order_volumes[0]
        # ideal_total_volume = volume_before_threshold + rest of the volume
        # ideal_total_volume = ideal_total_volume * percent_volume_before_threshold / 100 + ideal_total_volume * (1 - percent_volume_before_threshold / 100)
        # Where: ideal_total_volume * percent_volume_before_threshold / 100 = target_before_threshold_volume
        # Therefore: ideal_total_volume = target_before_threshold_volume + ideal_total_volume * (1 - percent_volume_before_threshold / 100)
        # ideal_total_volume - ideal_total_volume * (100 - ideal_total_volume) = target_before_threshold_volume
        # 1 - (1 - percent_volume_before_threshold / 100) = target_before_threshold_volume / ideal_total_volume
        # ideal_total_volume = target_before_threshold_volume / (1 - (1 - percent_volume_before_threshold * 100))
        ideal_total_volume = (
            target_before_threshold_volume / percent_volume_before_threshold * trading_constants.ONE_HUNDRED
        )
        # keep up to 10 decimals to avoid floating point precision issues due to percent ratios
        return _quantize_decimal(ideal_total_volume)

    @classmethod
    def get_logger(cls):
        return commons_logging.get_logger(cls.__name__)


def _quantize_decimal(value: decimal.Decimal) -> decimal.Decimal:
    return value.quantize(
        _MAX_PRECISION, 
        rounding=decimal.ROUND_HALF_UP
    )


def get_sorted_sided_orders(orders: list[BookOrderData], closer_to_further: bool) -> list[BookOrderData]:
    if orders:
        side = orders[0].side
        return sorted(
            orders,
            key=lambda o: o.price,
            reverse=side == (
                trading_enums.TradeOrderSide.BUY if closer_to_further else trading_enums.TradeOrderSide.SELL
            ),
        )
    return orders
