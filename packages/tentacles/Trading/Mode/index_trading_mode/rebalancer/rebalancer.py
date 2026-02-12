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
import asyncio
import decimal
import typing

import octobot_commons.logging as logging
import octobot_commons.signals as commons_signals
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.modes as trading_modes
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_trading.errors as trading_errors
import octobot_trading.enums as trading_enums
import octobot_trading.api as trading_api

import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading


class RebalanceAborted(Exception):
    pass


class AbstractRebalancer:
    FILL_ORDER_TIMEOUT = 60
    PRICE_THRESHOLD_TO_USE_MARKET_ORDER = decimal.Decimal(0.01)  # 1%

    def __init__(self, trading_mode):
        self.trading_mode = trading_mode
        self.logger = logging.get_logger(self.__class__.__name__)

        self._already_logged_aborted_rebalance_error = False

    async def prepare_coin_rebalancing(self, coin: str):
        raise NotImplementedError("prepare_coin_rebalancing is not implemented")

    async def buy_coin(
        self, 
        symbol: str, 
        ideal_amount: decimal.Decimal, 
        ideal_price: typing.Optional[decimal.Decimal],
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> list:
        """
        Buys a coin or opens/increases a position for a symbol.
        """
        raise NotImplementedError("buy_coin is not implemented")

    async def get_removed_coins_to_sell_orders(self, details: dict, dependencies: typing.Optional[commons_signals.SignalDependencies]) -> list:
        removed_coins_to_sell_orders = []
        if removed_coins_to_sell := list(details[index_trading.RebalanceDetails.REMOVE.value]):
            removed_coins_to_sell_orders = await trading_modes.convert_assets_to_target_asset(
                self.trading_mode, removed_coins_to_sell,
                self.trading_mode.exchange_manager.exchange_personal_data.portfolio_manager.reference_market, {},
                dependencies=dependencies
            )
        return removed_coins_to_sell_orders
    
    async def get_coins_to_sell_orders(self, details: dict, dependencies: typing.Optional[commons_signals.SignalDependencies]) -> list:
        order_coins_to_sell = self.get_coins_to_sell(details)
        coins_to_sell_orders = await trading_modes.convert_assets_to_target_asset(
            self.trading_mode, order_coins_to_sell,
            self.trading_mode.exchange_manager.exchange_personal_data.portfolio_manager.reference_market, {},
            dependencies=dependencies
        )
        return coins_to_sell_orders

    async def validate_sold_removed_assets(
        self,
        details: dict,
        removed_orders: typing.Optional[list] = None
    ) -> None:
        if (
            details[index_trading.RebalanceDetails.REMOVE.value] and
            not (
                details[index_trading.RebalanceDetails.BUY_MORE.value]
                or details[index_trading.RebalanceDetails.ADD.value]
                or details[index_trading.RebalanceDetails.SWAP.value]
            )
        ):
            if removed_orders is None:
                removed_orders = []
            # if rebalance is triggered by removed assets, make sure that the asset can actually be sold
            # otherwise the whole rebalance is useless
            sold_coins = [
                symbol_util.parse_symbol(order.symbol).base
                if order.side is trading_enums.TradeOrderSide.SELL
                else symbol_util.parse_symbol(order.symbol).quote
                for order in removed_orders
            ]
            if not any(
                asset in sold_coins
                for asset in details[index_trading.RebalanceDetails.REMOVE.value]
            ):
                self.logger.info(
                    f"Cancelling rebalance: not enough {list(details[index_trading.RebalanceDetails.REMOVE.value])} funds to sell"
                )
                raise trading_errors.MissingMinimalExchangeTradeVolume(
                    f"not enough {list(details[index_trading.RebalanceDetails.REMOVE.value])} funds to sell"
                )

    async def sell_indexed_coins_for_reference_market(
        self, 
        details: dict, 
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> list:
        await self.pre_cancel_conflicting_orders(details, dependencies, trading_enums.TradeOrderSide.BUY)
        removed_coins_to_sell_orders = await self.get_removed_coins_to_sell_orders(details, dependencies)
        await self.validate_sold_removed_assets(details, removed_coins_to_sell_orders)
        coins_to_sell_orders = await self.get_coins_to_sell_orders(details, dependencies)
        orders = removed_coins_to_sell_orders + coins_to_sell_orders
        if orders:
            # ensure all orders are filled
            await self.wait_for_orders_to_fill(orders)
        return orders

    def get_coins_to_sell(self, details: dict) -> list:
        return list(details[index_trading.RebalanceDetails.SWAP.value]) or (
            self.trading_mode.indexed_coins
        )

    async def wait_for_orders_to_fill(self, orders: list) -> None:
        """
        Waits for the specified orders to be filled (positions to close/open or assets to be sold/bought).
        """
        if orders:
            await asyncio.gather(
                *[
                    trading_personal_data.wait_for_order_fill(
                        order, self.FILL_ORDER_TIMEOUT, True
                    ) for order in orders
                ],
                return_exceptions=True
            )

    def get_pending_open_quantity(self, symbol: str) -> decimal.Decimal:
        pending_quantity = decimal.Decimal(0)
        for order in trading_api.get_open_orders(self.trading_mode.exchange_manager, symbol=symbol):
            remaining_quantity = order.origin_quantity - order.filled_quantity
            if remaining_quantity <= decimal.Decimal(0):
                continue
            if order.side is trading_enums.TradeOrderSide.BUY:
                pending_quantity += remaining_quantity
            elif order.side is trading_enums.TradeOrderSide.SELL:
                pending_quantity -= remaining_quantity
        return pending_quantity

    async def cancel_symbol_open_orders(
        self,
        symbol: str,
        dependencies: typing.Optional[commons_signals.SignalDependencies],
        allowed_sides: typing.Optional[set[trading_enums.TradeOrderSide]] = None
    ) -> typing.Optional[commons_signals.SignalDependencies]:
        cancelled_dependencies = commons_signals.SignalDependencies()
        for order in trading_api.get_open_orders(self.trading_mode.exchange_manager, symbol=symbol):
            if isinstance(order, trading_personal_data.MarketOrder):
                continue
            if allowed_sides and order.side not in allowed_sides:
                continue
            try:
                is_cancelled, dependency = await self.trading_mode.cancel_order(order)
                if is_cancelled and dependency is not None:
                    cancelled_dependencies.extend(dependency)
            except trading_errors.UnexpectedExchangeSideOrderStateError as err:
                self.logger.warning(f"Skipped order cancel: {err}, order: {order}")
        if dependencies is not None:
            dependencies.extend(cancelled_dependencies)
        return cancelled_dependencies or None

    async def pre_cancel_conflicting_orders(
        self,
        details: dict,
        dependencies: typing.Optional[commons_signals.SignalDependencies],
        side: trading_enums.TradeOrderSide
    ) -> None:
        symbols_to_cleanup = self.get_pre_cancel_order_symbols(details, side)
        for symbol in symbols_to_cleanup:
            await self.cancel_symbol_open_orders(
                symbol,
                dependencies=dependencies,
                allowed_sides={side}
            )

    def get_pre_cancel_order_symbols(self, details: dict, side: trading_enums.TradeOrderSide) -> set[str]:
        symbols_to_cleanup: set[str] = set()
        keys = self.get_rebalance_details_keys_for_side(side)
        
        for key in keys:
            for coin_or_symbol in details.get(key, {}):
                symbols_to_cleanup.add(self.get_symbol_and_base_asset(coin_or_symbol)[0])
        return symbols_to_cleanup

    def get_rebalance_details_keys_for_side(self, side: trading_enums.TradeOrderSide) -> list[str]:
        if side == trading_enums.TradeOrderSide.BUY:
            return [index_trading.RebalanceDetails.REMOVE.value, index_trading.RebalanceDetails.SELL_SOME.value]
        if side == trading_enums.TradeOrderSide.SELL:
            return [index_trading.RebalanceDetails.ADD.value, index_trading.RebalanceDetails.BUY_MORE.value]
        raise ValueError(f"Unsupported side: {side}")

    def get_symbol_and_base_asset(self, coin_or_symbol: str) -> tuple[str, str]:
        if symbol_util.is_symbol(coin_or_symbol):
            return coin_or_symbol, symbol_util.parse_symbol(coin_or_symbol).base
        ref_market = self.trading_mode.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
        return symbol_util.merge_currencies(coin_or_symbol, ref_market), coin_or_symbol
