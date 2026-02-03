#  Drakkar-Software OctoBot-Tentacles
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

import octobot_commons.channels_name as channels_name
import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.authentication as authentication
import octobot_commons.tentacles_management as tentacles_management
import octobot_commons.signals as commons_signals
import async_channel.channels as channels
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.modes as trading_modes
import octobot_trading.errors as errors
import octobot_trading.exchanges as exchanges
import octobot_trading.signals as trading_signals
import octobot_trading.personal_data as personal_data
import octobot_trading.modes.script_keywords as script_keywords


class RemoteTradingSignalsTradingMode(trading_modes.AbstractTradingMode):

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.merged_symbol = None
        self.last_signal_description = ""

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        self.UI.user_input(
            common_constants.CONFIG_TRADING_SIGNALS_STRATEGY, common_enums.UserInputTypes.TEXT, "", inputs,
            title="Trading strategy: identifier of the trading strategy to use."
        )
        self.UI.user_input(
            RemoteTradingSignalsModeConsumer.MAX_VOLUME_PER_BUY_ORDER_CONFIG_KEY,
            common_enums.UserInputTypes.FLOAT, 100, inputs,
            min_val=0, max_val=100,
            title="Maximum volume per buy order in % of quote symbol holdings (USDT for BTC/USDT).",
        )
        self.UI.user_input(
            RemoteTradingSignalsModeConsumer.ROUND_TO_MINIMAL_SIZE_IF_NECESSARY_CONFIG_KEY,
            common_enums.UserInputTypes.BOOLEAN, True, inputs,
            title="Round to minimal size orders if missing funds according to signal. "
                  "Used when copy signals require a volume that doesn't meet the minimal exchange order size."
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
        producer_state = "" if self.producers[0].state in (None, trading_enums.EvaluatorStates.UNKNOWN) \
            else self.producers[0].state.name
        return producer_state, self.last_signal_description

    def get_mode_producer_classes(self) -> list:
        return [RemoteTradingSignalsModeProducer]

    def get_mode_consumer_classes(self) -> list:
        return [RemoteTradingSignalsModeConsumer]

    async def create_producers(self, auto_start) -> list:
        producers = await super().create_producers(auto_start)
        return producers + await self._subscribe_to_signal_feed()

    async def _subscribe_to_signal_feed(self):
        channel, created = await trading_signals.create_remote_trading_signal_channel_if_missing(
            self.exchange_manager
        )
        if self.exchange_manager.is_backtesting:
            # TODO: create and return producer simulator with this bot id
            raise NotImplementedError("signal producer simulator is not implemented")
            return []
        if created:
            # only subscribe once to the signal channel
            try:
                await channel.subscribe_to_product_feed(
                    self.trading_config[common_constants.CONFIG_TRADING_SIGNALS_STRATEGY]
                )
            except (authentication.AuthenticationRequired, authentication.AuthenticationError) as e:
                self.logger.exception(e, True, f"Error while subscribing to signal feed: {e}. Please sign in to "
                                               f"your OctoBot account to receive trading signals")
            except Exception as e:
                self.logger.exception(e, True, f"Error while subscribing to signal feed: {e}. This trading mode won't "
                                               f"be operating")
        return []

    async def create_consumers(self) -> list:
        consumers = await super().create_consumers()
        signals_consumer = await channels.get_chan(
            channels_name.OctoBotCommunityChannelsName.REMOTE_TRADING_SIGNALS_CHANNEL.value)\
            .new_consumer(
                self._remote_trading_signal_callback,
                identifier=self.trading_config[common_constants.CONFIG_TRADING_SIGNALS_STRATEGY],
                symbol=self.symbol,
                bot_id=self.bot_id
            )
        return consumers + [signals_consumer]

    async def _remote_trading_signal_callback(self, identifier, exchange, symbol, version, bot_id, signal):
        self.logger.info(f"received signal: {signal}")
        await self.producers[0].signal_callback(signal)
        self.logger.info("done")

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return False

    @staticmethod
    def is_backtestable():
        return False

    def is_following_trading_signals(self):
        return True

    async def stop(self) -> None:
        self.logger.debug("Stopping trading mode: this should normally not be happening unless OctoBot is stopping")
        await super().stop()


class RemoteTradingSignalsModeConsumer(trading_modes.AbstractTradingModeConsumer):
    MAX_VOLUME_PER_BUY_ORDER_CONFIG_KEY = "max_volume"
    ROUND_TO_MINIMAL_SIZE_IF_NECESSARY_CONFIG_KEY = "round_to_minimal_size_if_necessary"

    def __init__(self, trading_mode):
        super().__init__(trading_mode)
        self.MAX_VOLUME_PER_BUY_ORDER = \
            decimal.Decimal(f"{self.trading_mode.trading_config.get(self.MAX_VOLUME_PER_BUY_ORDER_CONFIG_KEY, 100)}")
        self.ROUND_TO_MINIMAL_SIZE_IF_NECESSARY = \
            self.trading_mode.trading_config.get(self.ROUND_TO_MINIMAL_SIZE_IF_NECESSARY_CONFIG_KEY)

    async def init_user_inputs(self, should_clear_inputs):
        self.MAX_VOLUME_PER_BUY_ORDER = \
            decimal.Decimal(f"{self.trading_mode.trading_config.get(self.MAX_VOLUME_PER_BUY_ORDER_CONFIG_KEY, 100)}")
        self.ROUND_TO_MINIMAL_SIZE_IF_NECESSARY = \
            self.trading_mode.trading_config.get(self.ROUND_TO_MINIMAL_SIZE_IF_NECESSARY_CONFIG_KEY)

    async def internal_callback(
        self, trading_mode_name, cryptocurrency, symbol, time_frame, final_note, state,
        data: commons_signals.Signal, dependencies=None
    ):
        """
        Override not to call self.create_order_if_possible to skip portfolio checks and handle signals directly
        """
        try:
            await self.handle_signal(symbol, data)
        except errors.MissingMinimalExchangeTradeVolume:
            self.logger.info(self.get_minimal_funds_error(symbol, final_note))
        except errors.TraderDisabledError as err:
            self.logger.error(f"Impossible to execution action on a disabled trader: {err}.")
        except Exception as e:
            self.logger.exception(e, True, f"Error when handling remote signal orders: {e}")

    async def handle_signal(self, symbol, data: commons_signals.Signal):
        if data.topic == trading_enums.TradingSignalTopics.ORDERS.value:
            # creates a new order (or multiple split orders), always check self.can_create_order() first.
            await self._handle_signal_orders(symbol, data)
        elif data.topic == trading_enums.TradingSignalTopics.POSITIONS.value:
            await self._handle_positions_signal(symbol, data)
        else:
            self.logger.error(f"Unhandled signal topic: {data.topic} (signal: {data})")

    async def _handle_positions_signal(self, symbol: str, signal: commons_signals.Signal):
        action = signal.content.get(trading_enums.TradingSignalCommonsAttrs.ACTION.value)
        if action == trading_enums.TradingSignalPositionsActions.EDIT.value:
            await self._edit_position(symbol, signal)
        else:
            self.logger.error(f"Unhandled signal action: {action} (signal: {signal})")

    async def _edit_position(self, symbol: str, signal: commons_signals.Signal):
        leverage = signal.content.get(trading_enums.TradingSignalPositionsAttrs.LEVERAGE.value)
        side = signal.content.get(trading_enums.TradingSignalPositionsAttrs.SIDE.value)
        if side:
            side = trading_enums.PositionSide(side)
        if leverage is not None:
            await self._set_leverage(symbol, decimal.Decimal(str(leverage)), side)

    async def _handle_signal_orders(self, symbol: str, signal: commons_signals.Signal):
        to_create_orders_descriptions, to_edit_orders_descriptions, \
            to_cancel_orders_descriptions, to_group_orders_descriptions = \
            self._parse_signal_orders(signal)
        self._update_orders_according_to_config(to_edit_orders_descriptions)
        self._update_orders_according_to_config(to_create_orders_descriptions)
        await self._group_orders(to_group_orders_descriptions, symbol)
        cancelled_count = await self._cancel_orders(to_cancel_orders_descriptions, symbol)
        edited_count = await self._edit_orders(to_edit_orders_descriptions, symbol)
        created_count = await self._create_orders(to_create_orders_descriptions, symbol)

        self.trading_mode.last_signal_description = \
            f"Last signal: {created_count} new order{'s' if created_count > 1 else ''}"
        # send_notification
        if not self.exchange_manager.is_backtesting:
            await self._send_alert_notification(symbol, created_count, edited_count, cancelled_count)

    async def _group_orders(self, orders_descriptions, symbol):
        groups = []
        orders_by_group_id = {}
        for order_description, order in self.get_open_order_from_description(orders_descriptions, symbol):
            order_group = self._get_or_create_order_group(
                order_description,
                order_description[trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value])
            if order_group not in groups:
                groups.append(order_group)
                orders_by_group_id[order_group.name] = []
            order.add_to_order_group(order_group)
            orders_by_group_id[order_group.name].append(order)

        for group in groups:
            # in futures, inactive orders are not necessary
            if self.exchange_manager.trader.enable_inactive_orders and not self.exchange_manager.is_future:
                await group.get_active_order_swap_strategy.apply_inactive_orders(orders_by_group_id[group.name])

    async def _cancel_orders(self, orders_descriptions, symbol):
        cancelled_count = 0
        for _, order in self.get_open_order_from_description(orders_descriptions, symbol):
            try:
                await self._cancel_order_on_exchange(order)
            except (errors.OrderCancelError, errors.UnexpectedExchangeSideOrderStateError) as err:
                self.logger.warning(f"Skipping order cancel: {err} ({err.__class__.__name__})")
            cancelled_count += 1
        return cancelled_count

    async def _edit_orders(self, orders_descriptions, symbol):
        edited_count = 0
        for order_description, order in self.get_open_order_from_description(orders_descriptions, symbol):
            edited_price = order_description[trading_enums.TradingSignalOrdersAttrs.UPDATED_LIMIT_PRICE.value]
            edited_stop_price = order_description[trading_enums.TradingSignalOrdersAttrs.UPDATED_STOP_PRICE.value]
            edited_quantity, _, _ = await self._get_quantity_from_signal_percent(
                order_description, order.side, symbol, order.reduce_only, True
            )
            await self._edit_order_on_exchange(
                order,
                edited_quantity=decimal.Decimal(edited_quantity) if edited_quantity else None,
                edited_price=decimal.Decimal(edited_price) if edited_price else None,
                edited_stop_price=decimal.Decimal(edited_stop_price) if edited_stop_price else None
            )
            edited_count += 1
        return edited_count

    async def _get_quantity_from_signal_percent(self, order_description, side, symbol, reduce_only, update_amount):
        quantity_type, quantity = script_keywords.parse_quantity(
            order_description[
                trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value
                if update_amount else trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value
            ]
        )
        portfolio_type = common_constants.PORTFOLIO_TOTAL if quantity_type is script_keywords.QuantityType.PERCENT \
            else common_constants.PORTFOLIO_AVAILABLE
        current_symbol_holding, current_market_holding, market_quantity, current_price, symbol_market = \
            await personal_data.get_pre_order_data(self.exchange_manager, symbol=symbol,
                                                   timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
                                                   portfolio_type=portfolio_type)
        if self.exchange_manager.is_future:
            max_order_size, _ = personal_data.get_futures_max_order_size(
                self.exchange_manager, symbol, side, current_price, reduce_only,
                current_symbol_holding, market_quantity
            )
            position_percent = order_description[
                trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_POSITION.value
                if update_amount else trading_enums.TradingSignalOrdersAttrs.TARGET_POSITION.value
            ]
            if position_percent is not None:
                quantity_type, quantity = script_keywords.parse_quantity(position_percent)
                if quantity_type in (
                    script_keywords.QuantityType.POSITION_PERCENT,
                    script_keywords.QuantityType.POSITION_PERCENT_ALIAS
                ):
                    open_position_size_val = \
                        self.exchange_manager.exchange_personal_data.positions_manager.get_symbol_position(
                            symbol,
                            trading_enums.PositionSide.BOTH
                        ).size
                    target_size = open_position_size_val * quantity / trading_constants.ONE_HUNDRED
                    order_size = abs(target_size - open_position_size_val)
                    return order_size, current_price, max_order_size
                raise errors.InvalidArgumentError(f"Unhandled position based quantity type: {position_percent}")
        else:
            max_order_size = market_quantity if side is trading_enums.TradeOrderSide.BUY else current_symbol_holding
        return max_order_size * quantity / trading_constants.ONE_HUNDRED, current_price, max_order_size

    async def _bundle_order(self, order_description, to_create_orders, ignored_orders, bundled_with, fees_currency_side,
                            created_groups, symbol):
        chained_order = await self._create_order(order_description, symbol, created_groups, fees_currency_side)
        try:
            main_order = to_create_orders[bundled_with][0]
            # always align bundled order quantity with the main order one
            chained_order.update(chained_order.symbol, quantity=main_order.origin_quantity)
            params = await self.exchange_manager.trader.bundle_chained_order_with_uncreated_order(
                main_order, chained_order, chained_order.update_with_triggering_order_fees
            )
            to_create_orders[bundled_with][1].update(params)
        except KeyError:
            if bundled_with in ignored_orders:
                self.logger.error(f"Ignored order bundled to id {bundled_with}: "
                                  f"associated master order has not been created")

    async def _chain_order(self, order_description, created_orders, ignored_orders, chained_to, fees_currency_side,
                           created_groups, symbol, order_description_by_id):
        failed_order_creation = False
        try:
            base_order = created_orders[chained_to]
            if base_order is None:
                # when an error occurred when creating the initial order
                failed_order_creation = True
                raise KeyError
        except KeyError as e:
            if chained_to in ignored_orders or failed_order_creation:
                message = f"Ignored order chained to id {chained_to}: associated master order has not been created"
                if failed_order_creation:
                    self.logger.info(message)
                else:
                    self.logger.error(message)
            else:
                self.logger.error(
                    f"Ignored chained order from {order_description}. Chained orders have to be sent in the same "
                    f"signal as the order they are chained to. Missing order with id: {e}.")
            return 0
        desc_base_order_quantity = \
            order_description_by_id[chained_to][trading_enums.TradingSignalOrdersAttrs.QUANTITY.value]
        desc_chained_order_quantity = order_description[trading_enums.TradingSignalOrdersAttrs.QUANTITY.value]
        # compute target quantity based on the base order's description quantity to keep accurate %
        target_quantity = decimal.Decimal(f"{desc_chained_order_quantity}") * base_order.origin_quantity / \
            decimal.Decimal(f"{desc_base_order_quantity}")
        chained_order = await self._create_order(
            order_description, symbol, created_groups, fees_currency_side, target_quantity=target_quantity
        )
        if chained_order.origin_quantity == trading_constants.ZERO:
            self.logger.warning(f"Ignored chained order: {chained_order}: not enough funds")
            return 0
        await self.exchange_manager.trader.chain_order(
            base_order, chained_order, chained_order.update_with_triggering_order_fees, False
        )
        if base_order.state is not None and base_order.is_filled() and chained_order.should_be_created():
            try:
                await personal_data.create_as_chained_order(chained_order)
            except errors.OctoBotExchangeError as err:
                # todo later on: handle locale error if necessary
                self.logger.error(f"Failed to create chained order: {chained_order}: {err}")
            return 1
        return 0

    async def _create_order(self, order_description, symbol, created_groups, fees_currency_side, target_quantity=None):
        group = None
        if group_id := order_description[trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value]:
            group = created_groups[group_id]
        side = trading_enums.TradeOrderSide(order_description[trading_enums.TradingSignalOrdersAttrs.SIDE.value])
        reduce_only = order_description[trading_enums.TradingSignalOrdersAttrs.REDUCE_ONLY.value]
        quantity, current_price, max_order_size = await self._get_quantity_from_signal_percent(
            order_description, side, symbol, reduce_only, False
        )
        quantity = target_quantity or quantity
        symbol_market = self.exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
        adapted_quantity = personal_data.decimal_adapt_quantity(symbol_market, quantity)
        if adapted_quantity == trading_constants.ZERO:
            if self.ROUND_TO_MINIMAL_SIZE_IF_NECESSARY:
                adapted_max_size = personal_data.decimal_adapt_quantity(symbol_market, max_order_size)
                if adapted_max_size > trading_constants.ZERO:
                    try:
                        adapted_quantity = personal_data.get_minimal_order_amount(symbol_market)
                        self.logger.info(f"Minimal order amount reached, rounding to {adapted_quantity}")
                    except errors.NotSupported as e:
                        self.logger.warning(f"Impossible to round order to minimal order size: {e}.")
                else:
                    funds_options = " or increase leverage" if self.exchange_manager.is_future else ""
                    self.logger.warning(f"Not enough funds to create minimal size order: current maximum order "
                                        f"size={max_order_size}. Add funds{funds_options} to be able to trade.")
            else:
                self.logger.info("Not enough funds to create order based on signal target amount. "
                                 "Enable minimal size rounding to still trade in this situation. "
                                 "Add funds or increase leverage to be able to trade in this setup.")
        price = order_description[trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value] \
            or order_description[trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value]
        adapted_price = personal_data.decimal_adapt_price(symbol_market, decimal.Decimal(f"{price}"))
        order_type = trading_enums.TraderOrderType(
            order_description[trading_enums.TradingSignalOrdersAttrs.TYPE.value]
        )
        if order_type in (trading_enums.TraderOrderType.BUY_MARKET, trading_enums.TraderOrderType.SELL_MARKET):
            # side param is not supported for these orders
            side = None
        associated_entries = order_description.get(
            trading_enums.TradingSignalOrdersAttrs.ASSOCIATED_ORDER_IDS.value, None
        )
        trigger_above = order_description.get(trading_enums.TradingSignalOrdersAttrs.TRIGGER_ABOVE.value, None)
        trailing_profile = None
        if trailing_profile_details := order_description.get(
            trading_enums.TradingSignalOrdersAttrs.TRAILING_PROFILE.value
        ):
            trailing_profile = personal_data.create_trailing_profile(
                personal_data.TrailingProfileTypes(
                    order_description[trading_enums.TradingSignalOrdersAttrs.TRAILING_PROFILE_TYPE.value],
                ),
                trailing_profile_details
            )
        is_active = order_description.get(trading_enums.TradingSignalOrdersAttrs.IS_ACTIVE.value, True)
        active_trigger_price = (
            None if order_description.get(trading_enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_PRICE.value) is None
            else decimal.Decimal(str(
                order_description[trading_enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_PRICE.value]
            ))
        )
        active_trigger_above = order_description.get(trading_enums.TradingSignalOrdersAttrs.ACTIVE_TRIGGER_ABOVE.value)
        cancel_policy = None
        if cancel_policy_type := order_description.get(
            trading_enums.TradingSignalOrdersAttrs.CANCEL_POLICY_TYPE.value
        ):
            cancel_policy = personal_data.create_cancel_policy(
                cancel_policy_type,
                order_description[trading_enums.TradingSignalOrdersAttrs.CANCEL_POLICY_KWARGS.value]
            )
        order = personal_data.create_order_instance(
            trader=self.exchange_manager.trader,
            order_type=order_type,
            symbol=symbol,
            current_price=current_price,
            quantity=adapted_quantity,
            price=adapted_price,
            side=side,
            trigger_above=trigger_above,
            tag=order_description[trading_enums.TradingSignalOrdersAttrs.TAG.value],
            order_id=order_description[trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value],
            group=group,
            fees_currency_side=fees_currency_side,
            reduce_only=reduce_only,
            associated_entry_id=associated_entries[0] if associated_entries else None,
            trailing_profile=trailing_profile,
            is_active=is_active,
            active_trigger_price=active_trigger_price,
            active_trigger_above=active_trigger_above,
            cancel_policy=cancel_policy
        )
        if associated_entries and len(associated_entries) > 1:
            for associated_entry in associated_entries[1:]:
                order.associate_to_entry(associated_entry)
        order.update_with_triggering_order_fees = order_description.get(
            trading_enums.TradingSignalOrdersAttrs.UPDATE_WITH_TRIGGERING_ORDER_FEES.value, False
        )
        return order

    def _get_or_create_order_group(self, order_description, group_id):
        group_type = order_description[trading_enums.TradingSignalOrdersAttrs.GROUP_TYPE.value]
        group_class = tentacles_management.get_deep_class_from_parent_subclasses(group_type, personal_data.OrderGroup)
        active_order_swap_strategy = None
        if active_strategy_type := order_description.get(
            trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TYPE.value
        ):
            active_order_swap_strategy = tentacles_management.get_deep_class_from_parent_subclasses(
                active_strategy_type, personal_data.ActiveOrderSwapStrategy
            )(
                swap_timeout=
                    order_description[trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TIMEOUT.value],
                trigger_price_configuration=
                    order_description[trading_enums.TradingSignalOrdersAttrs.ACTIVE_SWAP_STRATEGY_TRIGGER_CONFIG.value]
            )
        return self.exchange_manager.exchange_personal_data.orders_manager.get_or_create_group(
            group_class, group_id, active_order_swap_strategy=active_order_swap_strategy
        )

    async def _create_orders(self, orders_descriptions, symbol):
        to_create_orders = {}   # dict of (orders, orders_param)
        created_groups = {}
        created_orders = {}
        ignored_orders = set()
        order_description_by_id = {
            orders_description[trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value]: orders_description
            for orders_description in orders_descriptions
        }
        fees_currency_side = None
        if self.exchange_manager.is_future:
            fees_currency_side = self.exchange_manager.exchange.get_pair_contract(symbol)\
                .get_fees_currency_side()
        for order_description in orders_descriptions:
            if group_id := order_description[trading_enums.TradingSignalOrdersAttrs.GROUP_ID.value]:
                group = self._get_or_create_order_group(order_description, group_id)
                await group.enable(False)
                created_groups[group_id] = group
            if order_description[trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value] is not None:
                # bundled orders are created later on
                continue
            if order_description[trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value] is not None:
                # chained orders are created later on
                continue
            created_order = await self._create_order(order_description, symbol, created_groups, fees_currency_side)
            if created_order.origin_quantity == trading_constants.ZERO:
                order_id = order_description[trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value]
                self.logger.error(f"Impossible to create order: {created_order} "
                                  f"(id: {order_id}): not enough funds on the account.")
                ignored_orders.add(order_id)
            else:
                to_create_orders[order_description[
                    trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value]
                ] = (created_order, {})
        for order_description in orders_descriptions:
            if bundled_with := order_description[trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value]:
                await self._bundle_order(order_description, to_create_orders, ignored_orders, bundled_with,
                                         fees_currency_side, created_groups, symbol)
        # create orders
        already_handled_order_ids = self.exchange_manager.exchange_personal_data.orders_manager\
            .get_all_active_and_pending_orders_id()
        for order_id, order_with_param in to_create_orders.items():
            if order_id in already_handled_order_ids:
                self.logger.debug(f"Ignored order with order id {order_id}: order already handled")
                continue
            created_orders[order_id] = \
                await self._create_order_on_exchange(order_with_param[0], params=order_with_param[1])
        # handle chained orders
        created_chained_orders_count = 0
        for order_description in orders_descriptions:
            if (chained_to := order_description[trading_enums.TradingSignalOrdersAttrs.CHAINED_TO.value]) \
                    and order_description[trading_enums.TradingSignalOrdersAttrs.BUNDLED_WITH.value] is None:
                order_id = \
                    order_description[trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value]
                if order_id in already_handled_order_ids:
                    self.logger.debug(
                        f"Ignored order with order id {order_id}: order already handled"
                    )
                    continue
                created_chained_orders_count += \
                    await self._chain_order(order_description, created_orders, ignored_orders, chained_to,
                                            fees_currency_side, created_groups, symbol, order_description_by_id)

        for group in created_groups.values():
            await group.enable(True)
        return len(to_create_orders) + created_chained_orders_count

    def get_open_order_from_description(self, order_descriptions, symbol):
        found_orders = []
        for order_description in order_descriptions:
            # filter orders using order_id
            if accurate_orders := [
                (order_description, order)
                for order in self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol=symbol)
                if order.order_id == order_description[trading_enums.TradingSignalOrdersAttrs.ORDER_ID.value]
            ]:
                found_orders += accurate_orders
                continue
            # 2nd chance: use order type and price as these are kept between bot restarts (loaded from exchange)
            orders = [
                (order_description, order)
                for order in self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol=symbol)
                if (order.origin_price == order_description[trading_enums.TradingSignalOrdersAttrs.STOP_PRICE.value] or
                    order.origin_price == order_description[trading_enums.TradingSignalOrdersAttrs.LIMIT_PRICE.value])
                    and self._is_compatible_order_type(order, order_description)
            ]
            if orders:
                found_orders += orders
            else:
                self.logger.error(
                    f"Order not found on {self.exchange_manager.exchange_name} open orders, "
                    f"description: {order_description}"
                )
        return found_orders

    def _is_compatible_order_type(self, order, order_description):
        side = order_description[trading_enums.TradingSignalOrdersAttrs.SIDE.value]
        if not order.side.value == side:
            return False
        order_type = order_description[trading_enums.TradingSignalOrdersAttrs.TYPE.value]
        return personal_data.TraderOrderTypeClasses[order_type] == order.__class__

    def _parse_signal_orders(self, signal: commons_signals.Signal):
        to_create_orders = []
        to_edit_orders = []
        to_cancel_orders = []
        to_group_orders = []
        for order_description in [signal.content] + self._get_nested_signal_order_descriptions(signal.content):
            action = order_description.get(trading_enums.TradingSignalCommonsAttrs.ACTION.value)
            if action == trading_enums.TradingSignalOrdersActions.CREATE.value:
                to_create_orders.append(order_description)
            elif action == trading_enums.TradingSignalOrdersActions.EDIT.value:
                to_edit_orders.append(order_description)
            elif action == trading_enums.TradingSignalOrdersActions.CANCEL.value:
                to_cancel_orders.append(order_description)
            elif action == trading_enums.TradingSignalOrdersActions.ADD_TO_GROUP.value:
                to_group_orders.append(order_description)
        return to_create_orders, to_edit_orders, to_cancel_orders, to_group_orders

    def _get_nested_signal_order_descriptions(self, order_description):
        order_descriptions = []
        for nested_desc in order_description.get(trading_enums.TradingSignalOrdersAttrs.ADDITIONAL_ORDERS.value) or []:
            order_descriptions.append(nested_desc)
            # also explore multiple level nested signals
            order_descriptions += self._get_nested_signal_order_descriptions(nested_desc)
        return order_descriptions

    def _update_orders_according_to_config(self, order_descriptions):
        for order_description in order_descriptions:
            self._update_according_to_config(order_description)

    def _update_according_to_config(self, order_description):
        # filter max buy order size
        side = order_description.get(trading_enums.TradingSignalOrdersAttrs.SIDE.value, None)
        if side is None:
            found_orders = self.get_open_order_from_description([order_description], None)
            try:
                side = found_orders[0][1].side.value
            except KeyError:
                pass
        if side is trading_enums.TradeOrderSide.BUY.value:
            for key in (trading_enums.TradingSignalOrdersAttrs.TARGET_AMOUNT.value,
                        trading_enums.TradingSignalOrdersAttrs.UPDATED_TARGET_AMOUNT.value):
                self._update_quantity_according_to_config(order_description, key)

    def _update_quantity_according_to_config(self, order_description, quantity_key):
        quantity_type, quantity = script_keywords.parse_quantity(order_description[quantity_key])
        if quantity is not None and quantity > self.MAX_VOLUME_PER_BUY_ORDER:
            self.logger.warning(f"Updating signal order {quantity_key} from {quantity}{quantity_type.value} "
                                f"to {self.MAX_VOLUME_PER_BUY_ORDER}{quantity_type.value}")
            order_description[quantity_key] = f"{self.MAX_VOLUME_PER_BUY_ORDER}{quantity_type.value}"

    async def _send_alert_notification(self, symbol, created, edited, cancelled):
        try:
            import octobot_services.api as services_api
            import octobot_services.enums as services_enum
            title = f"New trading signal for {symbol}"
            messages = []
            if created:
                messages.append(f"- Created {created} order{'s' if created > 1 else ''}")
            if edited:
                messages.append(f"- Edited {edited} order{'s' if edited > 1 else ''}")
            if cancelled:
                messages.append(f"- Cancelled {cancelled} order{'s' if cancelled > 1 else ''}")
            content = "\n".join(messages)
            await services_api.send_notification(services_api.create_notification(
                content, title=title,
                category=services_enum.NotificationCategory.TRADING_SCRIPT_ALERTS
            ))
        except ImportError as e:
            self.logger.exception(e, True, f"Impossible to send notification: {e}")

    # exchange methods: bypass trading modes api to avoid sending signals
    async def _create_order_on_exchange(self, order, params):
        return await self.exchange_manager.trader.create_order(order, params=params)

    async def _cancel_order_on_exchange(self, order):
        await self.exchange_manager.trader.cancel_order(order)

    async def _edit_order_on_exchange(self, order, edited_quantity=None, edited_price=None, edited_stop_price=None):
        await self.exchange_manager.trader.edit_order(
            order,
            edited_quantity=edited_quantity,
            edited_price=edited_price,
            edited_stop_price=edited_stop_price
        )

    async def _set_leverage(self, symbol: str, leverage: decimal.Decimal, side):
        context = script_keywords.get_base_context(self.trading_mode, symbol=symbol)
        await script_keywords.set_leverage(context, leverage, side=side)


