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

import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.signals as commons_signals
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.modes as trading_modes
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.personal_data.orders.order_util as order_util

import tentacles.Trading.Mode.index_trading_mode.rebalancer as rebalancer


class FuturesRebalancer(rebalancer.AbstractRebalancer):
    async def prepare_coin_rebalancing(self, coin: str):
        await self.ensure_contract_loaded(coin)

    async def ensure_contract_loaded(self, coin: str):
        ref_market = self.trading_mode.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
        symbol = coin
        if not symbol_util.is_symbol(symbol):
            symbol = symbol_util.merge_currencies(coin, ref_market)
        try:
            await self.trading_mode.exchange_manager.exchange.get_pair_contract_async(symbol)
        except trading_errors.ContractExistsError:
            self.logger.info(f"Contract for {symbol} has been loaded.")

    async def buy_coin(
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
        positions_manager = self.trading_mode.exchange_manager.exchange_personal_data.positions_manager
        position = positions_manager.get_symbol_position(symbol, trading_enums.PositionSide.BOTH)
        _, _, _, current_price, symbol_market = await trading_personal_data.get_pre_order_data(
            self.trading_mode.exchange_manager, 
            symbol=symbol, 
            timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT
        )
        
        order_target_price = ideal_price if ideal_price is not None else current_price
        current_position_size = position.size if not position.is_idle() else trading_constants.ZERO
        effective_current_position_size = current_position_size + self.get_pending_open_quantity(symbol)
        size_difference = ideal_amount - effective_current_position_size
        
        if size_difference <= trading_constants.ZERO:
            return []
        
        side = trading_enums.TradeOrderSide.BUY  # Always open long positions for index
        max_order_size, increasing_position = order_util.get_futures_max_order_size(
            self.trading_mode.exchange_manager, symbol, side, current_price, False,
            current_position_size, ideal_amount
        )
        
        order_quantity = min(size_difference, max_order_size)
        if order_quantity <= trading_constants.ZERO:
            return []
        
        quantity = trading_personal_data.decimal_adapt_order_quantity_because_fees(
            self.trading_mode.exchange_manager, symbol, trading_enums.TraderOrderType.BUY_MARKET, order_quantity,
            order_target_price, trading_enums.TradeOrderSide.BUY
        )
        
        created_orders = []
        orders_should_have_been_created = False
        is_price_close_to_market = order_target_price >= current_price * (decimal.Decimal(1) - self.PRICE_THRESHOLD_TO_USE_MARKET_ORDER)
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
                reduce_only=False,  # Opening/increasing position
            )
            created_order = await self.trading_mode.create_order(current_order, dependencies=dependencies)
            if created_order is not None:
                created_orders.append(created_order)
        
        if created_orders:
            return created_orders
        if self.trading_mode.allow_skip_asset:
            self.logger.warning(f"Skipping {symbol} order creation...")
            return []
        if orders_should_have_been_created:
            raise trading_errors.OrderCreationError()
        raise trading_errors.MissingMinimalExchangeTradeVolume()
