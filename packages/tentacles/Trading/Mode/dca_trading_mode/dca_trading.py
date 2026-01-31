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
import enum
import typing

import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.evaluators_util as evaluators_util
import octobot_commons.signals as commons_signals

import octobot_evaluators.api as evaluators_api
import octobot_evaluators.constants as evaluators_constants
import octobot_evaluators.enums as evaluators_enums
import octobot_evaluators.matrix as matrix

import octobot_trading.modes as trading_modes
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.util as trading_util
import octobot_trading.errors as trading_errors
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.modes.script_keywords as script_keywords


class TriggerMode(enum.Enum):
    TIME_BASED = "Time based"
    MAXIMUM_EVALUATORS_SIGNALS_BASED = "Maximum evaluators signals based"


class DCATradingModeConsumer(trading_modes.AbstractTradingModeConsumer):
    AMOUNT_TO_BUY_IN_REF_MARKET = "amount_to_buy_in_reference_market"
    ENTRY_LIMIT_ORDERS_PRICE_PERCENT = "entry_limit_orders_price_percent"
    USE_MARKET_ENTRY_ORDERS = "use_market_entry_orders"
    USE_INIT_ENTRY_ORDERS = "use_init_entry_orders"
    USE_SECONDARY_ENTRY_ORDERS = "use_secondary_entry_orders"
    SECONDARY_ENTRY_ORDERS_COUNT = "secondary_entry_orders_count"
    SECONDARY_ENTRY_ORDERS_AMOUNT = "secondary_entry_orders_amount"
    SECONDARY_ENTRY_ORDERS_PRICE_PERCENT = "secondary_entry_orders_price_percent"
    DEFAULT_ENTRY_LIMIT_PRICE_MULTIPLIER = decimal.Decimal("0.05")  # 5% by default
    DEFAULT_SECONDARY_ENTRY_ORDERS_COUNT = 0
    DEFAULT_SECONDARY_ENTRY_ORDERS_AMOUNT = ""
    DEFAULT_SECONDARY_ENTRY_ORDERS_PRICE_MULTIPLIER = DEFAULT_ENTRY_LIMIT_PRICE_MULTIPLIER

    USE_TAKE_PROFIT_EXIT_ORDERS = "use_take_profit_exit_orders"
    EXIT_LIMIT_ORDERS_PRICE_PERCENT = "exit_limit_orders_price_percent"
    DEFAULT_EXIT_LIMIT_PRICE_MULTIPLIER = DEFAULT_ENTRY_LIMIT_PRICE_MULTIPLIER
    USE_SECONDARY_EXIT_ORDERS = "use_secondary_exit_orders"
    SECONDARY_EXIT_ORDERS_COUNT = "secondary_exit_orders_count"
    SECONDARY_EXIT_ORDERS_PRICE_PERCENT = "secondary_exit_orders_price_percent"
    DEFAULT_SECONDARY_EXIT_ORDERS_COUNT = 0
    DEFAULT_SECONDARY_EXIT_ORDERS_PRICE_MULTIPLIER = DEFAULT_ENTRY_LIMIT_PRICE_MULTIPLIER

    USE_STOP_LOSSES = "use_stop_losses"
    STOP_LOSS_PRICE_PERCENT = "stop_loss_price_percent"
    DEFAULT_STOP_LOSS_ORDERS_PRICE_MULTIPLIER = 2 * DEFAULT_ENTRY_LIMIT_PRICE_MULTIPLIER

    async def create_new_orders(self, symbol, _, state, **kwargs):
        current_order = None
        initial_dependencies = kwargs.get(self.CREATE_ORDER_DEPENDENCIES_PARAM, None)
        post_cancel_dependencies = None
        try:
            price = await trading_personal_data.get_up_to_date_price(
                self.exchange_manager, symbol, timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT
            )
            symbol_market = self.exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
            created_orders = []
            ctx = script_keywords.get_base_context(self.trading_mode, symbol)
            if state is trading_enums.EvaluatorStates.NEUTRAL.value:
                raise trading_errors.NotSupported(state)
            side = trading_enums.TradeOrderSide.BUY if state in (
                trading_enums.EvaluatorStates.LONG.value, trading_enums.EvaluatorStates.VERY_LONG.value
            ) else trading_enums.TradeOrderSide.SELL

            secondary_quantity = None
            if user_amount := trading_modes.get_user_selected_order_amount(
                self.trading_mode, trading_enums.TradeOrderSide.BUY
            ):
                initial_entry_price = price if self.trading_mode.use_market_entry_orders else \
                    trading_personal_data.decimal_adapt_price(
                        symbol_market,
                        price * (
                            1 - self.trading_mode.entry_limit_orders_price_multiplier
                            if side is trading_enums.TradeOrderSide.BUY
                            else 1 + self.trading_mode.entry_limit_orders_price_multiplier
                        )
                    )
                if self.trading_mode.cancel_open_orders_at_each_entry:
                    post_cancel_dependencies = await self._cancel_existing_orders_if_replaceable(
                        ctx, symbol, user_amount, price, initial_entry_price, 
                        side, symbol_market, initial_dependencies
                    )

                quantity = await script_keywords.get_amount_from_input_amount(
                    context=ctx,
                    input_amount=user_amount,
                    side=side.value,
                    reduce_only=False,
                    is_stop_order=False,
                    use_total_holding=False,
                )

                if self.trading_mode.use_secondary_entry_orders and self.trading_mode.secondary_entry_orders_amount:
                    # compute secondary orders quantity before locking quantity from initial order
                    secondary_quantity = await script_keywords.get_amount_from_input_amount(
                        context=ctx,
                        input_amount=self.trading_mode.secondary_entry_orders_amount,
                        side=side.value,
                        reduce_only=False,
                        is_stop_order=False,
                        use_total_holding=False,
                    )
            else:
                self.logger.error(
                        f"Missing {side.value} entry order quantity in {self.trading_mode.get_name()} configuration"
                        f", please set the \"Amount per buy order\" value.")
                return []

            # consider holdings only after orders have been cancelled
            current_symbol_holding, current_market_holding, market_quantity = (
                trading_personal_data.get_portfolio_amounts(
                    self.exchange_manager, symbol, price
                )
            )
            if self.exchange_manager.is_future:
                self.trading_mode.ensure_supported(symbol)
                # on futures, current_symbol_holding = current_market_holding = market_quantity
                initial_available_base_funds, _ = trading_personal_data.get_futures_max_order_size(
                    self.exchange_manager, symbol, side,
                    price, False, current_symbol_holding, market_quantity
                )
                initial_available_quote_funds = initial_available_base_funds * price
            else:
                initial_available_quote_funds = current_market_holding \
                    if side is trading_enums.TradeOrderSide.BUY else current_symbol_holding
            if side is trading_enums.TradeOrderSide.BUY:
                initial_entry_order_type = trading_enums.TraderOrderType.BUY_MARKET \
                    if self.trading_mode.use_market_entry_orders else trading_enums.TraderOrderType.BUY_LIMIT
            else:
                initial_entry_order_type = trading_enums.TraderOrderType.SELL_MARKET \
                    if self.trading_mode.use_market_entry_orders else trading_enums.TraderOrderType.SELL_LIMIT
            adapted_entry_quantity = trading_personal_data.decimal_adapt_order_quantity_because_fees(
                self.exchange_manager, symbol, initial_entry_order_type, quantity, initial_entry_price, side
            )

            # initial entry
            orders_should_have_been_created = await self._create_entry_order(
                initial_entry_order_type, adapted_entry_quantity, initial_entry_price,
                symbol_market, symbol, created_orders, price, post_cancel_dependencies
            )
            # secondary entries
            if self.trading_mode.use_secondary_entry_orders and self.trading_mode.secondary_entry_orders_count > 0:
                secondary_order_type = trading_enums.TraderOrderType.BUY_LIMIT \
                    if side is trading_enums.TradeOrderSide.BUY else trading_enums.TraderOrderType.SELL_LIMIT
                if not secondary_quantity:
                    if self.trading_mode.secondary_entry_orders_amount:
                        self.logger.warning(
                            f"Impossible to create {side.value} secondary entry order: computed quantity is {secondary_quantity}, "
                            f"configured quantity is: {self.trading_mode.secondary_entry_orders_amount}."
                        )
                    else:
                        self.logger.error(
                            f"Missing {side.value} secondary entry order quantity in {self.trading_mode.get_name()} "
                            f"configuration, please set the \"Secondary entry orders count\" value "
                            f"when enabling secondary entry orders."
                        )
                else:
                    for i in range(self.trading_mode.secondary_entry_orders_count):
                        remaining_funds = initial_available_quote_funds - sum(
                            trading_personal_data.get_locked_funds(order)
                            for order in created_orders
                        )
                        adapted_secondary_quantity = trading_personal_data.decimal_adapt_order_quantity_because_fees(
                            self.exchange_manager, symbol, initial_entry_order_type, secondary_quantity,
                            initial_entry_price, side
                        )
                        skip_other_orders = adapted_secondary_quantity != secondary_quantity
                        if skip_other_orders or remaining_funds < (
                            (secondary_quantity * initial_entry_price)
                            if side is trading_enums.TradeOrderSide.BUY else secondary_quantity
                        ):
                            self.logger.debug(
                                f"Not enough available funds to create {symbol} {i + 1}/"
                                f"{self.trading_mode.secondary_entry_orders_count} secondary order with quantity of "
                                f"{secondary_quantity} on {self.exchange_manager.exchange_name}"
                            )
                            continue
                        multiplier = self.trading_mode.entry_limit_orders_price_multiplier + \
                            (i + 1) * self.trading_mode.secondary_entry_orders_price_multiplier
                        secondary_target_price = price * (
                            (1 - multiplier) if side is trading_enums.TradeOrderSide.BUY else
                            (1 + multiplier)
                        )
                        if not await self._create_entry_order(
                            secondary_order_type, secondary_quantity, secondary_target_price,
                            symbol_market, symbol, created_orders, price, post_cancel_dependencies
                        ):
                            # stop iterating if an order can't be created
                            self.logger.info(
                                f"Stopping {self.exchange_manager.exchange_name} {symbol} entry orders creation "
                                f"on secondary order {i + 1}/{self.trading_mode.secondary_entry_orders_count}."
                            )
                            break
            if created_orders:
                return created_orders
            if orders_should_have_been_created:
                raise trading_errors.OrderCreationError()
            raise trading_errors.MissingMinimalExchangeTradeVolume()

        except (
            trading_errors.MissingFunds,
            trading_errors.MissingMinimalExchangeTradeVolume,
            trading_errors.OrderCreationError,
            trading_errors.InvalidCancelPolicyError,
            trading_errors.TraderDisabledError
        ):
            raise
        except Exception as err:
            self.logger.exception(
                err, True, f"Failed to create order : {err}. Order: {current_order if current_order else None}"
            )
            return []

    async def _cancel_existing_orders_if_replaceable(
        self, ctx, symbol, user_amount, price, initial_entry_price, 
        side, symbol_market, dependencies
    ) -> typing.Optional[commons_signals.SignalDependencies]:
        next_step_dependencies = None
        if to_cancel_orders := [
            order
            for order in self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol=symbol)
            if not (order.is_cancelled() or order.is_closed() or order.is_partially_filled()) and side is order.side
        ]:
            # Cancel existing DCA orders of the same side from previous iterations
            # Edge cases about cancelling existing orders when recreating entry orders
            # 1. max holding ratio is reached, meaning that portfolio + open orders already contain the
            # max % of asset
            #   => in this case, we still want to be able to replace open orders of any.
            #   Need to cancel open orders 1st
            # 2. value of the portfolio or available holdings dropped to the point that user configured
            # amount
            # is now too small to comply with min exchange rules.
            #   => in this case, orders won't be able to be created.
            #   Open orders should not be cancelled
            # Conclusion:
            #   => Always cancel orders first except when exchange min amount would be reached in new
            #   buy orders
            next_step_dependencies = commons_signals.SignalDependencies()
            can_create_entries = await self._can_create_entry_orders_regarding_min_exchange_order_size(
                ctx, user_amount, price, initial_entry_price, side, symbol_market, to_cancel_orders
            )
            if can_create_entries:
                for order in to_cancel_orders:
                    try:
                        is_cancelled, new_dependencies = await self.trading_mode.cancel_order(
                            order, dependencies=dependencies
                        )
                        if is_cancelled:
                            next_step_dependencies.extend(new_dependencies)
                    except trading_errors.UnexpectedExchangeSideOrderStateError as err:
                        self.logger.warning(f"Skipped order cancel: {err}, order: {order}")
            else:
                self.logger.info(
                    f"Skipping {self.exchange_manager.exchange_name} {symbol} entry order cancel as new "
                    f"entries are likely not complying with exchange minimal order size."
                )
        return next_step_dependencies or dependencies

    async def _can_create_entry_orders_regarding_min_exchange_order_size(
        self, ctx, user_amount, price, initial_entry_price, side, symbol_market, to_cancel_orders
    ):
        quantity = await script_keywords.get_amount_from_input_amount(
            context=ctx,
            input_amount=user_amount,
            side=side.value,
            reduce_only=False,
            is_stop_order=False,
            use_total_holding=False,
            orders_to_be_ignored=to_cancel_orders,  # consider existing orders as cancelled
        )
        can_create_entries = self._is_above_exchange_min_order_size(quantity, initial_entry_price, symbol_market)
        if (
            can_create_entries and
            self.trading_mode.use_secondary_entry_orders and
            self.trading_mode.secondary_entry_orders_amount
        ):
            # compute secondary orders quantity before locking quantity from initial order
            if secondary_quantity := await script_keywords.get_amount_from_input_amount(
                context=ctx,
                input_amount=self.trading_mode.secondary_entry_orders_amount,
                side=side.value,
                reduce_only=False,
                is_stop_order=False,
                use_total_holding=False,
                orders_to_be_ignored=to_cancel_orders,  # consider existing orders as cancelled
            ):
                # check that at least the 1st secondary order can be created
                multiplier = self.trading_mode.entry_limit_orders_price_multiplier + (
                    1 * self.trading_mode.secondary_entry_orders_price_multiplier
                )
                secondary_target_price = price * (
                    (1 - multiplier) if side is trading_enums.TradeOrderSide.BUY else
                    (1 + multiplier)
                )
                can_create_entries = self._is_above_exchange_min_order_size(
                    secondary_quantity, secondary_target_price, symbol_market
                )
        return can_create_entries

    def _is_above_exchange_min_order_size(self, quantity, price, symbol_market):
        return bool(
            trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                quantity,
                price,
                symbol_market
            )
        )

    async def _create_entry_order(
        self, order_type, quantity, price, symbol_market, 
        symbol, created_orders, current_price, dependencies
    ):
        if self._is_max_asset_ratio_reached(symbol):
            # do not create entry on symbol when max ratio is reached
            return False
        for order_quantity, order_price in \
                trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                    quantity,
                    price,
                    symbol_market
                ):
            entry_order = trading_personal_data.create_order_instance(
                trader=self.exchange_manager.trader,
                order_type=order_type,
                symbol=symbol,
                current_price=current_price,
                quantity=order_quantity,
                price=order_price
            )
            created_at_least_one_order = False
            try:
                if created_order := await self._create_entry_with_chained_exit_orders(
                    entry_order, price, symbol_market, dependencies
                ):
                    created_orders.append(created_order)
                    created_at_least_one_order = True
                    return True
            except trading_errors.MaxOpenOrderReachedForSymbolError as err:
                self.logger.warning(
                    f"Impossible to create {symbol} entry ({entry_order.side.value}) order: "
                    f"creating more orders would exceed {self.exchange_manager.exchange_name}'s limits: {err}"
                )
                return created_at_least_one_order
        try:
            buying = order_type in (trading_enums.TraderOrderType.BUY_MARKET, trading_enums.TraderOrderType.BUY_LIMIT)
            parsed_symbol = symbol_util.parse_symbol(symbol)
            missing_currency = parsed_symbol.quote if buying else parsed_symbol.base
            settlement_asset = parsed_symbol.settlement_asset if parsed_symbol.is_future() else parsed_symbol.quote
            quantity_currency = trading_personal_data.get_order_quantity_currency(self.exchange_manager, symbol)
            if parsed_symbol.is_spot():
                cost = quantity * price
            else:
                cost = quantity
            min_cost = trading_personal_data.get_minimal_order_cost(symbol_market, default_price=float(price))
            min_amount = trading_personal_data.get_minimal_order_amount(symbol_market)
            self.logger.info(
                f"Please get more {missing_currency}: {symbol} {order_type.value} not created on "
                f"{self.exchange_manager.exchange_name}: exchange order requirements are not met. "
                f"Attempted order cost: {cost} {settlement_asset}, quantity: {quantity} {quantity_currency}, "
                f"price: {price}, min cost: {min_cost} {settlement_asset}, min amount: {min_amount} {quantity_currency}"
            )
        except Exception as err:
            self.logger.exception(err, True, f"Error when creating error message {err}")
        return False

    async def _create_entry_with_chained_exit_orders(
        self, entry_order, entry_price, symbol_market, dependencies
    ):
        params = {}
        exit_side = (
            trading_enums.TradeOrderSide.SELL 
            if entry_order.side is trading_enums.TradeOrderSide.BUY
            else trading_enums.TradeOrderSide.BUY
        )
        exit_multiplier_side_flag = 1 if exit_side is trading_enums.TradeOrderSide.SELL else -1
        total_exists_count = 1 + (
            self.trading_mode.secondary_exit_orders_count if self.trading_mode.use_secondary_exit_orders else 0
        )
        stop_price = entry_price * (
            trading_constants.ONE - (
                self.trading_mode.stop_loss_price_multiplier * exit_multiplier_side_flag
            )
        )
        first_sell_price = entry_price * (
            trading_constants.ONE + (
                self.trading_mode.exit_limit_orders_price_multiplier * exit_multiplier_side_flag
            )
        )
        last_sell_price = entry_price * (
            trading_constants.ONE + (
                self.trading_mode.secondary_exit_orders_price_multiplier *
                (1 + self.trading_mode.secondary_exit_orders_count) * exit_multiplier_side_flag
            )
        )
        # split entry into multiple exits if necessary (and possible)
        exit_quantities = self._split_entry_quantity(
            entry_order.origin_quantity, total_exists_count,
            min(stop_price, first_sell_price, last_sell_price),
            max(stop_price, first_sell_price, last_sell_price),
            symbol_market
        )
        can_bundle_exit_orders = len(exit_quantities) == 1
        reduce_only_chained_orders = self.exchange_manager.is_future
        exit_orders = []
        # 1. ensure entry order can be created
        if entry_order.order_type not in (
            trading_enums.TraderOrderType.BUY_MARKET, trading_enums.TraderOrderType.SELL_MARKET
        ):
            trading_personal_data.ensure_orders_limit(
                self.exchange_manager, entry_order.symbol, [trading_enums.TraderOrderType.BUY_LIMIT]
            )
        for i, exit_quantity in exit_quantities:
            is_last = i == len(exit_quantities)
            order_couple = []
            # stop loss
            if self.trading_mode.use_stop_loss:
                # 1. ensure order can be created
                exit_orders.append(trading_enums.TraderOrderType.STOP_LOSS)
                trading_personal_data.ensure_orders_limit(self.exchange_manager, entry_order.symbol, exit_orders)
                # 2. initialize order
                stop_price = trading_personal_data.decimal_adapt_price(symbol_market, stop_price)
                param_update, chained_order = await self.register_chained_order(
                    entry_order, stop_price, trading_enums.TraderOrderType.STOP_LOSS, exit_side,
                    quantity=exit_quantity, allow_bundling=can_bundle_exit_orders,
                    reduce_only=reduce_only_chained_orders,
                    # only the last order is to take trigger fees into account
                    update_with_triggering_order_fees=is_last and not self.exchange_manager.is_future
                )
                params.update(param_update)
                order_couple.append(chained_order)
            # take profit
            if self.trading_mode.use_take_profit_exit_orders:
                # 1. ensure order can be created
                take_profit_order_type = self.exchange_manager.trader.get_take_profit_order_type(
                    entry_order,
                    trading_enums.TraderOrderType.BUY_LIMIT
                    if exit_side is trading_enums.TradeOrderSide.BUY else trading_enums.TraderOrderType.SELL_LIMIT
                )
                exit_orders.append(take_profit_order_type)
                trading_personal_data.ensure_orders_limit(self.exchange_manager, entry_order.symbol, exit_orders)
                # 2. initialize order
                take_profit_multiplier = self.trading_mode.exit_limit_orders_price_multiplier \
                    if i == 1 else (
                        self.trading_mode.exit_limit_orders_price_multiplier +
                        self.trading_mode.secondary_exit_orders_price_multiplier * i
                    )
                take_profit_price = trading_personal_data.decimal_adapt_price(
                    symbol_market,
                    entry_price * (
                            trading_constants.ONE + (take_profit_multiplier * exit_multiplier_side_flag)
                    )
                )
                param_update, chained_order = await self.register_chained_order(
                    entry_order, take_profit_price, take_profit_order_type, None,
                    quantity=exit_quantity, allow_bundling=can_bundle_exit_orders,
                    reduce_only=reduce_only_chained_orders,
                    # only the last order is to take trigger fees into account
                    update_with_triggering_order_fees=is_last and not self.exchange_manager.is_future
                )
                params.update(param_update)
                order_couple.append(chained_order)
            if len(order_couple) > 1:
                oco_group = self.exchange_manager.exchange_personal_data.orders_manager.create_group(
                    trading_personal_data.OneCancelsTheOtherOrderGroup,
                    active_order_swap_strategy=trading_personal_data.StopFirstActiveOrderSwapStrategy()
                )
                for order in order_couple:
                    order.add_to_order_group(oco_group)
                # in futures, inactive orders are not necessary
                if self.exchange_manager.trader.enable_inactive_orders and not self.exchange_manager.is_future:
                    await oco_group.active_order_swap_strategy.apply_inactive_orders(order_couple)
        return await self.trading_mode.create_order(
            entry_order, params=params or None, dependencies=dependencies
        )

    def _is_max_asset_ratio_reached(self, symbol):
        if self.exchange_manager.is_future:
            # not implemented for futures
            return False
        asset = symbol_util.parse_symbol(symbol).base
        ratio = self.exchange_manager.exchange_personal_data.portfolio_manager. \
            portfolio_value_holder.get_holdings_ratio(asset, include_assets_in_open_orders=True)
        if ratio >= self.trading_mode.max_asset_holding_ratio:
            self.logger.info(
                f"Max holding ratio reached for {asset}: ratio: {ratio}, max ratio: "
                f"{self.trading_mode.max_asset_holding_ratio}. Skipping {symbol} entry order."
            )
            return True
        return False

    @staticmethod
    def _split_entry_quantity(quantity, target_exits_count, lowest_price, highest_price, symbol_market):
        if target_exits_count == 1:
            return [(1, quantity)]
        adapted_sell_orders_count, increment = trading_personal_data.get_split_orders_count_and_increment(
            lowest_price, highest_price, quantity, target_exits_count, symbol_market, False
        )
        if adapted_sell_orders_count:
            return [
                (
                    i + 1,
                    trading_personal_data.decimal_adapt_quantity(symbol_market, quantity / adapted_sell_orders_count)
                )
                for i in range(adapted_sell_orders_count)
            ]
        else:
            return []

    def skip_portfolio_available_check_before_creating_orders(self) -> bool:
        """
        When returning true, will skip portfolio available funds check
        before calling self.create_new_orders().
        Override if necessary
        """
        # will cancel open orders: skip available checks
        return self.trading_mode.cancel_open_orders_at_each_entry


