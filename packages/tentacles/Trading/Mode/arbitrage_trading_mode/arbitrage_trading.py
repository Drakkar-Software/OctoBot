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
import asyncio
import decimal

import async_channel.constants as channel_constants
import async_channel.channels as channel_instances
import octobot.constants as octobot_constants
import octobot_commons.data_util as data_util
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.pretty_printer as pretty_printer
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.api as trading_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.constants as trading_constants
import octobot_trading.modes as trading_modes
import octobot_trading.octobot_channel_consumer as octobot_channel_consumer
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import tentacles.Trading.Mode.arbitrage_trading_mode.arbitrage_container as arbitrage_container_import


class ArbitrageTradingMode(trading_modes.AbstractTradingMode):

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.merged_symbol = None

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        self.UI.user_input(
            "portfolio_percent_per_trade", commons_enums.UserInputTypes.FLOAT, 25, inputs,
            min_val=0, max_val=100,
            title="Trade size: percent of your portfolio to include in each arbitrage order.",
        )
        self.UI.user_input(
            "stop_loss_delta_percent", commons_enums.UserInputTypes.FLOAT, 0.1, inputs,
            min_val=0, max_val=100,
            title="Stop loss price: price percent from the price of the initial order to set the stop loss on.",
        )
        exchanges = list(self.config[commons_constants.CONFIG_EXCHANGES].keys())
        self.UI.user_input(
            "exchanges_to_trade_on", commons_enums.UserInputTypes.MULTIPLE_OPTIONS, [exchanges[0]], inputs,
            options=exchanges,
            title="Trading exchanges: exchanges on which to perform arbitrage trading: these will be used to create "
                  "arbitrage orders. Leaving this empty will result in arbitrage trading on every exchange, "
                  "which is sub-optimal. Add exchange configurations to add exchanges to this list.",
        )
        self.UI.user_input(
            "minimal_price_delta_percent", commons_enums.UserInputTypes.FLOAT, 0.25, inputs,
            min_val=0, max_val=100,
            title="Cross exchange triggering delta: minimal percent difference to trigger an arbitrage order. Remember "
                  "to set it higher than twice your trading exchanges' fees since two orders will be placed each time.",
        )
        self.UI.user_input(
            "enable_shorts", commons_enums.UserInputTypes.BOOLEAN, True, inputs,
            title="Enable shorts: enable arbitrage trades starting with a sell order and ending with a buy order.",
        )
        self.UI.user_input(
            "enable_longs", commons_enums.UserInputTypes.BOOLEAN, True, inputs,
            title="Enable longs: enable arbitrage trades starting with a buy order and ending with a sell order.",
        )

    def get_current_state(self) -> (str, float):
        return super().get_current_state()[0] if self.producers[0].state is None else self.producers[0].state.name, \
               self.producers[0].final_eval if self.producers[0].final_eval else "N/A"

    def get_mode_producer_classes(self) -> list:
        return [ArbitrageModeProducer]

    def get_mode_consumer_classes(self) -> list:
        return [ArbitrageModeConsumer]

    async def create_consumers(self) -> list:
        consumers = await super().create_consumers()
        # order consumer
        order_consumer = await exchanges_channel.get_chan(trading_personal_data.OrdersChannel.get_name(),
                                                          self.exchange_manager.id).new_consumer(
            self._order_notification_callback,
            symbol=self.symbol if self.symbol else channel_constants.CHANNEL_WILDCARD
        )
        return consumers + [order_consumer]

    async def _order_notification_callback(self, exchange, exchange_id, cryptocurrency, symbol, order,
                                           update_type, is_from_bot):
        if order[
            trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.FILLED.value \
                and is_from_bot:
            await self.producers[0].order_filled_callback(order)
        elif order[
            trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.CANCELED.value \
                and is_from_bot:
            await self.producers[0].order_cancelled_callback(order)

    @classmethod
    def get_is_trading_on_exchange(cls, exchange_name, tentacles_setup_config) -> bool:
        """
        :return: True if exchange_name is in exchanges_to_trade_on (case insensitive)
        or if exchanges_to_trade_on is missing or empty
        """
        exchanges_to_trade_on = tentacles_manager_api.get_tentacle_config(tentacles_setup_config, cls) \
            .get("exchanges_to_trade_on", [])
        return not exchanges_to_trade_on or exchange_name.lower() in [
            exchange.lower() for exchange in exchanges_to_trade_on
        ]

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        """
        :return: True if the mode is not symbol dependant else False
        """
        return False

    @staticmethod
    def is_backtestable():
        return False


class ArbitrageModeConsumer(trading_modes.AbstractTradingModeConsumer):
    ARBITRAGE_CONTAINER_KEY = "arbitrage"
    ARBITRAGE_PHASE_KEY = "phase"
    QUANTITY_KEY = "quantity"
    INITIAL_PHASE = "initial"
    SECONDARY_PHASE = "secondary"

    def __init__(self, trading_mode):
        super().__init__(trading_mode)
        self.open_arbitrages = []

    def on_reload_config(self):
        """
        Called at constructor and after the associated trading mode's reload_config.
        Implement if necessary
        """
        self.PORTFOLIO_PERCENT_PER_TRADE = decimal.Decimal(str(
            self.trading_mode.trading_config["portfolio_percent_per_trade"] / 100))
        self.STOP_LOSS_DELTA_FROM_OWN_PRICE = decimal.Decimal(str(
            self.trading_mode.trading_config["stop_loss_delta_percent"] / 100))

    async def create_new_orders(self, symbol, final_note, state, **kwargs):
        # no possible default values in kwargs: interrupt if missing element
        data = kwargs[self.CREATE_ORDER_DATA_PARAM]
        phase = data[ArbitrageModeConsumer.ARBITRAGE_PHASE_KEY]
        arbitrage_container = data[ArbitrageModeConsumer.ARBITRAGE_CONTAINER_KEY]
        if phase == ArbitrageModeConsumer.INITIAL_PHASE:
            await self._create_initial_arbitrage_order(arbitrage_container)
        elif phase == ArbitrageModeConsumer.SECONDARY_PHASE:
            await self._create_secondary_arbitrage_order(arbitrage_container, data[ArbitrageModeConsumer.QUANTITY_KEY])

    async def _create_initial_arbitrage_order(self, arbitrage_container):
        current_symbol_holding, current_market_holding, market_quantity, price, symbol_market = \
            await trading_personal_data.get_pre_order_data(self.exchange_manager,
                                                           symbol=self.trading_mode.symbol,
                                                           timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT)

        created_orders = []
        order_type = trading_enums.TraderOrderType.BUY_LIMIT \
            if arbitrage_container.state is trading_enums.EvaluatorStates.LONG \
            else trading_enums.TraderOrderType.SELL_LIMIT
        quantity = self._get_quantity_from_holdings(current_symbol_holding, market_quantity, arbitrage_container.state)
        if order_type is trading_enums.TraderOrderType.SELL_LIMIT:
            quantity = trading_personal_data.decimal_add_dusts_to_quantity_if_necessary(quantity, price, symbol_market,
                                                                                        current_symbol_holding)
        for order_quantity, order_price in trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                quantity,
                arbitrage_container.own_exchange_price,
                symbol_market):
            current_order = trading_personal_data.create_order_instance(trader=self.exchange_manager.trader,
                                                                        order_type=order_type,
                                                                        symbol=self.trading_mode.symbol,
                                                                        current_price=arbitrage_container.own_exchange_price,
                                                                        quantity=order_quantity,
                                                                        price=order_price)
            created_order = await self.trading_mode.create_order(current_order)
            if created_order is not None:
                created_orders.append(created_order)
                arbitrage_container.initial_limit_order_id = created_order.order_id
                self.open_arbitrages.append(arbitrage_container)
            # only create one order per arbitrage
            return created_orders

    async def _create_secondary_arbitrage_order(self, arbitrage_container, quantity):
        created_orders = []
        current_symbol_holding, current_market_holding, market_quantity, price, symbol_market = \
            await trading_personal_data.get_pre_order_data(self.exchange_manager,
                                                           symbol=self.trading_mode.symbol,
                                                           timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT)
        now_selling = arbitrage_container.state is trading_enums.EvaluatorStates.LONG
        entry_id = arbitrage_container.initial_limit_order_id
        if now_selling:
            quantity = trading_personal_data.decimal_add_dusts_to_quantity_if_necessary(quantity, price, symbol_market,
                                                                                        current_symbol_holding)
        for order_quantity, order_price in trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
            quantity,
            arbitrage_container.target_price,
            symbol_market
        ):
            oco_group = self.exchange_manager.exchange_personal_data.orders_manager.create_group(
                trading_personal_data.OneCancelsTheOtherOrderGroup,
                active_order_swap_strategy=trading_personal_data.StopFirstActiveOrderSwapStrategy()
            )
            current_limit_order = trading_personal_data.create_order_instance(
                trader=self.exchange_manager.trader,
                order_type=trading_enums.TraderOrderType.SELL_LIMIT if now_selling
                else trading_enums.TraderOrderType.BUY_LIMIT,
                symbol=self.trading_mode.symbol,
                current_price=arbitrage_container.own_exchange_price,
                quantity=order_quantity,
                price=order_price,
                group=oco_group,
                associated_entry_id=entry_id
            )
            stop_price = self._get_stop_loss_price(symbol_market,
                                                   arbitrage_container.own_exchange_price,
                                                   now_selling)
            current_stop_order = trading_personal_data.create_order_instance(
                trader=self.exchange_manager.trader,
                order_type=trading_enums.TraderOrderType.STOP_LOSS,
                symbol=self.trading_mode.symbol,
                current_price=arbitrage_container.own_exchange_price,
                quantity=order_quantity,
                price=stop_price,
                group=oco_group,
                side=trading_enums.TradeOrderSide.SELL
                if now_selling else trading_enums.TradeOrderSide.BUY,
                associated_entry_id=entry_id,
            )
            # in futures, inactive orders are not necessary
            if self.exchange_manager.trader.enable_inactive_orders and not self.exchange_manager.is_future:
                await oco_group.active_order_swap_strategy.apply_inactive_orders(
                    [current_limit_order, current_stop_order]
                )
            if created_limit_order := await self.trading_mode.create_order(current_limit_order):
                created_stop_order = await self.trading_mode.create_order(current_stop_order)
                created_orders.append(created_limit_order)
                arbitrage_container.secondary_limit_order_id = created_limit_order.order_id
                arbitrage_container.secondary_stop_order_id = created_stop_order.order_id
            return created_orders
        return []

    def _get_quantity_from_holdings(self, current_symbol_holding, market_quantity, state):
        # TODO handle quantity in a non dynamic manner (avoid subsequent orders volume reduction)
        if state is trading_enums.EvaluatorStates.LONG:
            return market_quantity * self.PORTFOLIO_PERCENT_PER_TRADE
        return current_symbol_holding * self.PORTFOLIO_PERCENT_PER_TRADE

    def _get_stop_loss_price(self, symbol_market, starting_price, now_selling):
        if now_selling:
            return trading_personal_data.decimal_adapt_price(symbol_market,
                                                             starting_price * (trading_constants.ONE
                                                                               - self.STOP_LOSS_DELTA_FROM_OWN_PRICE))
        return trading_personal_data.decimal_adapt_price(symbol_market,
                                                         starting_price * (trading_constants.ONE
                                                                           + self.STOP_LOSS_DELTA_FROM_OWN_PRICE))


