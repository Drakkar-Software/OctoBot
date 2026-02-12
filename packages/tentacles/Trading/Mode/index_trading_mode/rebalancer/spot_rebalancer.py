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
import octobot_trading.modes as trading_modes
import octobot_trading.personal_data as trading_personal_data

import tentacles.Trading.Mode.index_trading_mode.rebalancer as rebalancer


class SpotRebalancer(rebalancer.AbstractRebalancer):
    async def prepare_coin_rebalancing(self, coin: str):
        # Nothing to do in SPOT
        pass

    async def buy_coin(
        self, 
        symbol: str, 
        ideal_amount: decimal.Decimal,
        ideal_price: typing.Optional[decimal.Decimal],
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> list:
        current_symbol_holding, current_market_holding, market_quantity, current_price, symbol_market = \
            await trading_personal_data.get_pre_order_data(
                self.trading_mode.exchange_manager, 
                symbol=symbol, 
                timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT
            )
        order_target_price = ideal_price if ideal_price is not None else current_price
        # ideally use the expected reference_market_available_holdings ratio, fallback to available
        # holdings if necessary
        target_quantity = min(ideal_amount, current_market_holding / order_target_price)
        effective_current_symbol_holding = current_symbol_holding + self.get_pending_open_quantity(symbol)
        ideal_quantity = target_quantity - effective_current_symbol_holding
        if ideal_quantity <= trading_constants.ZERO:
            return []
        quantity = trading_personal_data.decimal_adapt_order_quantity_because_fees(
            self.trading_mode.exchange_manager, symbol, trading_enums.TraderOrderType.BUY_MARKET, ideal_quantity,
            order_target_price, trading_enums.TradeOrderSide.BUY
        )
        created_orders = []
        is_price_close_to_market = order_target_price >= current_price * (decimal.Decimal(1) - self.PRICE_THRESHOLD_TO_USE_MARKET_ORDER)
        orders_should_have_been_created = False
        ideal_order_type = trading_enums.TraderOrderType.BUY_MARKET if is_price_close_to_market else trading_enums.TraderOrderType.BUY_LIMIT
        order_type = (
            ideal_order_type
            if self.trading_mode.exchange_manager.exchange.is_market_open_for_order_type(symbol, ideal_order_type)
            else trading_enums.TraderOrderType.BUY_LIMIT
        )

        if trading_personal_data.get_trade_order_type(order_type) is not trading_enums.TradeOrderType.MARKET:
            # can't use market orders: use limit orders with price a bit above the current price to instant fill it.
            order_target_price, quantity = \
                trading_modes.get_instantly_filled_limit_order_adapted_price_and_quantity(
                    order_target_price, quantity, order_type
                )

        for order_quantity, order_price in trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
            quantity,
            order_target_price,
            symbol_market
        ):
            orders_should_have_been_created = True
            current_order = trading_personal_data.create_order_instance(
                trader=self.trading_mode.exchange_manager.trader,
                order_type=order_type,
                symbol=symbol,
                current_price=current_price,
                quantity=order_quantity,
                price=order_price,
            )
            created_order = await self.trading_mode.create_order(current_order, dependencies=dependencies)
            created_orders.append(created_order)
        if created_orders:
            return created_orders
        if self.trading_mode.allow_skip_asset:
            self.logger.warning(f"Skipping {symbol} order creation...")
            return []
        if orders_should_have_been_created:
            raise trading_errors.OrderCreationError()
        raise trading_errors.MissingMinimalExchangeTradeVolume()