class DCATradingModeProducer(trading_modes.AbstractTradingModeProducer):
    MINUTES_BEFORE_NEXT_BUY = "minutes_before_next_buy"
    TRIGGER_MODE = "trigger_mode"
    CANCEL_OPEN_ORDERS_AT_EACH_ENTRY = "cancel_open_orders_at_each_entry"
    HEALTH_CHECK_ORPHAN_FUNDS_THRESHOLD = "health_check_orphan_funds_threshold"
    MAX_ASSET_HOLDING_PERCENT = "max_asset_holding_percent"

    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        self.task = None
        self.state = trading_enums.EvaluatorStates.NEUTRAL

    async def stop(self):
        if self.trading_mode is not None:
            self.trading_mode.flush_trading_mode_consumers()
        if self.task is not None:
            self.task.cancel()
        await super().stop()

    async def set_final_eval(self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame, trigger_source: str):
        evaluations = []
        # Strategies analysis
        for evaluated_strategy_node in matrix.get_tentacles_value_nodes(
                matrix_id,
                matrix.get_tentacle_nodes(matrix_id,
                                          exchange_name=self.exchange_name,
                                          tentacle_type=evaluators_enums.EvaluatorMatrixTypes.STRATEGIES.value),
                cryptocurrency=cryptocurrency,
                symbol=symbol):

            if evaluators_util.check_valid_eval_note(evaluators_api.get_value(evaluated_strategy_node),
                                                     evaluators_api.get_type(evaluated_strategy_node),
                                                     evaluators_constants.EVALUATOR_EVAL_DEFAULT_TYPE):
                evaluations.append(evaluators_api.get_value(evaluated_strategy_node))

        is_forced_init_entry = self._should_trigger_init_entry()
        if evaluations or is_forced_init_entry:
            state = trading_enums.EvaluatorStates.NEUTRAL
            if is_forced_init_entry:
                self.logger.info(
                    f"Triggering {self.trading_mode.symbol} init entries [{self.exchange_manager.exchange_name}]"
                )
                state = trading_enums.EvaluatorStates.VERY_LONG
            elif all(
                evaluation == -1
                for evaluation in evaluations
            ):
                state = trading_enums.EvaluatorStates.VERY_LONG
            elif all(
                evaluation == 1
                for evaluation in evaluations
            ):
                state = trading_enums.EvaluatorStates.VERY_SHORT
            self.final_eval = evaluations
            try:
                await self.trigger_dca(cryptocurrency=cryptocurrency, symbol=symbol, state=state)
            finally:
                try:
                    self.trading_mode.are_initialization_orders_pending = False
                except AttributeError:
                    if self.trading_mode is None:
                        # can very rarely happen on early cancelled backtestings
                        self.logger.warning(
                            f"{self.__class__.__name__} has already been stopped, skipping are_initialization_orders_pending setting"
                        )
                    else:
                        # unexpected error, raise
                        raise

    def _should_trigger_init_entry(self):
        if self.trading_mode.enable_initialization_entry:
            return self.trading_mode.are_initialization_orders_pending
        return False

    @trading_modes.enabled_trader_only()
    async def trigger_dca(self, cryptocurrency: str, symbol: str, state: trading_enums.EvaluatorStates):
        if self.trading_mode.max_asset_holding_ratio < trading_constants.ONE:
            # if holding ratio should be checked, wait for price init to be able to compute this ratio
            await self._wait_for_symbol_prices_and_profitability_init(self._get_config_init_timeout())
        self.state = state
        self.logger.debug(
            f"{symbol} DCA triggered on {self.exchange_manager.exchange_name}, state: {self.state.value}"
        )
        if self.state is trading_enums.EvaluatorStates.NEUTRAL:
            self.last_activity = trading_modes.TradingModeActivity(trading_enums.TradingModeActivityType.NOTHING_TO_DO)
        else:
            self.last_activity = trading_modes.TradingModeActivity(trading_enums.TradingModeActivityType.CREATED_ORDERS)
            await self._process_entries(cryptocurrency, symbol, state)
            await self._process_exits(cryptocurrency, symbol, state)

    async def _process_pre_entry_actions(self, symbol: str, side=trading_enums.PositionSide.BOTH):
        try:
            # if position is idle, ensure leverage is set according to configuration
            if (
                self.exchange_manager.is_future and
                self.exchange_manager.exchange_personal_data.positions_manager.get_symbol_position(
                    symbol, side
                ).is_idle()
            ):
                config_leverage = await script_keywords.user_select_leverage(
                    script_keywords.get_base_context(self.trading_mode, symbol=symbol), def_val=0
                )
                if config_leverage:
                    parsed_leverage = decimal.Decimal(str(config_leverage))
                    current_leverage = self.exchange_manager.exchange.get_pair_contract(symbol).current_leverage
                    if parsed_leverage != current_leverage:
                        self.logger.info(f"Updating leverage of {symbol} from {current_leverage} to {parsed_leverage}")
                        await self.trading_mode.set_leverage(symbol, side, parsed_leverage)
        except Exception as err:
            self.logger.exception(
                err, True, f"Error when processing pre_state_update_actions: {err} ({symbol=} {side=})"
            )

    async def _process_entries(self, cryptocurrency: str, symbol: str, state: trading_enums.EvaluatorStates):
        entry_side = trading_enums.TradeOrderSide.BUY if state in (
            trading_enums.EvaluatorStates.LONG, trading_enums.EvaluatorStates.VERY_LONG
        ) else trading_enums.TradeOrderSide.SELL
        if entry_side is trading_enums.TradeOrderSide.SELL:
            self.logger.debug(f"{entry_side.value} entry side not supported for now. Ignored state: {state.value})")
            return
        await self._process_pre_entry_actions(symbol)
        # call orders creation from consumers
        await self.submit_trading_evaluation(
            cryptocurrency=cryptocurrency,
            symbol=symbol,
            time_frame=None,
            final_note=None,
            state=state
        )
        # send_notification
        await self._send_alert_notification(symbol, state, "entry")

    async def _process_exits(self, cryptocurrency: str, symbol: str, state: trading_enums.EvaluatorStates):
        # todo implement signal based exits
        pass

    async def dca_task(self):
        while not self.should_stop:
            try:
                for cryptocurrency, pairs in trading_util.get_traded_pairs_by_currency(
                        self.exchange_manager.config
                ).items():
                    if self.trading_mode.symbol in pairs:
                        await self.trigger_dca(
                            cryptocurrency=cryptocurrency,
                            symbol=self.trading_mode.symbol,
                            state=trading_enums.EvaluatorStates.VERY_LONG
                        )
                if self.exchange_manager.is_backtesting:
                    self.logger.error(
                        f"{self.trading_mode.trigger_mode.value} trigger is not supporting backtesting for now. Please "
                        f"configure another trigger mode to use {self.trading_mode.get_name()} in backtesting."
                    )
                    return
                await asyncio.sleep(self.trading_mode.minutes_before_next_buy * commons_constants.MINUTE_TO_SECONDS)
            except Exception as e:
                self.logger.error(f"An error happened during DCA task : {e}")

    async def inner_start(self) -> None:
        await super().inner_start()
        if self.trading_mode.trigger_mode is TriggerMode.TIME_BASED:
            self.task = asyncio.create_task(self.delayed_start())

    def get_channels_registration(self):
        registration_channels = []
        if self.trading_mode.trigger_mode is TriggerMode.MAXIMUM_EVALUATORS_SIGNALS_BASED:
            topic = self.trading_mode.trading_config.get(commons_constants.CONFIG_ACTIVATION_TOPICS.replace(" ", "_"),
                                                         commons_enums.ActivationTopics.EVALUATION_CYCLE.value)
            try:
                registration_channels.append(self.TOPIC_TO_CHANNEL_NAME[topic])
            except KeyError:
                self.logger.error(f"Unknown registration topic: {topic}")
        return registration_channels

    def get_extra_init_symbol_topics(self) -> typing.Optional[list]:
        if self.exchange_manager.is_backtesting:
            # disabled in backtesting as price might not be initialized at this point
            return None
        # required as trigger can happen independently of price events when time based
        return [commons_enums.InitializationEventExchangeTopics.PRICE.value]

    async def delayed_start(self):
        await self.dca_task()

    async def _send_alert_notification(self, symbol, state, step):
        if self.exchange_manager.is_backtesting:
            return
        try:
            import octobot_services.api as services_api
            import octobot_services.enums as services_enum
            action = "unknown"
            if state in (trading_enums.EvaluatorStates.LONG, trading_enums.EvaluatorStates.VERY_LONG):
                action = "BUYING"
            elif state in (trading_enums.EvaluatorStates.SHORT, trading_enums.EvaluatorStates.VERY_SHORT):
                action = "SELLING"
            title = f"DCA {step} trigger for : #{symbol}"
            alert = f"{action} on {self.exchange_manager.exchange_name}"
            await services_api.send_notification(services_api.create_notification(
                alert, title=title, markdown_text=alert,
                category=services_enum.NotificationCategory.PRICE_ALERTS
            ))
        except ImportError as e:
            self.logger.exception(e, True, f"Impossible to send notification: {e}")


