#  Drakkar-Software OctoBot
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
import typing

import octobot_commons.signals as commons_signals
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors

import octobot_copy.enums as rebalancer_enums
import octobot_copy.rebalancing.rebalancer.rebalancer as base_rebalancer


class FuturesRebalancer(base_rebalancer.AbstractRebalancer):
    async def prepare_coin_rebalancing(self, coin: str):
        symbol, _ = self._get_symbol_and_base_asset(coin)
        await self._exchange_interface.market.ensure_contract_loaded(symbol)

    async def _buy_coin(
        self,
        symbol: str,
        ideal_amount: decimal.Decimal,
        ideal_price: typing.Optional[decimal.Decimal],
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> list:
        """
        Opens or increases a position for a symbol.
        For futures, this creates orders to open/increase positions instead of buying assets.
        """
        position = self._exchange_interface.positions.get_symbol_position(symbol, trading_enums.PositionSide.BOTH)
        _, _, _, current_price, symbol_market = await self._exchange_interface.orders.get_pre_order_data(
            symbol=symbol,
            timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT
        )

        order_target_price = ideal_price if ideal_price is not None else current_price
        current_position_size = position.size if not position.is_idle() else trading_constants.ZERO
        effective_current_position_size = current_position_size + self._get_pending_open_quantity(symbol)
        size_difference = ideal_amount - effective_current_position_size

        if size_difference <= trading_constants.ZERO:
            self._get_logger().warning(
                f"Skipping {symbol} futures position increase: size_difference={size_difference} "
                f"(ideal_amount={ideal_amount}, effective_current_position_size={effective_current_position_size})"
            )
            return []

        side = trading_enums.TradeOrderSide.BUY  # Always open long positions for targeted coins
        max_order_size, _ = self._exchange_interface.orders.get_futures_max_order_size(
            symbol, side, current_price, False, current_position_size, ideal_amount
        )

        order_quantity = min(size_difference, max_order_size)
        if order_quantity <= trading_constants.ZERO:
            self._get_logger().warning(
                f"Skipping {symbol} futures order creation: order_quantity={order_quantity} after "
                f"capping size_difference={size_difference} with max_order_size={max_order_size}"
            )
            return []

        is_price_close_to_market = order_target_price >= current_price * (decimal.Decimal(1) - self.PRICE_THRESHOLD_TO_USE_MARKET_ORDER)
        ideal_order_type = trading_enums.TraderOrderType.BUY_MARKET if is_price_close_to_market else trading_enums.TraderOrderType.BUY_LIMIT
        order_type = (
            ideal_order_type
            if self._exchange_interface.market.is_market_open_for_order_type(symbol, ideal_order_type)
            else trading_enums.TraderOrderType.BUY_LIMIT
        )

        order_target_price, order_quantity = (
            self._exchange_interface.orders.adapt_order_quantity_and_target_price_for_order_creation(
                order_type,
                symbol,
                order_quantity,
                order_target_price,
                adapt_price_for_limit_orders=True,
            )
        )
        created_orders, orders_should_have_been_created = await self._exchange_interface.orders.create_orders(
            order_type,
            symbol,
            current_price,
            order_quantity,
            order_target_price,
            symbol_market,
            dependencies=dependencies,
            reduce_only=False,
            skip_none_create_results=True,
            raise_all_creation_error=self._rebalance_actions_planner.client.raise_all_order_errors,
        )

        if created_orders:
            return created_orders
        if self._rebalance_actions_planner.client.allow_skip_asset:
            self._get_logger().warning(f"Skipping {symbol} order creation...")
            return []
        if orders_should_have_been_created:
            raise trading_errors.OrderCreationError()
        raise trading_errors.MissingMinimalExchangeTradeVolume()

    def compute_desired_futures_position_size(
        self,
        current_price: decimal.Decimal,
        target_ratio: decimal.Decimal,
    ) -> decimal.Decimal:
        if current_price <= trading_constants.ZERO:
            return trading_constants.ZERO
        total_holdings_value = self._exchange_interface.portfolio.get_traded_assets_holdings_value(
            self._exchange_interface.portfolio.reference_market
        )
        try:
            return max(
                trading_constants.ZERO,
                decimal.Decimal(str(target_ratio)) * total_holdings_value / current_price
            )
        except decimal.DecimalException:
            return trading_constants.ZERO

    async def _get_coins_to_sell_orders(self, details: dict, dependencies: typing.Optional[commons_signals.SignalDependencies]) -> list:
        orders = []
        symbol_target_ratio: dict[str, typing.Optional[decimal.Decimal]] = {}

        for coin_or_symbol in self._get_coins_to_sell(details):
            symbol_target_ratio[self._get_symbol_and_base_asset(coin_or_symbol)[0]] = None

        for coin_or_symbol in details.get(rebalancer_enums.RebalanceDetails.REMOVE.value, {}):
            symbol_target_ratio[self._get_symbol_and_base_asset(coin_or_symbol)[0]] = None

        for coin_or_symbol, target_ratio in details.get(rebalancer_enums.RebalanceDetails.SELL_SOME.value, {}).items():
            symbol_target_ratio[self._get_symbol_and_base_asset(coin_or_symbol)[0]] = target_ratio

        for symbol, target_ratio in symbol_target_ratio.items():
            _, _, _, current_price, symbol_market = await self._exchange_interface.orders.get_pre_order_data(
                symbol=symbol,
                timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
            )
            desired_futures_position_size = (
                self.compute_desired_futures_position_size(current_price, target_ratio)
                if target_ratio is not None
                else None
            )
            orders += await self._exchange_interface.positions.close_symbol_position(
                symbol,
                dependencies,
                current_price,
                symbol_market,
                desired_futures_position_size=desired_futures_position_size,
            )

        return orders