class RemoteTradingSignalsModeProducer(trading_modes.AbstractTradingModeProducer):

    def get_channels_registration(self):
        # trading mode is waking up this producer directly from signal channel
        return []

    @trading_modes.enabled_trader_only()
    async def signal_callback(self, signal):
        exchange_type = signal.content[trading_enums.TradingSignalOrdersAttrs.EXCHANGE_TYPE.value]
        if exchange_type == exchanges.get_exchange_type(self.exchange_manager).value:
            state = trading_enums.EvaluatorStates.UNKNOWN
            symbol = (
                signal.content.get(trading_enums.TradingSignalOrdersAttrs.SYMBOL.value)
                or signal.content.get(trading_enums.TradingSignalPositionsAttrs.SYMBOL.value)
            )
            await self._set_state(
                self.trading_mode.cryptocurrency,
                symbol,
                state, signal
            )
        else:
            self.logger.error(f"Incompatible signal exchange type: {exchange_type} "
                              f"with current exchange: {self.exchange_manager}")

    async def _set_state(self, cryptocurrency: str, symbol: str, new_state, signal):
        async with self.trading_mode_trigger():
            self.state = new_state
            self.logger.info(f"[{symbol}] update state: {self.state.name}")
            # call orders creation from consumers
            await self.submit_trading_evaluation(cryptocurrency=cryptocurrency,
                                                 symbol=symbol,
                                                 time_frame=None,
                                                 final_note=self.final_eval,
                                                 state=self.state,
                                                 data=signal)

    async def stop(self):
        if self.trading_mode is not None:
            self.trading_mode.flush_trading_mode_consumers()
        await super().stop()