class DCATradingMode(trading_modes.AbstractTradingMode):
    MODE_PRODUCER_CLASSES = [DCATradingModeProducer]
    MODE_CONSUMER_CLASSES = [DCATradingModeConsumer]
    SUPPORTS_INITIAL_PORTFOLIO_OPTIMIZATION = True
    SUPPORTS_HEALTH_CHECK = True
    DEFAULT_HEALTH_CHECK_SELL_ORPHAN_FUNDS_RATIO_THRESHOLD = decimal.Decimal("0.1")  # 10%
    HEALTH_CHECK_FILL_ORDERS_TIMEOUT = 20

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.enable_initialization_entry = False
        self.use_market_entry_orders = False
        self.trigger_mode = TriggerMode.TIME_BASED
        self.minutes_before_next_buy = None

        self.entry_limit_orders_price_multiplier = DCATradingModeConsumer.DEFAULT_ENTRY_LIMIT_PRICE_MULTIPLIER
        self.use_secondary_entry_orders = False
        self.secondary_entry_orders_count = DCATradingModeConsumer.DEFAULT_SECONDARY_ENTRY_ORDERS_COUNT
        self.secondary_entry_orders_amount = DCATradingModeConsumer.DEFAULT_SECONDARY_ENTRY_ORDERS_AMOUNT
        self.secondary_entry_orders_price_multiplier = DCATradingModeConsumer.DEFAULT_ENTRY_LIMIT_PRICE_MULTIPLIER

        self.use_take_profit_exit_orders = False
        self.exit_limit_orders_price_multiplier = DCATradingModeConsumer.DEFAULT_EXIT_LIMIT_PRICE_MULTIPLIER
        self.use_secondary_exit_orders = False
        self.secondary_exit_orders_count = DCATradingModeConsumer.DEFAULT_SECONDARY_EXIT_ORDERS_COUNT
        self.secondary_exit_orders_price_multiplier = DCATradingModeConsumer.DEFAULT_ENTRY_LIMIT_PRICE_MULTIPLIER

        self.use_stop_loss = False
        self.stop_loss_price_multiplier = DCATradingModeConsumer.DEFAULT_STOP_LOSS_ORDERS_PRICE_MULTIPLIER

        self.cancel_open_orders_at_each_entry = True
        self.health_check_orphan_funds_threshold = self.DEFAULT_HEALTH_CHECK_SELL_ORPHAN_FUNDS_RATIO_THRESHOLD
        self.max_asset_holding_ratio = trading_constants.ONE
        self.max_asset_holding_ratio = decimal.Decimal("0.5")
        # self.max_asset_holding_ratio = decimal.Decimal("0.66")
        # self.max_asset_holding_ratio = decimal.Decimal("1")

        # enable initialization orders
        self.are_initialization_orders_pending = True

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        default_config = self.get_default_config()
        self.trigger_mode = TriggerMode(
            self.UI.user_input(
                DCATradingModeProducer.TRIGGER_MODE, commons_enums.UserInputTypes.OPTIONS,
                default_config[DCATradingModeProducer.TRIGGER_MODE],
                inputs, options=[mode.value for mode in TriggerMode],
                title="Trigger mode: When should DCA entry orders should be triggered."
            )
        )
        self.minutes_before_next_buy = int(self.UI.user_input(
            DCATradingModeProducer.MINUTES_BEFORE_NEXT_BUY, commons_enums.UserInputTypes.INT,
            default_config[DCATradingModeProducer.MINUTES_BEFORE_NEXT_BUY], inputs,
            min_val=1,
            title="Trigger period: Minutes to wait between each transaction. Examples: 60 for 1 hour, 1440 for 1 day, "
                  "10080 for 1 week or 43200 for 1 month.",
            editor_options={
                commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                    DCATradingModeProducer.TRIGGER_MODE: TriggerMode.TIME_BASED.value
                }
            }
        ))
        self.enable_initialization_entry = self.UI.user_input(
            DCATradingModeConsumer.USE_INIT_ENTRY_ORDERS, commons_enums.UserInputTypes.BOOLEAN,
            default_config[DCATradingModeConsumer.USE_INIT_ENTRY_ORDERS], inputs,
            title="Enable initialization entry orders: Automatically trigger entry orders "
                  "when starting OctoBot, regardless of initial evaluator values.",
            editor_options={
                commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                    DCATradingModeProducer.TRIGGER_MODE: TriggerMode.MAXIMUM_EVALUATORS_SIGNALS_BASED.value
                }
            }
        )
        trading_modes.user_select_order_amount(self, inputs, include_sell=False)
        self.use_market_entry_orders = self.UI.user_input(
            DCATradingModeConsumer.USE_MARKET_ENTRY_ORDERS, commons_enums.UserInputTypes.BOOLEAN,
            default_config[DCATradingModeConsumer.USE_MARKET_ENTRY_ORDERS], inputs,
            title="Use market orders instead of limit orders."
        )
        self.entry_limit_orders_price_multiplier = decimal.Decimal(str(
            self.UI.user_input(
                DCATradingModeConsumer.ENTRY_LIMIT_ORDERS_PRICE_PERCENT, commons_enums.UserInputTypes.FLOAT,
                float(default_config[DCATradingModeConsumer.ENTRY_LIMIT_ORDERS_PRICE_PERCENT]
                      * trading_constants.ONE_HUNDRED), inputs,
                min_val=0,
                title="Limit entry percent difference: Price difference in percent to compute the entry price from "
                      "when using limit orders. "
                      "Example: 10 on a 2000 USDT price would create a buy limit price at 1800 USDT or "
                      "a sell limit price at 2200 USDT.",
                editor_options={
                    commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                        DCATradingModeConsumer.USE_MARKET_ENTRY_ORDERS: False
                    }
                }
            )
        )) / trading_constants.ONE_HUNDRED
        self.use_secondary_entry_orders = self.UI.user_input(
            DCATradingModeConsumer.USE_SECONDARY_ENTRY_ORDERS, commons_enums.UserInputTypes.BOOLEAN,
            default_config[DCATradingModeConsumer.USE_SECONDARY_ENTRY_ORDERS], inputs,
            title="Enable secondary entry orders: Split entry into multiple orders using different prices."
        )
        self.secondary_entry_orders_count = self.UI.user_input(
            DCATradingModeConsumer.SECONDARY_ENTRY_ORDERS_COUNT, commons_enums.UserInputTypes.INT,
            default_config[DCATradingModeConsumer.SECONDARY_ENTRY_ORDERS_COUNT], inputs,
            title="Secondary entry orders count: Number of secondary limit orders to create alongside the initial "
                  "entry order.",
            editor_options={
                commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                    DCATradingModeConsumer.USE_SECONDARY_ENTRY_ORDERS: True
                }
            }
        )
        self.secondary_entry_orders_price_multiplier = decimal.Decimal(str(
            self.UI.user_input(
                DCATradingModeConsumer.SECONDARY_ENTRY_ORDERS_PRICE_PERCENT, commons_enums.UserInputTypes.FLOAT,
                float(default_config[DCATradingModeConsumer.SECONDARY_ENTRY_ORDERS_PRICE_PERCENT]
                      * trading_constants.ONE_HUNDRED), inputs,
                title="Secondary entry orders price interval percent: Price difference in percent to compute the "
                      "price of secondary entry orders compared to the price of the initial entry order. "
                      "Example: 10 on a 1800 USDT entry buy (with an asset price of 2000) would "
                      "create secondary entry buy orders at 1600 USDT, 1400 USDT and so on.",
                editor_options={
                    commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                        DCATradingModeConsumer.USE_SECONDARY_ENTRY_ORDERS: True
                    }
                }
            )
        )) / trading_constants.ONE_HUNDRED
        self.secondary_entry_orders_amount = self.UI.user_input(
            DCATradingModeConsumer.SECONDARY_ENTRY_ORDERS_AMOUNT, commons_enums.UserInputTypes.TEXT,
            default_config[DCATradingModeConsumer.SECONDARY_ENTRY_ORDERS_AMOUNT], inputs,
            title=f"Secondary entry orders amount: {trading_modes.get_order_amount_value_desc()}",
            other_schema_values={"minLength": 0},
            editor_options={
                commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                    DCATradingModeConsumer.USE_SECONDARY_ENTRY_ORDERS: True
                }
            }
        )
        self.use_take_profit_exit_orders = self.UI.user_input(
            DCATradingModeConsumer.USE_TAKE_PROFIT_EXIT_ORDERS, commons_enums.UserInputTypes.BOOLEAN,
            default_config[DCATradingModeConsumer.USE_TAKE_PROFIT_EXIT_ORDERS], inputs,
            title="Enable take profit exit orders: Automatically create take profit exit orders "
                  "when entries are filled."
        )
        self.exit_limit_orders_price_multiplier = decimal.Decimal(str(
            self.UI.user_input(
                DCATradingModeConsumer.EXIT_LIMIT_ORDERS_PRICE_PERCENT, commons_enums.UserInputTypes.FLOAT,
                float(default_config[DCATradingModeConsumer.EXIT_LIMIT_ORDERS_PRICE_PERCENT]
                      * trading_constants.ONE_HUNDRED), inputs,
                min_val=0,
                title="Limit exit percent difference: Price difference in percent to compute the exit price from "
                      "after an entry is filled. "
                      "Example: 10 on a 2000 USDT filled price buy would create a sell limit price at 2200 USDT.",
                editor_options={
                    commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                        DCATradingModeConsumer.USE_TAKE_PROFIT_EXIT_ORDERS: True
                    }
                }
            )
        )) / trading_constants.ONE_HUNDRED
        self.use_secondary_exit_orders = self.UI.user_input(
            DCATradingModeConsumer.USE_SECONDARY_EXIT_ORDERS, commons_enums.UserInputTypes.BOOLEAN,
            default_config[DCATradingModeConsumer.USE_SECONDARY_EXIT_ORDERS], inputs,
            title="Enable secondary exit orders: Split each filled entry order into into multiple exit orders using "
                  "different prices.",
            editor_options={
                commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                    DCATradingModeConsumer.USE_TAKE_PROFIT_EXIT_ORDERS: True
                }
            }
        )
        self.secondary_exit_orders_count = self.UI.user_input(
            DCATradingModeConsumer.SECONDARY_EXIT_ORDERS_COUNT, commons_enums.UserInputTypes.INT,
            default_config[DCATradingModeConsumer.SECONDARY_EXIT_ORDERS_COUNT], inputs,
            title="Secondary exit orders count: Number of secondary limit orders to create additionally to "
                  "the initial exit order. When enabled, the entry filled amount is split into each exit orders.",
            editor_options={
                commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                    DCATradingModeConsumer.USE_SECONDARY_EXIT_ORDERS: True
                }
            }
        )
        self.secondary_exit_orders_price_multiplier = decimal.Decimal(str(
            self.UI.user_input(
                DCATradingModeConsumer.SECONDARY_EXIT_ORDERS_PRICE_PERCENT, commons_enums.UserInputTypes.FLOAT,
                float(default_config[DCATradingModeConsumer.SECONDARY_EXIT_ORDERS_PRICE_PERCENT]
                      * trading_constants.ONE_HUNDRED), inputs,
                title="Secondary exit orders price interval percent: Price difference in percent to compute the "
                      "price of secondary exit orders compared to the price of the associated entry order. "
                      "Example: 10 on a 2000 USDT exit sell price would create secondary exit sell orders "
                      "at 2200 USDT, 2400 USDT and so on.",
                editor_options={
                    commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                        DCATradingModeConsumer.USE_SECONDARY_EXIT_ORDERS: True
                    }
                }
            )
        )) / trading_constants.ONE_HUNDRED
        self.use_stop_loss = self.UI.user_input(
            DCATradingModeConsumer.USE_STOP_LOSSES, commons_enums.UserInputTypes.BOOLEAN,
            default_config[DCATradingModeConsumer.USE_STOP_LOSSES], inputs,
            title="Enable stop losses: Create stop losses when entries are filled.",
        )
        self.stop_loss_price_multiplier = decimal.Decimal(str(
            self.UI.user_input(
                DCATradingModeConsumer.STOP_LOSS_PRICE_PERCENT, commons_enums.UserInputTypes.FLOAT,
                float(default_config[DCATradingModeConsumer.STOP_LOSS_PRICE_PERCENT] * trading_constants.ONE_HUNDRED),
                inputs, min_val=0, max_val=100,
                title="Stop loss price percent: maximum percent losses to compute the stop loss price from. "
                      "Example: a buy entry filled at 2000 with a Stop loss percent at"
                      " 15 will create a stop order at 1700.",
                editor_options={
                    commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                        DCATradingModeConsumer.USE_STOP_LOSSES: True
                    }
                }
            )
        )) / trading_constants.ONE_HUNDRED

        self.cancel_open_orders_at_each_entry = self.UI.user_input(
            DCATradingModeProducer.CANCEL_OPEN_ORDERS_AT_EACH_ENTRY, commons_enums.UserInputTypes.BOOLEAN,
            default_config[DCATradingModeProducer.CANCEL_OPEN_ORDERS_AT_EACH_ENTRY], inputs,
            title="Cancel open orders on each entry: Cancel existing orders from previous iteration on each entry.",
        )

        self.is_health_check_enabled = self.UI.user_input(
            self.ENABLE_HEALTH_CHECK, commons_enums.UserInputTypes.BOOLEAN,
            default_config[self.ENABLE_HEALTH_CHECK], inputs,
            title="Health check: when enabled, OctoBot will automatically sell traded assets that are not associated "
                  "to a sell order and that represent at least the 'Health check threshold' part of the "
                  "portfolio. Health check can be useful to avoid inactive funds, for example if a buy order got "
                  "filled but no sell order was created. Requires a common quote market for each traded pair. "
                  "Warning: will sell any asset associated to a trading pair that is not covered by a sell order, "
                  "even if not bought by OctoBot or this trading mode.",
        )
        self.health_check_orphan_funds_threshold = decimal.Decimal(str(
            self.UI.user_input(
                DCATradingModeProducer.HEALTH_CHECK_ORPHAN_FUNDS_THRESHOLD, commons_enums.UserInputTypes.FLOAT,
                float(default_config[DCATradingModeProducer.HEALTH_CHECK_ORPHAN_FUNDS_THRESHOLD]
                      * trading_constants.ONE_HUNDRED), inputs,
                title="Health check threshold: Minimum % of the portfolio taken by a traded asset that is not in "
                      "sell orders. Assets above this threshold will be sold for the common quote market during "
                      "Health check.",
                editor_options={
                    commons_enums.UserInputOtherSchemaValuesTypes.DEPENDENCIES.value: {
                        self.ENABLE_HEALTH_CHECK: True
                    }
                }
            )
        )) / trading_constants.ONE_HUNDRED
        self.max_asset_holding_ratio = decimal.Decimal(str(
            self.UI.user_input(
                DCATradingModeProducer.MAX_ASSET_HOLDING_PERCENT, commons_enums.UserInputTypes.FLOAT,
                float(default_config[DCATradingModeProducer.MAX_ASSET_HOLDING_PERCENT]
                      * trading_constants.ONE_HUNDRED), inputs,
                title="Max asset holding: Maximum % of the portfolio to allocate to an asset. "
                      "Buy orders to buy this asset won't be created if this ratio is reached. "
                      "Only applied when trading on spot.",
                min_val=0, max_val=100
            )
        )) / trading_constants.ONE_HUNDRED

    @classmethod
    def get_default_config(
        cls,
        buy_amount: typing.Optional[str] = None,
        sell_amount: typing.Optional[str] = None,
        use_secondary_entry_orders: typing.Optional[bool] = None,
        secondary_entry_orders_count: typing.Optional[int] = None,
        exit_limit_orders_price_percent: typing.Optional[float] = None,
        entry_limit_orders_price_percent: typing.Optional[float] = None,
        secondary_entry_orders_price_percent: typing.Optional[float] = None,
        secondary_entry_orders_amount: typing.Optional[str] = None,
        enable_stop_loss: typing.Optional[bool] = None,
        stop_loss_price: typing.Optional[float] = None,
        use_init_entry_orders: typing.Optional[bool] = None,
        use_take_profit_exit_orders: typing.Optional[bool] = None,
        trigger_mode:typing. Optional[TriggerMode] = None,
        secondary_exit_orders_price_percent: typing.Optional[float] = None,
        health_check_orphan_funds_threshold: typing.Optional[float] = None,
        max_asset_holding_percent : typing.Optional[float] = None,
    ) -> dict:
        return {
            trading_constants.CONFIG_BUY_ORDER_AMOUNT: buy_amount,
            trading_constants.CONFIG_SELL_ORDER_AMOUNT: sell_amount,
            DCATradingModeProducer.TRIGGER_MODE: trigger_mode.value if trigger_mode else TriggerMode.TIME_BASED.value,
            DCATradingModeProducer.MINUTES_BEFORE_NEXT_BUY: 10080,
            DCATradingModeConsumer.USE_INIT_ENTRY_ORDERS: use_init_entry_orders or False,
            DCATradingModeConsumer.USE_MARKET_ENTRY_ORDERS: False,
            DCATradingModeConsumer.ENTRY_LIMIT_ORDERS_PRICE_PERCENT:
                entry_limit_orders_price_percent or DCATradingModeConsumer.DEFAULT_ENTRY_LIMIT_PRICE_MULTIPLIER,
            DCATradingModeConsumer.USE_SECONDARY_ENTRY_ORDERS: use_secondary_entry_orders or False,
            DCATradingModeConsumer.SECONDARY_ENTRY_ORDERS_COUNT:
                secondary_entry_orders_count or DCATradingModeConsumer.DEFAULT_SECONDARY_ENTRY_ORDERS_COUNT,
            DCATradingModeConsumer.SECONDARY_ENTRY_ORDERS_PRICE_PERCENT:
                secondary_entry_orders_price_percent or DCATradingModeConsumer.DEFAULT_ENTRY_LIMIT_PRICE_MULTIPLIER,
            DCATradingModeConsumer.SECONDARY_ENTRY_ORDERS_AMOUNT: secondary_entry_orders_amount or "",
            DCATradingModeConsumer.USE_TAKE_PROFIT_EXIT_ORDERS: use_take_profit_exit_orders or False,
            DCATradingModeConsumer.EXIT_LIMIT_ORDERS_PRICE_PERCENT:
                exit_limit_orders_price_percent or DCATradingModeConsumer.DEFAULT_EXIT_LIMIT_PRICE_MULTIPLIER,
            DCATradingModeConsumer.USE_SECONDARY_EXIT_ORDERS: False,
            DCATradingModeConsumer.SECONDARY_EXIT_ORDERS_COUNT:
                DCATradingModeConsumer.DEFAULT_SECONDARY_EXIT_ORDERS_COUNT,
            DCATradingModeConsumer.SECONDARY_EXIT_ORDERS_PRICE_PERCENT:
                secondary_exit_orders_price_percent or DCATradingModeConsumer.DEFAULT_ENTRY_LIMIT_PRICE_MULTIPLIER,
            DCATradingModeConsumer.USE_STOP_LOSSES: enable_stop_loss or False,
            DCATradingModeConsumer.STOP_LOSS_PRICE_PERCENT:
                stop_loss_price or DCATradingModeConsumer.DEFAULT_STOP_LOSS_ORDERS_PRICE_MULTIPLIER,
            DCATradingModeProducer.CANCEL_OPEN_ORDERS_AT_EACH_ENTRY: True,
            cls.ENABLE_HEALTH_CHECK: False,
            DCATradingModeProducer.HEALTH_CHECK_ORPHAN_FUNDS_THRESHOLD:
                health_check_orphan_funds_threshold or cls.DEFAULT_HEALTH_CHECK_SELL_ORPHAN_FUNDS_RATIO_THRESHOLD,
            DCATradingModeProducer.MAX_ASSET_HOLDING_PERCENT: max_asset_holding_percent or decimal.Decimal(1),
        }

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return False

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
            trading_enums.ExchangeTypes.FUTURE,
        ]

    def get_current_state(self) -> (str, float):
        return (
            super().get_current_state()[0] if self.producers[0].state is None else self.producers[0].state.name,
            ",".join([str(e) for e in self.producers[0].final_eval]) if self.producers[0].final_eval
            else self.producers[0].final_eval
        )

    async def single_exchange_process_optimize_initial_portfolio(
        self, sellable_assets, target_asset: str, tickers: dict
    ) -> list:
        traded_coins = [
            symbol.base
            for symbol in self.exchange_manager.exchange_config.traded_symbols
        ]
        sellable_assets = sorted(list(set(sellable_assets + traded_coins)))
        self.logger.info(f"Optimizing portfolio: selling {sellable_assets} to buy {target_asset}")
        return await trading_modes.convert_assets_to_target_asset(
            self, sellable_assets, target_asset, tickers
        )

    async def single_exchange_process_health_check(self, chained_orders: list, tickers: dict) -> list:
        common_quote = trading_exchanges.get_common_traded_quote(self.exchange_manager)
        if (
            common_quote is None
            or not (self.use_take_profit_exit_orders or self.use_stop_loss)
        ):
            # skipped when:
            # - common_quote is unset
            # - not using take profit or stop losses, health check should not be used
            return []
        created_orders = []
        for asset, amount in self._get_lost_funds_to_sell(common_quote, chained_orders):
            # sell lost funds
            self.logger.info(
                f"Health check: selling {amount} {asset} into {common_quote} on {self.exchange_manager.exchange_name}"
            )
            try:
                asset_orders = await trading_modes.convert_asset_to_target_asset(
                    self, asset, common_quote, tickers, asset_amount=amount
                )
                if not asset_orders:
                    self.logger.info(
                        f"Health check: Not enough funds to create an order according to exchanges rules using "
                        f"{amount} {asset} into {common_quote} on {self.exchange_manager.exchange_name}"
                    )
                else:
                    created_orders.extend(asset_orders)
            except Exception as err:
                self.logger.exception(
                    err, True, f"Error when creating order to sell {asset} into {common_quote}: {err}"
                )
        if created_orders:
            await asyncio.gather(
                *[
                    trading_personal_data.wait_for_order_fill(
                        order, self.HEALTH_CHECK_FILL_ORDERS_TIMEOUT, True
                    ) for order in created_orders
                ]
            )
            for producer in self.producers:
                producer.last_activity = trading_modes.TradingModeActivity(
                    trading_enums.TradingModeActivityType.CREATED_ORDERS
                )
        return created_orders

    def _get_lost_funds_to_sell(self, common_quote: str, chained_orders: list) -> list[(str, decimal.Decimal)]:
        asset_and_amount = []
        value_holder = self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder
        traded_base_assets = set(
            symbol.base
            for symbol in self.exchange_manager.exchange_config.traded_symbols
        )
        sell_orders = [
            order
            for order in self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders() + chained_orders
            if order.side is trading_enums.TradeOrderSide.SELL
        ]
        partially_filled_buy_orders = [
            order
            for order in self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
            if order.side is trading_enums.TradeOrderSide.BUY and order.is_partially_filled()
        ]
        orphan_asset_values_by_asset = {}
        total_traded_assets_value = value_holder.value_converter.evaluate_value(
            common_quote,
            self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio(
                common_quote
            ).total,
            target_currency=common_quote,
            init_price_fetchers=False
        )
        for asset in traded_base_assets:
            asset_holding = \
                self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio(
                    asset
                )
            holdings_value = value_holder.value_converter.evaluate_value(
                asset, asset_holding.total, target_currency=common_quote, init_price_fetchers=False
            )
            total_traded_assets_value += holdings_value
            holdings_in_sell_orders = sum(
                order.origin_quantity
                for order in sell_orders
                if symbol_util.parse_symbol(order.symbol).base == asset
            )
            holdings_from_partially_filled_buy_orders = sum(
                order.filled_quantity
                for order in partially_filled_buy_orders
                if symbol_util.parse_symbol(order.symbol).base == asset
            )
            # do not consider more than the available amounts
            orphan_amount = min(
                asset_holding.total - holdings_in_sell_orders - holdings_from_partially_filled_buy_orders, 
                asset_holding.available
            )
            if orphan_amount and orphan_amount > 0:
                orphan_asset_values_by_asset[asset] = (
                    holdings_value * orphan_amount / asset_holding.total, orphan_amount
                )

        for asset, value_and_orphan_amount in orphan_asset_values_by_asset.items():
            value, orphan_amount = value_and_orphan_amount
            ratio = value / total_traded_assets_value
            if ratio > self.health_check_orphan_funds_threshold:
                asset_and_amount.append((asset, orphan_amount))
        return asset_and_amount
