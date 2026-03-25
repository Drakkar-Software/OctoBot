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

import octobot_commons.logging as logging
import octobot_commons.signals as commons_signals
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors
import octobot_trading.enums as trading_enums
import octobot_copy.enums as rebalancer_enums
import octobot_copy.errors as copy_errors
import octobot_copy.exchange.exchange_interface as copy_exchange
import octobot_copy.rebalancing.planner.rebalance_actions_planner as rebalance_actions_planner_import


SIMPLE_ADD_MIN_TOLERANCE_RATIO = decimal.Decimal("0.8")  # 20% tolerance
IDEAL_AMOUNT = "ideal_amount"
IDEAL_PRICE = "ideal_price"


class AbstractRebalancer:
    PRICE_THRESHOLD_TO_USE_MARKET_ORDER = decimal.Decimal(0.01)  # 1%

    def __init__(
        self,
        exchange_interface: copy_exchange.ExchangeInterface,
        rebalance_actions_planner: rebalance_actions_planner_import.RebalanceActionsPlanner,
        target_coins_prices: dict,
    ):
        self._exchange_interface: copy_exchange.ExchangeInterface = exchange_interface
        self._rebalance_actions_planner: rebalance_actions_planner_import.RebalanceActionsPlanner = rebalance_actions_planner
        self._target_coins_prices: dict[str, decimal.Decimal] = target_coins_prices
        self._already_logged_aborted_rebalance_error: bool = False

    async def prepare_coin_rebalancing(self, coin: str):
        raise NotImplementedError("prepare_coin_rebalancing is not implemented")

    async def ensure_enough_funds_to_buy_after_selling(self) -> None:
        """
        Raises MissingMinimalExchangeTradeVolume if there are not enough funds
        to buy the targeted coins.
        """
        ref_market = self._exchange_interface.private_data.reference_market
        reference_market_to_split = self._get_traded_assets_holdings_value(ref_market)
        # will raise if funds are missing
        await self._get_symbols_and_amounts(
            self._target_coins_prices,
            reference_market_to_split,
        )

    async def sell_targeted_coins_for_reference_market(
        self,
        details: dict[str, typing.Any],
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> list:
        """
        Sells targeted or swapped coins for the reference market.
        """
        await self._pre_cancel_conflicting_orders(details, dependencies, trading_enums.TradeOrderSide.BUY)
        removed_coins_to_sell_orders = await self._get_removed_coins_to_sell_orders(details, dependencies)
        await self._validate_sold_removed_assets(details, removed_coins_to_sell_orders)
        coins_to_sell_orders = await self._get_coins_to_sell_orders(details, dependencies)
        orders = removed_coins_to_sell_orders + coins_to_sell_orders
        if orders:
            # ensure all orders are filled
            await self._exchange_interface.private_data.wait_for_orders_to_fill(orders)
        return orders

    def can_simply_buy_coins_without_selling(self, details: dict[str, typing.Any]) -> bool:
        """
        Returns True when it is possible to just buy the targeted coins
        without selling any other coins.
        """
        simple_buy_coins = self._get_simple_buy_coins(details)
        if not simple_buy_coins:
            return False
        # check if there is enough free funds to buy those coins
        ref_market = self._exchange_interface.private_data.reference_market
        reference_market_to_split = self._get_traded_assets_holdings_value(ref_market)
        free_reference_market_holding = self._get_free_reference_market_holding(ref_market)
        cumulated_ratio = sum(
            self._rebalance_actions_planner.get_target_ratio(coin)
            for coin in simple_buy_coins
        )
        tolerated_min_amount = reference_market_to_split * cumulated_ratio * SIMPLE_ADD_MIN_TOLERANCE_RATIO
        # can reach target ratios without selling if this condition is met
        return tolerated_min_amount <= free_reference_market_holding

    async def split_reference_market_into_targeted_coins(
        self,
        details: dict[str, typing.Any],
        is_simple_buy_without_selling: bool,
        dependencies: typing.Optional[commons_signals.SignalDependencies],
    ) -> list:
        """
        Splits the reference market into the targeted coins.
        If is_simple_buy_without_selling is True and swaps are identified, only swap 
        targets will be bought in order to reduce the number of required transactions.
        Otherwise, all targeted coins will be bought.
        
        For each coin, if self._target_coins_prices is set and far enough from the current price,
        the coin will be bought using a limit order at the target price. 
        Otherwise, a market order will be used.
        """
        orders = []
        await self._pre_cancel_conflicting_orders(details, dependencies, trading_enums.TradeOrderSide.SELL)
        ref_market = self._exchange_interface.private_data.reference_market
        if details[rebalancer_enums.RebalanceDetails.SWAP.value] or is_simple_buy_without_selling:
            # has to infer total reference market holdings
            reference_market_to_split = self._get_traded_assets_holdings_value(ref_market)
            coins_to_buy = (
                self._get_simple_buy_coins(details) if is_simple_buy_without_selling
                else list(details[rebalancer_enums.RebalanceDetails.SWAP.value].values())
            )
        else:
            # can use actual reference market holdings: everything has been sold
            reference_market_to_split = self._get_free_reference_market_holding(ref_market)
            coins_to_buy = self._rebalance_actions_planner.targeted_coins

        reference_market_ratio = self._rebalance_actions_planner.client.reference_market_ratio
        # Distribute a percentage among targeted coins, keep the rest in reference market
        # If reference_market_ratio is 0, distribute everything (no reservation)
        if reference_market_ratio > trading_constants.ZERO:
            reference_market_to_distribute = reference_market_to_split * reference_market_ratio
            reference_market_reserved = reference_market_to_split - reference_market_to_distribute
        else:
            reference_market_to_distribute = reference_market_to_split
            reference_market_reserved = trading_constants.ZERO

        if reference_market_reserved > trading_constants.ZERO:
            self._get_logger().info(
                f"Distributing {reference_market_to_distribute} {ref_market} ({reference_market_ratio * trading_constants.ONE_HUNDRED}%) "
                f"among targeted coins, reserving {reference_market_reserved} {ref_market} for reference market"
            )

        amount_by_symbol = await self._get_symbols_and_amounts(
            self._target_coins_prices,
            reference_market_to_distribute,
            coins_to_buy=coins_to_buy,
        )
        for symbol, values in amount_by_symbol.items():
            orders.extend(
                await self._buy_coin(
                    symbol,
                    values.get(IDEAL_AMOUNT),
                    values.get(IDEAL_PRICE),
                    dependencies,
                )
            )
        if not orders and not self._rebalance_actions_planner.client.allow_skip_asset:
            raise trading_errors.MissingMinimalExchangeTradeVolume()
        return orders

    async def _buy_coin(
        self,
        symbol: str,
        ideal_amount: decimal.Decimal,
        ideal_price: typing.Optional[decimal.Decimal],
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> list:
        """
        Buys a coin or opens/increases a position for a symbol.
        If ideal_price is set and far enough from the current price, a limit order will be used.
        Otherwise, a market order will be used.
        """
        raise NotImplementedError("_buy_coin is not implemented")

    async def _get_removed_coins_to_sell_orders(self, details: dict[str, typing.Any], dependencies: typing.Optional[commons_signals.SignalDependencies]) -> list:
        removed_coins_to_sell_orders = []
        if removed_coins_to_sell := list(details[rebalancer_enums.RebalanceDetails.REMOVE.value]):
            removed_coins_to_sell_orders = await self._exchange_interface.private_data.convert_assets_to_target_asset(
                removed_coins_to_sell,
                self._exchange_interface.private_data.reference_market,
                {},
                dependencies=dependencies,
            )
        return removed_coins_to_sell_orders

    async def _get_coins_to_sell_orders(self, details: dict[str, typing.Any], dependencies: typing.Optional[commons_signals.SignalDependencies]) -> list:
        order_coins_to_sell = self._get_coins_to_sell(details)
        coins_to_sell_orders = await self._exchange_interface.private_data.convert_assets_to_target_asset(
            order_coins_to_sell,
            self._exchange_interface.private_data.reference_market,
            {},
            dependencies=dependencies,
        )
        return coins_to_sell_orders

    async def _validate_sold_removed_assets(
        self,
        details: dict[str, typing.Any],
        removed_orders: typing.Optional[list] = None
    ) -> None:
        if (
            details[rebalancer_enums.RebalanceDetails.REMOVE.value] and
            not (
                details[rebalancer_enums.RebalanceDetails.BUY_MORE.value]
                or details[rebalancer_enums.RebalanceDetails.ADD.value]
                or details[rebalancer_enums.RebalanceDetails.SWAP.value]
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
                for asset in details[rebalancer_enums.RebalanceDetails.REMOVE.value]
            ):
                self._get_logger().info(
                    f"Cancelling rebalance: not enough {list(details[rebalancer_enums.RebalanceDetails.REMOVE.value])} funds to sell"
                )
                raise trading_errors.MissingMinimalExchangeTradeVolume(
                    f"not enough {list(details[rebalancer_enums.RebalanceDetails.REMOVE.value])} funds to sell"
                )

    def _get_simple_buy_coins(self, details: dict[str, typing.Any]) -> list:
        # Returns the list of coins to simply buy.
        # Used to avoid a full rebalance when coins are seen as added to a basket
        # AND funds are available to buy it AND no asset should be sold
        added = details[rebalancer_enums.RebalanceDetails.ADD.value] or details[rebalancer_enums.RebalanceDetails.BUY_MORE.value]
        if added and not (
            details[rebalancer_enums.RebalanceDetails.SWAP.value]
            or details[rebalancer_enums.RebalanceDetails.SELL_SOME.value]
            or details[rebalancer_enums.RebalanceDetails.REMOVE.value]
            or details[rebalancer_enums.RebalanceDetails.FORCED_REBALANCE.value]
        ):
            added_coins = list(details[rebalancer_enums.RebalanceDetails.ADD.value]) + list(details[rebalancer_enums.RebalanceDetails.BUY_MORE.value])
            return [
                coin
                for coin in self._rebalance_actions_planner.targeted_coins  # iterate over targeted coins to keep order
                if coin in added_coins
            ] + [
                coin
                for coin in added_coins
                if coin not in self._rebalance_actions_planner.targeted_coins
            ]
        return []

    def _get_traded_assets_holdings_value(
        self,
        unit: str,
        coins_whitelist: typing.Optional[typing.Iterable] = None,
    ) -> decimal.Decimal:
        return self._exchange_interface.private_data.get_traded_assets_holdings_value(
            unit, coins_whitelist
        )

    def _get_free_reference_market_holding(self, reference_market: str) -> decimal.Decimal:
        return self._exchange_interface.private_data.get_free_reference_market_holding(reference_market)

    async def _get_symbols_and_amounts(
        self,
        coins_prices: dict[str, decimal.Decimal],
        reference_market_to_split: decimal.Decimal,
        *,
        coins_to_buy: typing.Optional[list] = None,
    ) -> dict:
        amount_by_symbol = {}
        ref_market = self._exchange_interface.private_data.reference_market
        min_order_size_margin = self._rebalance_actions_planner.client.min_order_size_margin
        coins = (
            list(coins_to_buy)
            if coins_to_buy is not None
            else list(self._rebalance_actions_planner.targeted_coins)
        )
        for coin in coins:
            if not symbol_util.is_symbol(coin):
                if coin == ref_market:
                    # nothing to do for reference market, keep as is
                    continue
                symbol = symbol_util.merge_currencies(coin, ref_market)
            else:
                symbol = coin

            up_to_date_price = await self._exchange_interface.public_data.get_up_to_date_price(symbol)
            price = coins_prices.get(symbol, up_to_date_price)
            ratio = self._rebalance_actions_planner.get_target_ratio(coin)
            if ratio == trading_constants.ZERO:
                # coin is not to handle
                continue
            try:
                ideal_amount = ratio * reference_market_to_split / price
            except decimal.DecimalException as err:
                raise copy_errors.RebalanceAborted(
                    f"Error computing {symbol} ideal amount ({ratio=}, {reference_market_to_split=}, {price=}): {err=}"
                ) from err
            # worse case (ex with 5 USDT min order size): exactly 5 USDT can be in portfolio, we therefore want to
            # trade at least 5 USDT to be able to buy more.
            # - we want ideal_amount - min_cost > min_cost
            # - in other words ideal_amount > min_cost * min_order_size_margin
            #   => ideal_amount / min_order_size_margin > min_cost
            effective_min_order_size_margin = min_order_size_margin
            if effective_min_order_size_margin < trading_constants.ONE:
                effective_min_order_size_margin = trading_constants.ONE
            adapted_quantity, symbol_market = (
                self._exchange_interface.private_data.check_and_adapt_order_details_if_necessary(
                    symbol,
                    ideal_amount / effective_min_order_size_margin,
                    price,
                )
            )
            if not adapted_quantity:
                if self._rebalance_actions_planner.client.allow_skip_asset:
                    self._get_logger().warning(
                        f"Skipping {symbol} buy: available funds are too low to buy {ratio*trading_constants.ONE_HUNDRED}% "
                        f"of {reference_market_to_split} holdings: {round(ideal_amount / effective_min_order_size_margin, 9)} {coin}"
                    )
                    continue
                # if we can't create an order in this case, we won't be able to balance the portfolio.
                # don't try to avoid triggering new rebalances on each wakeup cycling market sell & buy orders
                raise trading_errors.MissingMinimalExchangeTradeVolume(
                    f"Can't buy {symbol}: available funds are too low to buy {ratio*trading_constants.ONE_HUNDRED}% "
                    f"of {reference_market_to_split} holdings: {round(ideal_amount / effective_min_order_size_margin, 9)} {coin} "
                    f"required order size is not compatible with {symbol} exchange requirements: "
                    f"{symbol_market[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS.value]}."
                )

            amount_by_symbol[symbol] = {
                IDEAL_AMOUNT: ideal_amount,
                IDEAL_PRICE: price,
            }
        return amount_by_symbol

    def _get_coins_to_sell(self, details: dict[str, typing.Any]) -> list:
        return list(details[rebalancer_enums.RebalanceDetails.SWAP.value]) or (
            self._rebalance_actions_planner.targeted_coins
        )

    def _get_pending_open_quantity(self, symbol: str) -> decimal.Decimal:
        return self._exchange_interface.private_data.get_pending_open_quantity(symbol)

    async def _cancel_symbol_open_orders(
        self,
        symbol: str,
        dependencies: typing.Optional[commons_signals.SignalDependencies],
        allowed_sides: typing.Optional[set[trading_enums.TradeOrderSide]] = None
    ) -> typing.Optional[commons_signals.SignalDependencies]:
        return await self._exchange_interface.private_data.cancel_symbol_open_orders(
            symbol, dependencies, allowed_sides=allowed_sides
        )

    async def _pre_cancel_conflicting_orders(
        self,
        details: dict[str, typing.Any],
        dependencies: typing.Optional[commons_signals.SignalDependencies],
        side: trading_enums.TradeOrderSide
    ) -> None:
        symbols_to_cleanup = self._get_pre_cancel_order_symbols(details, side)
        for symbol in symbols_to_cleanup:
            await self._cancel_symbol_open_orders(
                symbol,
                dependencies=dependencies,
                allowed_sides={side}
            )

    def _get_pre_cancel_order_symbols(self, details: dict[str, typing.Any], side: trading_enums.TradeOrderSide) -> set[str]:
        symbols_to_cleanup: set[str] = set()
        keys = self._get_rebalance_details_keys_for_side(side)

        for key in keys:
            for coin_or_symbol in details.get(key, {}):
                symbols_to_cleanup.add(self._get_symbol_and_base_asset(coin_or_symbol)[0])
        return symbols_to_cleanup

    def _get_rebalance_details_keys_for_side(self, side: trading_enums.TradeOrderSide) -> list[str]:
        if side == trading_enums.TradeOrderSide.BUY:
            return [rebalancer_enums.RebalanceDetails.REMOVE.value, rebalancer_enums.RebalanceDetails.SELL_SOME.value]
        if side == trading_enums.TradeOrderSide.SELL:
            return [rebalancer_enums.RebalanceDetails.ADD.value, rebalancer_enums.RebalanceDetails.BUY_MORE.value]
        raise ValueError(f"Unsupported side: {side}")

    def _get_symbol_and_base_asset(self, coin_or_symbol: str) -> tuple[str, str]:
        if symbol_util.is_symbol(coin_or_symbol):
            return coin_or_symbol, symbol_util.parse_symbol(coin_or_symbol).base # type: ignore
        return symbol_util.merge_currencies(coin_or_symbol, self._exchange_interface.private_data.reference_market), coin_or_symbol

    def _get_logger(self):
        return logging.get_logger(self.__class__.__name__)
