# pylint: disable=W0706
#  Drakkar-Software OctoBot-Trading
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
import enum
import typing

import octobot_commons.signals as commons_signals
import octobot_commons.symbols as symbol_util
import octobot_commons.constants as commons_constants

import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.exchanges
import octobot_trading.modes.channel as modes_channel
import octobot_trading.modes.mode_activity as mode_activity
import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.personal_data as personal_data
import octobot_trading.modes.abstract_trading_mode as abstract_trading_mode
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc


class AbstractTradingModeConsumer(modes_channel.ModeChannelConsumer):
    CREATE_ORDER_DATA_PARAM = "data"
    CREATE_ORDER_DEPENDENCIES_PARAM = "dependencies"
    
    def __init__(self, trading_mode):
        super().__init__()
        self.trading_mode: abstract_trading_mode.AbstractTradingMode = trading_mode
        self.exchange_manager: octobot_trading.exchanges.ExchangeManager = trading_mode.exchange_manager
        self.previous_call_error_per_symbol: dict[str, typing.Optional[Exception]] = {}    # stores the last order creation issue for symbol
        self.on_reload_config()

    def on_reload_config(self):
        """
        Called at constructor and after the associated trading mode's reload_config.
        Implement if necessary
        """

    def skip_portfolio_available_check_before_creating_orders(self) -> bool:
        """
        When returning true, will skip portfolio available funds check
        before calling self.create_new_orders().
        Override if necessary
        """
        return False

    def flush(self):
        self.trading_mode = None # type: ignore
        self.exchange_manager = None # type: ignore
        self.previous_call_error_per_symbol = None # type: ignore

    async def internal_callback(
        self, trading_mode_name, cryptocurrency, symbol, time_frame, final_note, state, 
        data, dependencies: typing.Optional[commons_signals.SignalDependencies] = None
    ):
        # creates a new order (or multiple split orders), always check self.can_create_order() first.
        try:
            await self.create_order_if_possible(
                symbol, final_note, state, data=data, dependencies=dependencies
            )
            self.previous_call_error_per_symbol[symbol] = None
        except errors.MissingMinimalExchangeTradeVolume as err:
            self.previous_call_error_per_symbol[symbol] = err
            self.logger.info(self.get_minimal_funds_error(symbol, final_note))
        except errors.UnhandledContractError as err:
            self.previous_call_error_per_symbol[symbol] = err
            self.logger.error(f"Unhandled contract error on {self.exchange_manager.exchange_name}: {err}. "
                              f"Please make sure that {symbol} is the full futures contract symbol. "
                              f"Future contract symbols contain the settlement currency after ':'. "
                              f"Example: use BTC/USDT:USDT for linear BTC/USDT contracts and "
                              f"BTC/USD:BTC for inverse BTC/USD contracts.")
        except (errors.InvalidPositionSide, errors.UnsupportedContractConfigurationError) as err:
            self.previous_call_error_per_symbol[symbol] = err
            self.logger.error(f"Impossible to create {symbol} order: {err}.")
        except errors.OrderCreationError as err:
            self.previous_call_error_per_symbol[symbol] = err
            self.logger.info(f"Failed {symbol} order creation on: {self.exchange_manager.exchange_name} "
                             f"an unexpected error happened when creating order. This is likely due to "
                             f"the order being refused by the exchange.")
        except errors.InvalidCancelPolicyError as err:
            self.previous_call_error_per_symbol[symbol] = err
            self.logger.error(f"Invalid cancel policy error on {self.exchange_manager.exchange_name}: {err}. "
                              f"Please make sure that the provided cancel policy is valid.")
        except errors.TraderDisabledError as err:
            self.previous_call_error_per_symbol[symbol] = err
            self.logger.error(f"Impossible to execution action on a disabled trader: {err}.")

    def get_minimal_funds_error(self, symbol, final_note):
        if symbol is None:
            return (
                f"Not enough funds to create new orders after {final_note} evaluation: "
                f"{self.exchange_manager.exchange_name} exchange minimal order "
                f"volume has not been reached."
            )
        else:
            market_status = self.exchange_manager.exchange.get_market_status(symbol, price_example=None, with_fixer=False)
            try:
                base, quote = symbol_util.parse_symbol(symbol).base_and_quote()
                portfolio = self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio
                funds = {
                    base: portfolio.get_currency_portfolio(base),
                    quote: portfolio.get_currency_portfolio(quote)
                }
            except Exception as err:
                self.logger.error(f"Error when getting funds for {symbol}: {err}")
                funds = {}
        return (
            f"Not enough funds to create a new {symbol} order after {final_note} evaluation: "
            f"{self.exchange_manager.exchange_name} exchange minimal order "
            f"volume has not been reached. Funds: {funds} "
            f"Exchanges requirements: {market_status.get(Ecmsc.LIMITS.value)}."
        )

    async def init_user_inputs(self, should_clear_inputs):
        pass

    async def create_new_orders(self, symbol, final_note, state, **kwargs):
        raise NotImplementedError("create_new_orders is not implemented")

    async def create_order_if_possible(self, symbol, final_note, state, **kwargs) -> list:
        """
        For each trader call the creator to check if order creation is possible and create it.
        Will retry once on failure
        :return: None
        """
        self.logger.debug(f"Entering create_order_if_possible for {symbol} on {self.exchange_manager.exchange_name}")
        try:
            async with self.trading_mode.remote_signal_publisher(symbol), \
                  self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.lock:
                if await self.can_create_order(symbol, state):
                    try:
                        return await self.create_new_orders(symbol, final_note, state, **kwargs)
                    except (
                        errors.MissingMinimalExchangeTradeVolume, errors.OrderCreationError,
                        errors.InvalidPositionSide, errors.UnsupportedContractConfigurationError, 
                        errors.InvalidCancelPolicyError, errors.TraderDisabledError
                    ):
                        raise
                    except errors.MissingFunds:
                        try:
                            self.logger.debug(f"Missing funds error: force refreshing portfolio")
                            # second chance: force portfolio update and retry
                            await exchange_channel.get_chan(constants.BALANCE_CHANNEL,
                                                            self.exchange_manager.id).get_internal_producer(). \
                                refresh_real_trader_portfolio(True)
                            self.logger.debug(f"Forced portfolio refresh success")
                            self.logger.debug(
                                f"Second call to self.create_new_orders with symbol: {symbol}, final_note: "
                                f"{final_note}, state: {state}, kwargs: {kwargs}"
                            )
                            return await self.create_new_orders(symbol, final_note, state, **kwargs)
                        except errors.MissingFunds as err:
                            self.previous_call_error_per_symbol[symbol] = err
                            self.logger.error(f"Failed to create {symbol} order on second attempt : {err})")
                    except Exception as err:
                        self.previous_call_error_per_symbol[symbol] = err
                        self.logger.exception(err, True, f"Error when creating {symbol} order: {err}")
            self.logger.info(f"Skipping order creation for {symbol} on {self.exchange_manager.exchange_name}: "
                             f"not enough available funds")
            return []
        finally:
            self.logger.debug(f"Exiting create_order_if_possible for {symbol}")

    # Can be overwritten
    async def can_create_order(self, symbol, state):
        if symbol is None or self.skip_portfolio_available_check_before_creating_orders():
            # should not check
            return True
        currency, market = symbol_util.parse_symbol(symbol).base_and_quote()
        portfolio = self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio

        # get symbol min amount when creating order
        symbol_limit = self.exchange_manager.exchange.get_market_status(symbol)[Ecmsc.LIMITS.value]
        symbol_min_amount = symbol_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MIN.value]
        order_min_amount = symbol_limit[Ecmsc.LIMITS_COST.value][Ecmsc.LIMITS_COST_MIN.value]

        if symbol_min_amount is None:
            symbol_min_amount = 0

        if self.exchange_manager.is_future:
            # future: need settlement asset and to take the open positions into account
            current_symbol_holding, _, market_quantity, current_price, _ = \
                await personal_data.get_pre_order_data(self.exchange_manager,
                                                       symbol=symbol,
                                                       timeout=constants.ORDER_DATA_FETCHING_TIMEOUT,
                                                       portfolio_type=commons_constants.PORTFOLIO_AVAILABLE)
            side = enums.TradeOrderSide.SELL \
                if state == enums.EvaluatorStates.VERY_SHORT.value or state == enums.EvaluatorStates.SHORT.value \
                else enums.TradeOrderSide.BUY
            max_order_size, _ = personal_data.get_futures_max_order_size(
                self.exchange_manager, symbol, side, current_price, False, current_symbol_holding, market_quantity
            )
            can_create_order = max_order_size > symbol_min_amount
            self.logger.debug(
                f"can_create_order: {can_create_order} [{symbol}] = "
                f"max_order_size > symbol_min_amount = {max_order_size} > {symbol_min_amount}"
            )
            return can_create_order

        # spot, trade asset directly
        # short cases => sell => need this currency
        if state == enums.EvaluatorStates.VERY_SHORT.value or state == enums.EvaluatorStates.SHORT.value:
            can_create_order = portfolio.get_currency_portfolio(currency).available > symbol_min_amount
            self.logger.debug(
                f"can_create_order: {can_create_order} [{symbol}] = "
                f"portfolio.get_currency_portfolio(currency).available > symbol_min_amount = "
                f"{portfolio.get_currency_portfolio(currency).available} > {symbol_min_amount}"
            )
            return can_create_order

        # long cases => buy => need money(aka other currency in the pair) to buy this currency
        elif state == enums.EvaluatorStates.LONG.value or state == enums.EvaluatorStates.VERY_LONG.value:
            can_create_order = portfolio.get_currency_portfolio(market).available > order_min_amount
            self.logger.debug(
                f"can_create_order: {can_create_order} [{symbol}] = "
                f"portfolio.get_currency_portfolio(market).available > order_min_amount = "
                f"{portfolio.get_currency_portfolio(market).available} > {order_min_amount}"
            )
            return can_create_order

        elif state == enums.EvaluatorStates.NEUTRAL.value:
            self.logger.debug(f"can_create_order: True. No check to perform for {state} state")
            return True

        # other cases like neutral state or unfulfilled previous conditions
        self.logger.debug("can_create_order: return False")
        return False

    def get_number_of_traded_assets(self):
        return len(self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder
                   .origin_crypto_currencies_values)

    def _update_producer_last_activity(self, activity_type: enum.Enum, reason):
        for producer in self.trading_mode.producers:
            if isinstance(producer, modes_channel.AbstractTradingModeProducer):
                if producer.last_activity is None:
                    producer.last_activity = mode_activity.TradingModeActivity(activity_type)
                else:
                    producer.last_activity.type = activity_type
                producer.last_activity.set_reason(reason)

    async def wait_for_active_position(self, symbol, timeout, side=None) -> bool:
        """
        Instantly return when the position is already active.
        Wait for the given timeout if the position is not active.
        :return: Return True when the position is active
        """
        if self.exchange_manager.is_backtesting:
            # never wait in backtesting
            return True
        if not self.exchange_manager.exchange.has_pair_contract(symbol):
            self.logger.error(f"Missing required contract for {symbol}")
            return False
        if not self.exchange_manager.exchange.get_pair_contract(symbol).is_one_way_position_mode() \
                and side is None:
            raise errors.NotSupported("The side parameter is required when dealing with non one-way contracts")
        position = self.exchange_manager.exchange_personal_data.positions_manager.get_symbol_position(
            symbol,
            side or enums.PositionSide.BOTH
        )
        if position.state is None:
            self.logger.error(f"Can't wait for active position: position state is unset for position: {position}")
            return False
        else:
            if not position.state.is_active():
                try:
                    self.logger.debug(f"Waiting for position idle to be active, position: {position}")
                    await position.state.wait_for_next_state(timeout)
                except asyncio.TimeoutError:
                    self.logger.debug(f"Timeout while waiting for idle position to be active, position: {position}")
        return position.state.is_active()

    async def register_chained_order(
        self, main_order, price, order_type, side, quantity=None, allow_bundling=True, tag=None, reduce_only=False,
        update_with_triggering_order_fees=None
    ) -> tuple:
        chained_order = personal_data.create_order_instance(
            trader=self.exchange_manager.trader,
            order_type=order_type,
            symbol=main_order.symbol,
            current_price=price,
            quantity=quantity or main_order.origin_quantity,
            price=price,
            side=side,
            associated_entry_id=main_order.order_id,
            reduce_only=reduce_only,
            tag=tag,
        )
        params = {}
        # do not reduce chained order amounts to account for fees when trading futures
        if update_with_triggering_order_fees is None:
            update_with_triggering_order_fees = not self.exchange_manager.is_future
        if allow_bundling:
            params = await self.exchange_manager.trader.bundle_chained_order_with_uncreated_order(
                main_order, chained_order, update_with_triggering_order_fees
            )
        else:
            await self.exchange_manager.trader.chain_order(
                main_order, chained_order, update_with_triggering_order_fees, False
            )
        return params, chained_order


def check_factor(min_val, max_val, factor):
    """
    Checks if factor is min_val < factor < max_val
    :param min_val:
    :param max_val:
    :param factor:
    :return:
    """
    if factor > max_val:
        return max_val
    if factor < min_val:
        return min_val
    return factor
