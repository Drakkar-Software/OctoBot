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

import async_channel.constants as channel_constants
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.evaluators_util as evaluators_util
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_evaluators.api as evaluators_api
import octobot_evaluators.matrix as matrix
import octobot_evaluators.enums as evaluators_enums
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.modes as trading_modes
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.modes.script_keywords as script_keywords
import tentacles.Evaluator.Strategies as Strategies


class DipAnalyserTradingMode(trading_modes.AbstractTradingMode):

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.sell_orders_per_buy = 3

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """

        trading_modes.user_select_order_amount(self, inputs, include_sell=False)

        self.sell_orders_per_buy = self.UI.user_input(
            "sell_orders_count", commons_enums.UserInputTypes.INT, 3, inputs, min_val=1,
            title="Number of sell orders to create after each buy."
        )
        self.UI.user_input(
            DipAnalyserTradingModeProducer.IGNORE_EXCHANGE_FEES, commons_enums.UserInputTypes.BOOLEAN, False, inputs,
            title="Ignore exchange fees when creating sell orders. When enabled, 100% of the bought assets will be "
                  "sold, otherwise a small part will be kept to cover exchange fees."
        )
        self.UI.user_input(
            DipAnalyserTradingModeConsumer.USE_BUY_MARKET_ORDERS, commons_enums.UserInputTypes.BOOLEAN, False, inputs,
            title="Use market orders instead of limit orders upon buy signals. Using a market order makes will "
                  "guaranty that each buy signal will create an entry. "
                  "Limit orders (which are priced at 99.5% of the current price) "
                  "can delay an entry for some time to replace an open buy order with a more suitable "
                  "one when the market is very volatile. "
                  "However limit orders might also never be filled and ending up missing a buy opportunity."
        )
        self.UI.user_input(
            DipAnalyserTradingModeConsumer.STOP_LOSS_MULTIPLIER, commons_enums.UserInputTypes.FLOAT, 0, inputs,
            min_val=0, max_val=1,
            title="Stop loss price multiplier: ratio to compute the stop loss price. "
                  "Example: a 0.7 multiplier on a 2000 USDT buy would create a "
                  "stop price at 2000*0.7 = 1400 USDT. Leave at 0 to disable stop losses."
        )
        self.UI.user_input(
            DipAnalyserTradingModeConsumer.LIGHT_VOLUME_WEIGHT, commons_enums.UserInputTypes.FLOAT, 0.4, inputs,
            min_val=0, max_val=1,
            title="Volume multiplier for a buy order on a light volume weight signal.",
        )
        self.UI.user_input(
            DipAnalyserTradingModeConsumer.MEDIUM_VOLUME_WEIGHT, commons_enums.UserInputTypes.FLOAT, 0.7, inputs,
            min_val=0, max_val=1,
            title="Volume multiplier for a buy order on a medium volume weight signal.",
        )
        self.UI.user_input(
            DipAnalyserTradingModeConsumer.HEAVY_VOLUME_WEIGHT, commons_enums.UserInputTypes.FLOAT, 1, inputs,
            min_val=0, max_val=1,
            title="Volume multiplier for a buy order on a heavy volume weight signal.",
        )
        self.UI.user_input(
            DipAnalyserTradingModeConsumer.LIGHT_PRICE_WEIGHT, commons_enums.UserInputTypes.FLOAT, 1.04, inputs,
            min_val=1,
            title="Price multiplier for the top sell order in a light price weight signal.",
        )
        self.UI.user_input(
            DipAnalyserTradingModeConsumer.MEDIUM_PRICE_WEIGHT, commons_enums.UserInputTypes.FLOAT, 1.07, inputs,
            min_val=1,
            title="Price multiplier for the top sell order in a medium price weight signal.",
        )
        self.UI.user_input(
            DipAnalyserTradingModeConsumer.HEAVY_PRICE_WEIGHT, commons_enums.UserInputTypes.FLOAT, 1.1, inputs,
            min_val=1,
            title="Price multiplier for the top sell order in a heavy price weight signal.",
        )

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
        return super().get_current_state()[0] if self.producers[0].state is None else self.producers[0].state.name, \
               "N/A"

    def get_mode_producer_classes(self) -> list:
        return [DipAnalyserTradingModeProducer]

    def get_mode_consumer_classes(self) -> list:
        return [DipAnalyserTradingModeConsumer]

    async def create_consumers(self) -> list:
        consumers = await super().create_consumers()

        # order consumer: filter by symbol not be triggered only on this symbol's orders
        order_consumer = await exchanges_channel.get_chan(trading_personal_data.OrdersChannel.get_name(),
                                                          self.exchange_manager.id).new_consumer(
            self._order_notification_callback,
            symbol=self.symbol if self.symbol else channel_constants.CHANNEL_WILDCARD
        )
        return consumers + [order_consumer]

    async def _order_notification_callback(self, exchange, exchange_id, cryptocurrency,
                                           symbol, order, update_type, is_from_bot):
        if order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] \
                == trading_enums.OrderStatus.FILLED.value and is_from_bot:
            await self.producers[0].order_filled_callback(order)

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return False


class DipAnalyserTradingModeConsumer(trading_modes.AbstractTradingModeConsumer):
    USE_BUY_MARKET_ORDERS = "use_buy_market_orders"
    STOP_LOSS_MULTIPLIER = "stop_loss_multiplier"
    STOP_LOSS_PRICE_MULTIPLIER = decimal.Decimal(0)
    USE_BUY_MARKET_ORDERS_VALUE = False
    LIMIT_PRICE_MULTIPLIER = decimal.Decimal("0.995")
    SOFT_MAX_CURRENCY_RATIO = decimal.Decimal("0.33")
    # consider a high ratio not to take too much risk and not to prevent order creation either
    DEFAULT_HOLDING_RATIO = decimal.Decimal("0.35")
    DEFAULT_FULL_VOLUME = decimal.Decimal("0.5")
    DEFAULT_SELL_TARGET = decimal.Decimal("1")

    RISK_VOLUME_MULTIPLIER = decimal.Decimal("0.2")

    DELTA_RATIO = decimal.Decimal("0.8")

    ORDER_ID_KEY = "order_id"
    VOLUME_KEY = "volume"
    BUY_PRICE_KEY = "buy_price"
    VOLUME_WEIGHT_KEY = "volume_weight"
    PRICE_WEIGHT_KEY = "price_weight"

    LIGHT_VOLUME_WEIGHT = "light_weight_volume_multiplier"
    MEDIUM_VOLUME_WEIGHT = "medium_weight_volume_multiplier"
    HEAVY_VOLUME_WEIGHT = "heavy_weight_volume_multiplier"
    VOLUME_WEIGH_TO_VOLUME_PERCENT = {}

    LIGHT_PRICE_WEIGHT = "light_weight_price_multiplier"
    MEDIUM_PRICE_WEIGHT = "medium_weight_price_multiplier"
    HEAVY_PRICE_WEIGHT = "heavy_weight_price_multiplier"
    PRICE_WEIGH_TO_PRICE_PERCENT = {}

    def __init__(self, trading_mode):
        super().__init__(trading_mode)
        self.sell_targets_by_order_id = {}

    def on_reload_config(self):
        """
        Called at constructor and after the associated trading mode's reload_config.
        Implement if necessary
        """
        self.STOP_LOSS_PRICE_MULTIPLIER = \
            decimal.Decimal(f"{self.trading_mode.trading_config.get(self.STOP_LOSS_MULTIPLIER, 0)}")
        self.USE_BUY_MARKET_ORDERS_VALUE = self.trading_mode.trading_config.get(self.USE_BUY_MARKET_ORDERS, False)
        self.PRICE_WEIGH_TO_PRICE_PERCENT = {}
        self.PRICE_WEIGH_TO_PRICE_PERCENT[1] = \
            decimal.Decimal(f"{self.trading_mode.trading_config[self.LIGHT_PRICE_WEIGHT]}")
        self.PRICE_WEIGH_TO_PRICE_PERCENT[2] = \
            decimal.Decimal(f"{self.trading_mode.trading_config[self.MEDIUM_PRICE_WEIGHT]}")
        self.PRICE_WEIGH_TO_PRICE_PERCENT[3] = \
            decimal.Decimal(f"{self.trading_mode.trading_config[self.HEAVY_PRICE_WEIGHT]}")

        self.VOLUME_WEIGH_TO_VOLUME_PERCENT[1] = \
            decimal.Decimal(f"{self.trading_mode.trading_config[self.LIGHT_VOLUME_WEIGHT]}")
        self.VOLUME_WEIGH_TO_VOLUME_PERCENT[2] = \
            decimal.Decimal(f"{self.trading_mode.trading_config[self.MEDIUM_VOLUME_WEIGHT]}")
        self.VOLUME_WEIGH_TO_VOLUME_PERCENT[3] = \
            decimal.Decimal(f"{self.trading_mode.trading_config[self.HEAVY_VOLUME_WEIGHT]}")

    async def create_new_orders(self, symbol, final_note, state, **kwargs):
        timeout = kwargs.get("timeout", trading_constants.ORDER_DATA_FETCHING_TIMEOUT)
        data = kwargs.get("data", {})
        if state == trading_enums.EvaluatorStates.LONG.value:
            volume_weight = data.get(self.VOLUME_WEIGHT_KEY, 1)
            price_weight = data.get(self.PRICE_WEIGHT_KEY, 1)
            return await self.create_buy_order(symbol, timeout, volume_weight, price_weight)
        elif state == trading_enums.EvaluatorStates.SHORT.value:
            quantity = data.get(self.VOLUME_KEY, decimal.Decimal("1"))
            buy_order_id = data[self.ORDER_ID_KEY]
            sell_weight = self._get_sell_target_for_registered_order(buy_order_id)
            sell_base = data[self.BUY_PRICE_KEY]
            return await self.create_sell_orders(symbol, timeout, self.trading_mode.sell_orders_per_buy,
                                                 quantity, sell_weight, sell_base, buy_order_id)
        self.logger.error(f"Unknown required order action: data= {data}")

    async def create_buy_order(self, symbol, timeout, volume_weight, price_weight):
        current_order = None
        try:
            current_symbol_holding, current_market_holding, market_quantity, price, symbol_market = \
                await trading_personal_data.get_pre_order_data(self.exchange_manager, symbol=symbol, timeout=timeout)
            max_buy_size = market_quantity
            if self.exchange_manager.is_future:
                max_buy_size, is_increasing_position = trading_personal_data.get_futures_max_order_size(
                    self.exchange_manager, symbol, trading_enums.TradeOrderSide.BUY,
                    price, False, current_symbol_holding, market_quantity
                )

            base = symbol_util.parse_symbol(symbol).base
            created_orders = []
            orders_should_have_been_created = False
            ctx = script_keywords.get_base_context(self.trading_mode, symbol)
            order_type = trading_enums.TraderOrderType.BUY_MARKET \
                if self.USE_BUY_MARKET_ORDERS_VALUE else trading_enums.TraderOrderType.BUY_LIMIT
            quantity = await self._get_buy_quantity_from_weight(ctx, volume_weight, max_buy_size, base)
            limit_price = trading_personal_data.decimal_adapt_price(
                symbol_market,
                price if self.USE_BUY_MARKET_ORDERS_VALUE else self.get_limit_price(price)
            )
            quantity = trading_personal_data.decimal_adapt_order_quantity_because_fees(
                self.exchange_manager, symbol, order_type, quantity, limit_price, trading_enums.TradeOrderSide.BUY
            )
            for order_quantity, order_price in trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                    quantity,
                    limit_price,
                    symbol_market):
                orders_should_have_been_created = True
                current_order = trading_personal_data.create_order_instance(
                    trader=self.exchange_manager.trader,
                    order_type=order_type,
                    symbol=symbol,
                    current_price=price,
                    quantity=order_quantity,
                    price=order_price,
                )
                if created_order := await self.trading_mode.create_order(current_order):
                    created_orders.append(created_order)
                    self._register_buy_order(created_order.order_id, price_weight)
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
        except Exception as e:
            self.logger.exception(
                e, True, f"Failed to create order : {e}. Order: {current_order if current_order else None}"
            )
            return []

    async def create_sell_orders(
        self, symbol, timeout, sell_orders_count, quantity, sell_weight, sell_base, buy_order_id
    ):
        current_order = None
        try:
            reduce_only = False
            if self.exchange_manager.is_future and await self.wait_for_active_position(symbol, timeout):
                # can use reduce only orders now that the position is active
                reduce_only = True
            current_symbol_holding, current_market_holding, market_quantity, price, symbol_market = \
                await trading_personal_data.get_pre_order_data(self.exchange_manager, symbol=symbol, timeout=timeout)
            max_sell_size = current_symbol_holding
            if self.exchange_manager.is_future:
                max_sell_size, is_increasing_position = trading_personal_data.get_futures_max_order_size(
                    self.exchange_manager, symbol, trading_enums.TradeOrderSide.SELL,
                    price, False, current_symbol_holding, market_quantity
                )
            created_orders = []
            orders_should_have_been_created = False
            sell_max_quantity = decimal.Decimal(min(decimal.Decimal(f"{max_sell_size}"), quantity))
            to_create_orders = self._generate_sell_orders(sell_orders_count, sell_max_quantity, sell_weight,
                                                          sell_base, symbol_market)
            for order_quantity, order_price in to_create_orders:
                orders_should_have_been_created = True
                current_limit_order = trading_personal_data.create_order_instance(
                    trader=self.exchange_manager.trader,
                    order_type=trading_enums.TraderOrderType.SELL_LIMIT,
                    symbol=symbol,
                    current_price=sell_base,
                    quantity=order_quantity,
                    price=order_price,
                    reduce_only=reduce_only,
                    associated_entry_id=buy_order_id,
                )
                created_sell_order, created_stop_order = await self._create_exit_with_stop_loss_if_enabled(
                    current_limit_order, sell_base, symbol_market, buy_order_id
                )
                created_orders.append(created_sell_order)
                if created_stop_order:
                    created_orders.append(created_stop_order)
            if created_orders:
                return created_orders
            if orders_should_have_been_created:
                raise trading_errors.OrderCreationError()
            raise trading_errors.MissingMinimalExchangeTradeVolume()

        except (trading_errors.MissingFunds,
                trading_errors.MissingMinimalExchangeTradeVolume,
                trading_errors.OrderCreationError):
            raise
        except Exception as e:
            self.logger.exception(
                e, True, f"Failed to create order : {e} ({e.__class__.__name__}). Order: "
                f"{current_order if current_order else None}"
            )
            return []

    async def _create_exit_with_stop_loss_if_enabled(self, sell_order_to_create, sell_base, symbol_market, buy_order_id):
        current_stop_order = None
        if self.STOP_LOSS_PRICE_MULTIPLIER and sell_order_to_create:
            stop_price = sell_base * self.STOP_LOSS_PRICE_MULTIPLIER
            oco_group = self.exchange_manager.exchange_personal_data.orders_manager.create_group(
                trading_personal_data.OneCancelsTheOtherOrderGroup,
                active_order_swap_strategy=trading_personal_data.StopFirstActiveOrderSwapStrategy()
            )
            sell_order_to_create.add_to_order_group(oco_group)
            current_stop_order = trading_personal_data.create_order_instance(
                trader=self.exchange_manager.trader,
                order_type=trading_enums.TraderOrderType.STOP_LOSS,
                symbol=sell_order_to_create.symbol,
                current_price=trading_personal_data.adapt_price(symbol_market, stop_price),
                quantity=sell_order_to_create.origin_quantity,
                price=stop_price,
                side=trading_enums.TradeOrderSide.SELL,
                reduce_only=True,
                group=oco_group,
                associated_entry_id=buy_order_id,
            )
            # in futures, inactive orders are not necessary
            if self.exchange_manager.trader.enable_inactive_orders and not self.exchange_manager.is_future:
                await oco_group.active_order_swap_strategy.apply_inactive_orders([sell_order_to_create, current_stop_order])
        created_sell_order = await self.trading_mode.create_order(sell_order_to_create)
        created_stop_order = None
        if created_sell_order and created_sell_order.is_open() and current_stop_order:
            created_stop_order = await self.trading_mode.create_order(current_stop_order)
            self.logger.debug(f"Grouping orders: {sell_order_to_create} and {created_stop_order}")
        return created_sell_order, created_stop_order

    def _register_buy_order(self, order_id, price_weight):
        self.sell_targets_by_order_id[order_id] = price_weight

    def unregister_buy_order(self, order_id):
        self.sell_targets_by_order_id.pop(order_id, None)

    async def _get_buy_quantity_from_weight(self, ctx, volume_weight, market_quantity, currency):
        weighted_volume = self.VOLUME_WEIGH_TO_VOLUME_PERCENT[volume_weight]
        # high risk is making larger orders, low risk is making smaller ones
        risk_multiplier = 1 + ((self.exchange_manager.trader.risk - decimal.Decimal("0.5")) * self.RISK_VOLUME_MULTIPLIER)
        weighted_volume = min(weighted_volume * risk_multiplier, trading_constants.ONE)
        # check configured quantity
        if user_amount := trading_modes.get_user_selected_order_amount(self.trading_mode,
                                                                       trading_enums.TradeOrderSide.BUY):
            return await script_keywords.get_amount_from_input_amount(
                context=ctx,
                input_amount=user_amount,
                side=trading_enums.TradeOrderSide.BUY.value,
                reduce_only=False,
                is_stop_order=False,
                use_total_holding=False,
            ) * weighted_volume
        traded_assets_count = self.get_number_of_traded_assets()
        if traded_assets_count == 1:
            return market_quantity * self.DEFAULT_FULL_VOLUME * weighted_volume
        elif traded_assets_count == 2:
            return market_quantity * self.SOFT_MAX_CURRENCY_RATIO * weighted_volume
        else:
            currency_ratio = trading_constants.ZERO
            if currency != self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market:
                # if currency (base) is not ref market => need to check holdings ratio not to spend all ref market
                # into one currency (at least 3 traded assets are available here)
                try:
                    currency_ratio = self.exchange_manager.exchange_personal_data.portfolio_manager. \
                        portfolio_value_holder.get_holdings_ratio(currency)
                except trading_errors.MissingPriceDataError:
                    # Can happen when ref market is not in the pair, data will be available later (ticker is now
                    # registered)
                    currency_ratio = self.DEFAULT_HOLDING_RATIO
            # linear function of % holding in this currency: volume_ratio is in [0, SOFT_MAX_CURRENCY_RATIO*0.8]
            volume_ratio = self.SOFT_MAX_CURRENCY_RATIO * \
                (1 - min(currency_ratio * self.DELTA_RATIO, trading_constants.ONE))
            return market_quantity * volume_ratio * weighted_volume

    def _get_sell_target_for_registered_order(self, order_id):
        try:
            return self.sell_targets_by_order_id[order_id]
        except KeyError:
            if not self.sell_targets_by_order_id:
                self.logger.warning(f"No registered buy orders, therefore no sell target for order with id "
                                    f"{order_id}. Using default sell target: {self.DEFAULT_SELL_TARGET}.")
            else:
                self.logger.warning(f"No sell target for order with id {order_id}. "
                                    f"Using default sell target: {self.DEFAULT_SELL_TARGET}.")
            return self.DEFAULT_SELL_TARGET

    def get_limit_price(self, price):
        # buy very close from current price
        return price * self.LIMIT_PRICE_MULTIPLIER

    def _generate_sell_orders(self, sell_orders_count, quantity, sell_weight, sell_base, symbol_market):
        volume_with_price = []
        sell_max = sell_base * self.PRICE_WEIGH_TO_PRICE_PERCENT[sell_weight]
        adapted_sell_orders_count, increment = trading_personal_data.get_split_orders_count_and_increment(
            sell_base, sell_max, quantity, sell_orders_count, symbol_market, True
        )
        if adapted_sell_orders_count:
            order_volume = quantity / adapted_sell_orders_count
            total_volume = 0
            for i in range(adapted_sell_orders_count):
                order_price = sell_base + (increment * (i + 1))
                for adapted_quantity, adapted_price \
                        in trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                        order_volume,
                        order_price,
                        symbol_market):
                    total_volume += adapted_quantity
                    volume_with_price.append((adapted_quantity, adapted_price))
            if not volume_with_price:
                volume_with_price.append((quantity, trading_personal_data.decimal_adapt_price(symbol_market,
                                                                                              sell_base + increment)))
                total_volume += quantity
            if total_volume < quantity:
                # ensure the whole target quantity is used
                full_quantity = volume_with_price[-1][0] + quantity - total_volume
                volume_with_price[-1] = (full_quantity, volume_with_price[-1][1])
        return volume_with_price


class DipAnalyserTradingModeProducer(trading_modes.AbstractTradingModeProducer):
    IGNORE_EXCHANGE_FEES = "ignore_exchange_fees"

    def __init__(self, channel, config, trading_mode, exchange_manager):
        self.ignore_exchange_fees = False
        super().__init__(channel, config, trading_mode, exchange_manager)

        self.state = trading_enums.EvaluatorStates.NEUTRAL
        self.first_trigger = True

        self.last_buy_candle = None
        self.base = symbol_util.parse_symbol(self.trading_mode.symbol).base

    def on_reload_config(self):
        """
        Called at constructor and after the associated trading mode's reload_config.
        Implement if necessary
        """
        self.ignore_exchange_fees = self.trading_mode.trading_config.get(self.IGNORE_EXCHANGE_FEES, False)

    async def stop(self):
        if self.trading_mode is not None:
            self.trading_mode.flush_trading_mode_consumers()
        await super().stop()

    async def set_final_eval(self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame, trigger_source: str):
        # Strategies analysis
        for evaluated_strategy_node in matrix.get_tentacles_value_nodes(
                matrix_id,
                matrix.get_tentacle_nodes(matrix_id,
                                          exchange_name=self.exchange_name,
                                          tentacle_type=evaluators_enums.EvaluatorMatrixTypes.STRATEGIES.value,
                                          tentacle_name=Strategies.DipAnalyserStrategyEvaluator.get_name()),
                symbol=symbol):
            if evaluators_util.check_valid_eval_note(evaluators_api.get_value(evaluated_strategy_node),
                                                     evaluators_api.get_type(evaluated_strategy_node),
                                                     Strategies.DipAnalyserStrategyEvaluator.get_eval_type()):
                self.final_eval = evaluators_api.get_value(evaluated_strategy_node)
                await self.create_state()

    async def create_state(self):
        self.state = trading_enums.EvaluatorStates.LONG
        if self.first_trigger:
            # can't rely on previous execution buy orders: need plans for sell orders
            await self._cancel_buy_orders()
            self.first_trigger = False
        if self.final_eval != commons_constants.START_PENDING_EVAL_NOTE:
            volume_weight = self.final_eval["volume_weight"]
            price_weight = self.final_eval["price_weight"]
            await self._create_bottom_order(self.final_eval["current_candle_time"], volume_weight, price_weight)

    async def order_filled_callback(self, filled_order):
        if filled_order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] \
                == trading_enums.TradeOrderSide.BUY.value:
            self.state = trading_enums.EvaluatorStates.SHORT
            paid_fees = 0 if self.ignore_exchange_fees else \
                decimal.Decimal(f"{trading_personal_data.total_fees_from_order_dict(filled_order, self.base)}")
            sell_quantity = \
                decimal.Decimal(f"{filled_order[trading_enums.ExchangeConstantsOrderColumns.FILLED.value]}") - paid_fees
            price = decimal.Decimal(f"{filled_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]}")
            await self._create_sell_order_if_enabled(
                filled_order[trading_enums.ExchangeConstantsOrderColumns.ID.value],
                sell_quantity,
                price
            )

    @trading_modes.enabled_trader_only()
    async def _create_sell_order_if_enabled(self, order_id, sell_quantity, buy_price):
        data = {
            DipAnalyserTradingModeConsumer.ORDER_ID_KEY: order_id,
            DipAnalyserTradingModeConsumer.VOLUME_KEY: sell_quantity,
            DipAnalyserTradingModeConsumer.BUY_PRICE_KEY: buy_price,
        }
        await self.submit_trading_evaluation(
            cryptocurrency=self.trading_mode.cryptocurrency,
            symbol=self.trading_mode.symbol,
            time_frame=None,
            state=trading_enums.EvaluatorStates.SHORT,
            data=data
        )

    async def _create_bottom_order(self, notification_candle_time, volume_weight, price_weight):
        self.logger.info(f"** New buy signal for ** : {self.trading_mode.symbol}")
        # call orders creation method
        await self._create_buy_order_if_enabled(notification_candle_time, volume_weight, price_weight)

    @trading_modes.enabled_trader_only()
    async def _create_buy_order_if_enabled(self, notification_candle_time, volume_weight, price_weight):
        # cancel previous by orders if any
        cancelled_orders = await self._cancel_buy_orders()
        if self.last_buy_candle == notification_candle_time and cancelled_orders or \
            self.last_buy_candle != notification_candle_time:
            # if subsequent notification from the same candle: only create order if able to cancel the previous buy
            # to avoid multiple order on the same candle
            data = {
                DipAnalyserTradingModeConsumer.VOLUME_WEIGHT_KEY: volume_weight,
                DipAnalyserTradingModeConsumer.PRICE_WEIGHT_KEY: price_weight,
            }
            await self.submit_trading_evaluation(cryptocurrency=self.trading_mode.cryptocurrency,
                                                    symbol=self.trading_mode.symbol,
                                                    time_frame=None,
                                                    state=trading_enums.EvaluatorStates.LONG,
                                                    data=data)
            self.last_buy_candle = notification_candle_time
        else:
            self.logger.debug(f"Trader ignored buy signal for {self.trading_mode.symbol}: "
                                f"buy order already filled.")

    @classmethod
    def get_should_cancel_loaded_orders(cls):
        return True

    def _get_current_buy_orders(self):
        return [order
                for order in self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(
                    self.trading_mode.symbol)
                if order.side == trading_enums.TradeOrderSide.BUY]

    @trading_modes.enabled_trader_only(disabled_return_value=False)
    async def _cancel_buy_orders(self):
        cancelled_orders = False
        for order in self._get_current_buy_orders():
            try:
                cancelled_orders = await self.trading_mode.cancel_order(order) or cancelled_orders
            except (trading_errors.OrderCancelError, trading_errors.UnexpectedExchangeSideOrderStateError) as err:
                self.logger.warning(f"Skipping order cancel: {err}")
                # order can't be cancelled: don't set cancelled_orders to True
        return cancelled_orders
