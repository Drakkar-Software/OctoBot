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
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.modes.modes_util as modes_util
import octobot_trading.personal_data as trading_personal_data

import octobot_copy.constants as copy_constants
import octobot_copy.enums as rebalancer_enums
import octobot_copy.rebalancing.rebalancer.rebalancer as base_rebalancer


class SpotRebalancer(base_rebalancer.AbstractRebalancer):

    async def prepare_coin_rebalancing(self, coin: str):
        # Nothing to do in SPOT
        pass

    async def try_efficient_spot_rebalance(
        self,
        details: dict[str, typing.Any],
        dependencies: typing.Optional[commons_signals.SignalDependencies] = None,
    ) -> typing.Optional[list]:
        if not self._is_two_asset_spot_delta_eligible(details):
            return None
        ref_market = self._exchange_interface.portfolio.reference_market
        base_currency = self._get_single_non_reference_targeted_coin()
        if base_currency is None:
            return None
        symbol = symbol_util.merge_currencies(base_currency, ref_market)
        price = await self._exchange_interface.market.get_up_to_date_price(symbol)
        price = self._target_coins_prices.get(symbol, price)
        if not price or price <= trading_constants.ZERO:
            return None
        portfolio_value_ref = self._get_traded_assets_holdings_value(ref_market)
        reference_market_ratio = self._rebalance_actions_planner.client.reference_market_ratio
        if reference_market_ratio > trading_constants.ZERO:
            value_to_distribute = portfolio_value_ref * reference_market_ratio
        else:
            value_to_distribute = portfolio_value_ref
        target_ratio = self._rebalance_actions_planner.get_target_ratio(base_currency)
        target_base_quantity = target_ratio * value_to_distribute / price
        if self._rebalance_actions_planner.client.can_include_assets_in_open_orders_in_holdings_ratio:
            current_base_quantity = (
                self._exchange_interface.portfolio.get_currency_portfolio_available(base_currency)
                + self._get_pending_open_quantity(symbol)
            )
        else:
            current_base_quantity = self._exchange_interface.portfolio.get_currency_portfolio_available(
                base_currency
            )
        delta_base = current_base_quantity - target_base_quantity
        exchange_manager = self._exchange_interface.orders._exchange_manager
        if delta_base > trading_constants.ZERO:
            await self._pre_cancel_conflicting_orders(
                details, dependencies, trading_enums.TradeOrderSide.BUY
            )
            adapted_chunks, _symbol_market = (
                self._exchange_interface.orders.check_and_adapt_order_details_if_necessary(
                    symbol,
                    delta_base,
                    price,
                )
            )
            if not adapted_chunks:
                # dust amounts: delta_base is too small to be traded
                return None
            sell_orders = await modes_util.convert_asset_to_target_asset(
                base_currency,
                ref_market,
                {},
                asset_amount=delta_base,
                dependencies=dependencies,
                raise_all_order_errors=self._rebalance_actions_planner.client.raise_all_order_errors,
                exchange_manager=exchange_manager,
            )
            if not sell_orders:
                return None
            await self._exchange_interface.orders.wait_for_orders_to_fill(sell_orders)
            return sell_orders
        if delta_base < trading_constants.ZERO:
            await self._pre_cancel_conflicting_orders(
                details, dependencies, trading_enums.TradeOrderSide.SELL
            )
            ideal_price = self._target_coins_prices.get(symbol, price)
            try:
                buy_orders = await self._buy_coin(
                    symbol,
                    target_base_quantity,
                    ideal_price,
                    dependencies,
                )
            except trading_errors.MissingMinimalExchangeTradeVolume:
                # e.g. free quote is mostly locked in open (mirrored) orders: delta buy is not
                # executable at min size; fall back to legacy sell-all-then-buy.
                return None
            if not buy_orders:
                # buy order is too small to be traded
                return None
            await self._exchange_interface.orders.wait_for_orders_to_fill(buy_orders)
            return buy_orders
        return None

    def _is_two_asset_spot_delta_eligible(self, details: dict[str, typing.Any]) -> bool:
        if details[rebalancer_enums.RebalanceDetails.FORCED_REBALANCE.value]:
            return False
        if details[rebalancer_enums.RebalanceDetails.REMOVE.value]:
            return False
        if details[rebalancer_enums.RebalanceDetails.ADD.value]:
            return False
        if details[rebalancer_enums.RebalanceDetails.SWAP.value]:
            return False
        ref_market = self._exchange_interface.portfolio.reference_market
        targeted = self._rebalance_actions_planner.targeted_coins
        if len(targeted) != 2 or ref_market not in targeted:
            return False
        non_reference = [coin for coin in targeted if coin != ref_market]
        return len(non_reference) == 1

    def _get_single_non_reference_targeted_coin(self) -> typing.Optional[str]:
        ref_market = self._exchange_interface.portfolio.reference_market
        for coin in self._rebalance_actions_planner.targeted_coins:
            if coin != ref_market:
                return coin
        return None

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