class ArbitrageModeProducer(trading_modes.AbstractTradingModeProducer):

    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        self.own_exchange_mark_price: decimal.Decimal = None
        self.other_exchanges_mark_prices = {}
        self.state = trading_enums.EvaluatorStates.NEUTRAL
        self.final_eval = ""
        self.quote, self.base = symbol_util.parse_symbol(self.trading_mode.symbol).base_and_quote()
        self.lock = asyncio.Lock()
        self.enable_shorts = self.enable_longs = True

    def on_reload_config(self):
        """
        Called at constructor and after the associated trading mode's reload_config.
        Implement if necessary
        """
        self.sup_triggering_price_delta_ratio: decimal.Decimal = \
            1 + decimal.Decimal(str(self.trading_mode.trading_config["minimal_price_delta_percent"] / 100))
        self.inf_triggering_price_delta_ratio: decimal.Decimal = \
            1 - decimal.Decimal(str(self.trading_mode.trading_config["minimal_price_delta_percent"] / 100))
        self.enable_shorts = self.trading_mode.trading_config.get("enable_shorts", True)
        self.enable_longs = self.trading_mode.trading_config.get("enable_longs", True)

    async def inner_start(self) -> None:
        """
        Start trading mode channels subscriptions
        """
        try:
            self.logger.info(f"Starting on listening for {self.trading_mode.symbol} arbitrage opportunities on "
                             f"{self.exchange_name} based on other exchanges prices.")
            for exchange_id in trading_api.get_all_exchange_ids_with_same_matrix_id(self.exchange_manager.exchange_name,
                                                                                    self.exchange_manager.id):
                # subscribe on existing exchanges
                if exchange_id != self.exchange_manager.id:
                    await self._subscribe_exchange_id_mark_price(exchange_id)
            await exchanges_channel.get_chan(trading_constants.MARK_PRICE_CHANNEL, self.exchange_manager.id). \
                new_consumer(
                self._own_exchange_mark_price_callback,
                symbol=self.trading_mode.symbol
            )
            await channel_instances.get_chan_at_id(octobot_constants.OCTOBOT_CHANNEL, self.trading_mode.bot_id). \
                new_consumer(
                # listen for new available exchange
                self._exchange_added_callback,
                subject=commons_enums.OctoBotChannelSubjects.NOTIFICATION.value,
                action=octobot_channel_consumer.OctoBotChannelTradingActions.EXCHANGE.value
            )
        except Exception as e:
            self.logger.exception(e, True, f"Error when starting arbitrage trading on {self.exchange_name}: {e}")

    async def order_filled_callback(self, filled_order):
        """
        Called when an order is filled: create secondary orders if the filled order is an initial order
        :param filled_order:
        :return: None
        """
        order_id = filled_order[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        async with self.lock:
            arbitrage = self._get_arbitrage(order_id)
            if arbitrage is not None:
                filled_quantity = filled_order[trading_enums.ExchangeConstantsOrderColumns.FILLED.value]
                if arbitrage.passed_initial_order:
                    # filled limit order or stop loss: close arbitrage
                    arbitrage_success = filled_order[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] != \
                                        trading_enums.TradeOrderType.STOP_LOSS.value
                    if arbitrage.state is trading_enums.EvaluatorStates.LONG:
                        filled_quantity = decimal.Decimal(str(filled_quantity * filled_order[
                            trading_enums.ExchangeConstantsOrderColumns.PRICE.value]))
                    self._log_results(arbitrage, arbitrage_success, filled_quantity)
                    self._close_arbitrage(arbitrage)
                else:
                    await self._trigger_arbitrage_secondary_order(arbitrage, filled_order, filled_quantity)

    async def order_cancelled_callback(self, cancelled_order):
        """
        Called when an order is cancelled (from bot or user)
        :param cancelled_order: the cancelled order
        :return: None
        """
        order_id = cancelled_order[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        async with self.lock:
            to_remove_orders = [arbitrage
                                for arbitrage in self._get_open_arbitrages()
                                if arbitrage.should_be_discarded_after_order_cancel(order_id)]
            for arbitrage in to_remove_orders:
                self._close_arbitrage(arbitrage)

    async def _own_exchange_mark_price_callback(
            self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, mark_price
    ):
        """
        Called on a price update from the current exchange
        :param exchange: name of the exchange
        :param exchange_id: id of the exchange
        :param cryptocurrency: related cryptocurrency
        :param symbol: related symbol
        :param mark_price: updated mark price
        :return: None
        """
        self.own_exchange_mark_price = decimal.Decimal(str(mark_price))
        try:
            if self.other_exchanges_mark_prices:
                await self._analyse_arbitrage_opportunities()
        except Exception as e:
            self.logger.exception(e, True, f"Error when handling mark_price_callback for {self.exchange_name}: {e}")

    async def _mark_price_callback(
            self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, mark_price
    ):
        """
        Called on a price update from an exchange that is different from the current one
        :param exchange: name of the exchange
        :param exchange_id: id of the exchange
        :param cryptocurrency: related cryptocurrency
        :param symbol: related symbol
        :param mark_price: updated mark price
        :return: None
        """
        self.other_exchanges_mark_prices[exchange] = decimal.Decimal(str(mark_price))
        try:
            if self.own_exchange_mark_price is not None:
                await self._analyse_arbitrage_opportunities()
        except Exception as e:
            self.logger.exception(e, True, f"Error when handling mark_price_callback for {self.exchange_name}: {e}")

    async def _analyse_arbitrage_opportunities(self):
        async with self.trading_mode_trigger():
            other_exchanges_average_price = \
                decimal.Decimal(str(data_util.mean(self.other_exchanges_mark_prices.values())))
            state = None
            if other_exchanges_average_price > self.own_exchange_mark_price * self.sup_triggering_price_delta_ratio:
                # min long = high price > own_price / (1 - 2fees)
                state = trading_enums.EvaluatorStates.LONG
            elif other_exchanges_average_price < self.own_exchange_mark_price * self.inf_triggering_price_delta_ratio:
                # min short = low price < own_price * (1 - 2fees)
                state = trading_enums.EvaluatorStates.SHORT
            if self._is_traded_state(state):
                # lock to prevent concurrent order management
                async with self.lock:
                    # 1. cancel invalided opportunities if any
                    await self._ensure_no_expired_opportunities(other_exchanges_average_price, state)
                    # 2. handle new opportunities
                    await self._trigger_arbitrage_opportunity(other_exchanges_average_price, state)

    def _is_traded_state(self, state):
        if state is None:
            return False
        if state is trading_enums.EvaluatorStates.SHORT:
            return self.enable_shorts
        if state is trading_enums.EvaluatorStates.LONG:
            return self.enable_longs

    async def _trigger_arbitrage_opportunity(self, other_exchanges_average_price, state):
        # ensure no similar arbitrage is already in place
        if self._ensure_no_existing_arbitrage_on_this_price(state):
            self._log_arbitrage_opportunity_details(other_exchanges_average_price, state)
            arbitrage_container = arbitrage_container_import.ArbitrageContainer(self.own_exchange_mark_price,
                                                                                other_exchanges_average_price, state)
            await self._create_arbitrage_initial_order(arbitrage_container)
            self._register_state(state, other_exchanges_average_price - self.own_exchange_mark_price)

    @trading_modes.enabled_trader_only()
    async def _create_arbitrage_initial_order(self, arbitrage_container):
        data = {
            ArbitrageModeConsumer.ARBITRAGE_CONTAINER_KEY: arbitrage_container,
            ArbitrageModeConsumer.ARBITRAGE_PHASE_KEY: ArbitrageModeConsumer.INITIAL_PHASE
        }
        await self.submit_trading_evaluation(cryptocurrency=self.trading_mode.cryptocurrency,
                                                symbol=self.trading_mode.symbol,
                                                time_frame=None,
                                                state=arbitrage_container.state,
                                                data=data)

    async def _trigger_arbitrage_secondary_order(self, arbitrage: arbitrage_container_import.ArbitrageContainer,
                                                 filled_order: dict,
                                                 filled_quantity_before_fees: decimal.Decimal):
        arbitrage.passed_initial_order = True
        now_buying = arbitrage.state is trading_enums.EvaluatorStates.SHORT
        # a SHORT arbitrage is an initial SELL followed by a BUY order.
        # Here in the secondary order construction:
        # - Buy (at a lower price) when the arbitrage is a SHORT
        # - Sell (at a higher price) when the arbitrage is a LONG
        paid_fees_in_quote = trading_personal_data.total_fees_from_order_dict(filled_order, self.quote)
        secondary_quantity = filled_quantity_before_fees - paid_fees_in_quote
        filled_price = decimal.Decimal(str(filled_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]))
        if now_buying:
            arbitrage.initial_before_fee_filled_quantity = filled_quantity_before_fees
        else:
            arbitrage.initial_before_fee_filled_quantity = filled_quantity_before_fees * filled_price
        if now_buying:
            # buying at a lower price: buy more than what has been sold, take fees into account
            fees_in_base = trading_personal_data.total_fees_from_order_dict(filled_order, self.base)
            secondary_base_amount = filled_price * secondary_quantity - fees_in_base
            secondary_quantity = secondary_base_amount / arbitrage.target_price
        await self._create_arbitrage_secondary_order(arbitrage, secondary_quantity)

    @trading_modes.enabled_trader_only()
    async def _create_arbitrage_secondary_order(self, arbitrage_container, secondary_quantity):
        data = {
            ArbitrageModeConsumer.ARBITRAGE_CONTAINER_KEY: arbitrage_container,
            ArbitrageModeConsumer.ARBITRAGE_PHASE_KEY: ArbitrageModeConsumer.SECONDARY_PHASE,
            ArbitrageModeConsumer.QUANTITY_KEY: secondary_quantity
        }
        await self.submit_trading_evaluation(cryptocurrency=self.trading_mode.cryptocurrency,
                                                symbol=self.trading_mode.symbol,
                                                time_frame=None,
                                                state=arbitrage_container.state,
                                                data=data)

    def _ensure_no_existing_arbitrage_on_this_price(self, state):
        for arbitrage_container in self._get_open_arbitrages():
            if arbitrage_container.is_similar(self.own_exchange_mark_price, state):
                return False
        return True

    def _get_arbitrage(self, order_id):
        for arbitrage_container in self._get_open_arbitrages():
            if arbitrage_container.is_watching_this_order(order_id):
                return arbitrage_container
        return None

    async def _ensure_no_expired_opportunities(self, other_exchanges_average_price, state):
        to_remove_arbitrages = []
        for arbitrage_container in self._get_open_arbitrages():
            # look for expired opposite side arbitrages and cancel them if still possible
            if arbitrage_container.state is not state and \
                    arbitrage_container.is_expired(other_exchanges_average_price):
                if await self._cancel_order(arbitrage_container):
                    to_remove_arbitrages.append(arbitrage_container)

        for arbitrage in to_remove_arbitrages:
            self._get_open_arbitrages().remove(arbitrage)

    @trading_modes.enabled_trader_only(disabled_return_value=False)
    async def _cancel_order(self, arbitrage_container) -> bool:
        try:
            if await self.trading_mode.cancel_order(
                self.exchange_manager.exchange_personal_data.orders_manager.get_order(
                    arbitrage_container.initial_limit_order_id
                )
            ):
                self.logger.info(f"Arbitrage opportunity expired: cancelled initial order on "
                                 f"{self.exchange_manager.exchange_name} for {self.trading_mode.symbol} at"
                                 f"{arbitrage_container.own_exchange_price}")
                return True
            return False
        except (trading_errors.OrderCancelError, trading_errors.UnexpectedExchangeSideOrderStateError) as err:
            self.logger.warning(f"Skipping order cancel: {err}")
            # order can't be cancelled, ignore it and proceed
            return True
        except KeyError:
            # order is not open anymore: can't cancel
            return False

    def _log_arbitrage_opportunity_details(self, other_exchanges_average_price, state):
        price_difference = other_exchanges_average_price / self.own_exchange_mark_price
        difference_percent = pretty_printer.round_with_decimal_count(float(price_difference) * 100 - 100, 5)
        self.logger.debug(f"Arbitrage opportunity on {self.exchange_manager.exchange_name} {state.name} for "
                          f"{self.trading_mode.symbol} "
                          f"({str(self.own_exchange_mark_price)} vs {other_exchanges_average_price} on average "
                          f"based on {len(self.other_exchanges_mark_prices)} registered exchange(s): "
                          f"{'+' if price_difference > 1 else ''}{difference_percent}%).")

    def _log_results(self, arbitrage, success, filled_quantity):
        self.logger.info(f"Closed {arbitrage.state.name} arbitrage on {self.exchange_manager.exchange_name} ["
                         f"{'success' if success else 'stop loss triggered'}] with {self.trading_mode.symbol}: "
                         f"profit before {'final' if arbitrage.state is trading_enums.EvaluatorStates.SHORT else 'all'} "
                         f"fees: {str(filled_quantity - arbitrage.initial_before_fee_filled_quantity)} "
                         f"{self.quote if arbitrage.state is trading_enums.EvaluatorStates.SHORT else self.base}")

    def _close_arbitrage(self, arbitrage):
        self._get_open_arbitrages().remove(arbitrage)
        self.state = trading_enums.EvaluatorStates.NEUTRAL
        self.final_eval = ""

    def _get_open_arbitrages(self):
        return self.trading_mode.get_trading_mode_consumers()[0].open_arbitrages

    def _register_state(self, new_state, price_difference):
        self.state = new_state
        self.final_eval = f"{'+' if float(price_difference) > 0 else ''}{str(price_difference)}"
        self.logger.info(f"New state on {self.exchange_manager.exchange_name} for {self.trading_mode.symbol}: "
                         f"{new_state}, price difference: {self.final_eval}")

    async def _exchange_added_callback(self, bot_id: str, subject: str, action: str, data: dict):
        if octobot_channel_consumer.OctoBotChannelTradingDataKeys.EXCHANGE_ID.value in data:
            # New exchange available: subscribe to its price updates
            await self._subscribe_exchange_id_mark_price(
                data[octobot_channel_consumer.OctoBotChannelTradingDataKeys.EXCHANGE_ID.value])

    async def _subscribe_exchange_id_mark_price(self, exchange_id):
        await exchanges_channel.get_chan(trading_constants.MARK_PRICE_CHANNEL, exchange_id).new_consumer(
            self._mark_price_callback,
            symbol=self.trading_mode.symbol
        )
        registered_exchange_name = trading_api.get_exchange_name(
            trading_api.get_exchange_manager_from_exchange_id(exchange_id)
        )
        self.logger.info(
            f"Arbitrage trading for {self.trading_mode.symbol} on {self.exchange_name}: registered "
            f"{registered_exchange_name} exchange as price data feed reference to identify arbitrage opportunities."
        )

    async def set_final_eval(self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame, trigger_source: str):
        # Ignore matrix calls
        pass

    @classmethod
    def get_should_cancel_loaded_orders(cls) -> bool:
        return False

    async def stop(self):
        if self.trading_mode is not None:
            self.trading_mode.flush_trading_mode_consumers()
        await super().stop()
