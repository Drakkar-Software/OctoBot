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

import octobot_copy.constants as copy_constants
import octobot_copy.rebalancing.rebalancer.rebalancer as base_rebalancer


class SpotRebalancer(base_rebalancer.AbstractRebalancer):

    async def prepare_coin_rebalancing(self, coin: str):
        # Nothing to do in SPOT
        pass

    async def _buy_coin(
        self,
        symbol: str,
        ideal_amount: decimal.Decimal,
        ideal_price: typing.Optional[decimal.Decimal],
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> list:
        current_symbol_holding, current_market_holding, market_quantity, current_price, symbol_market = \
            await self._exchange_interface.orders.get_pre_order_data(
                symbol=symbol,
                timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT
            )
        order_target_price = ideal_price if ideal_price is not None else current_price
        # ideally use the expected reference_market_available_holdings ratio, fallback to available
        # holdings if necessary
        target_quantity = min(ideal_amount, current_market_holding / order_target_price)
        if self._rebalance_actions_planner.client.can_include_assets_in_open_orders_in_holdings_ratio:
            effective_current_symbol_holding = current_symbol_holding + self._get_pending_open_quantity(symbol)
        else:
            effective_current_symbol_holding = current_symbol_holding # should be >0 ??
        ideal_quantity = target_quantity - effective_current_symbol_holding
        if ideal_quantity <= trading_constants.ZERO:
            return []
        if ideal_quantity < ideal_amount * decimal.Decimal("0.9"):
            self._get_logger().warning(
                f"{symbol} order quantity has to be reduced from {ideal_amount} to "
                f"{ideal_quantity} to adapt to available funds."
            )
        is_price_close_to_market = order_target_price >= current_price * (decimal.Decimal(1) - self.PRICE_THRESHOLD_TO_USE_MARKET_ORDER)
        ideal_order_type = trading_enums.TraderOrderType.BUY_MARKET if is_price_close_to_market else trading_enums.TraderOrderType.BUY_LIMIT
        order_type = (
            ideal_order_type
            if self._exchange_interface.market.is_market_open_for_order_type(symbol, ideal_order_type)
            else trading_enums.TraderOrderType.BUY_LIMIT
        )

        order_target_price, ideal_quantity = (
            self._exchange_interface.orders.adapt_order_quantity_and_target_price_for_order_creation(
                order_type,
                symbol,
                ideal_quantity,
                order_target_price,
                adapt_price_for_limit_orders=True,
            )
        )
        created_orders, orders_should_have_been_created = await self._exchange_interface.orders.create_orders(
            order_type,
            symbol,
            current_price,
            ideal_quantity,
            order_target_price,
            symbol_market,
            dependencies=dependencies,
            tag=copy_constants.REBALANCER_ORDER_TAG,
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
