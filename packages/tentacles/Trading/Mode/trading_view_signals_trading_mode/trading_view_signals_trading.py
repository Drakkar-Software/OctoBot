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
import math
import typing
import json
import copy
import enum

import async_channel.channels as channels
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.signals as commons_signals
import octobot_commons.tentacles_management as tentacles_management
import octobot_services.api as services_api
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.modes as trading_modes
import octobot_trading.errors as trading_errors
import octobot_trading.modes.script_keywords as script_keywords
import octobot_trading.api as trading_api
try:
    import tentacles.Services.Services_feeds.trading_view_service_feed as trading_view_service_feed
except ImportError:
    if commons_constants.USE_MINIMAL_LIBS:
        # mock trading_view_service_feed imports
        class TradingViewServiceFeedImportMock:
            class TradingViewServiceFeed:
                def get_name(self, *args, **kwargs):
                    raise ImportError("trading_view_service_feed not installed")
    trading_view_service_feed = TradingViewServiceFeedImportMock()
import tentacles.Trading.Mode.daily_trading_mode.daily_trading as daily_trading_mode
import tentacles.Trading.Mode.trading_view_signals_trading_mode.actions_params as actions_params
import tentacles.Trading.Mode.trading_view_signals_trading_mode.errors as trading_view_signals_trading_mode_errors
import tentacles.Meta.Keywords.scripting_library as scripting_library


_CANCEL_POLICIES_CACHE = {}


class SignalActions(enum.Enum):
    CREATE_ORDERS = "create_orders"
    CANCEL_ORDERS = "cancel_orders"
    ENSURE_EXCHANGE_BALANCE = "ensure_exchange_balance"
    ENSURE_BLOCKCHAIN_WALLET_BALANCE = "ensure_blockchain_wallet_balance"
    NO_ACTION = "no_action"
    WITHDRAW_FUNDS = "withdraw_funds"  # requires ALLOW_FUNDS_TRANSFER env to be True (disabled by default to protect funds)
    TRANSFER_FUNDS = "transfer_funds"  # requires ALLOW_FUNDS_TRANSFER env to be True (disabled by default to protect funds)


class TradingViewSignalsTradingMode(trading_modes.AbstractTradingMode):
    SERVICE_FEED_CLASS = trading_view_service_feed.TradingViewServiceFeed if hasattr(trading_view_service_feed, 'TradingViewServiceFeed') else None
    TRADINGVIEW_FUTURES_SUFFIXES = [".P"]
    PARAM_SEPARATORS = [";", "\\n", "\n"]
    GENERIC_USD_STABLECOIN_SYMBOL = "USD*"

    EXCHANGE_KEY = "EXCHANGE"
    TRADING_TYPE_KEY = "TRADING_TYPE"   # expect a trading_enums.ExchangeTypes value
    SYMBOL_KEY = "SYMBOL"
    SIGNAL_KEY = "SIGNAL"
    PRICE_KEY = "PRICE"
    VOLUME_KEY = "VOLUME"
    REDUCE_ONLY_KEY = "REDUCE_ONLY"
    ORDER_TYPE_SIGNAL = "ORDER_TYPE"
    STOP_PRICE_KEY = "STOP_PRICE"
    TAG_KEY = "TAG"
    EXCHANGE_ORDER_IDS = "EXCHANGE_ORDER_IDS"
    LEVERAGE = "LEVERAGE"
    TAKE_PROFIT_PRICE_KEY = "TAKE_PROFIT_PRICE"
    TAKE_PROFIT_VOLUME_RATIO_KEY = "TAKE_PROFIT_VOLUME_RATIO"
    ALLOW_HOLDINGS_ADAPTATION_KEY = "ALLOW_HOLDINGS_ADAPTATION"
    TRAILING_PROFILE = "TRAILING_PROFILE"
    CANCEL_POLICY = "CANCEL_POLICY"
    CANCEL_POLICY_PARAMS = "CANCEL_POLICY_PARAMS"
    PARAM_PREFIX_KEY = "PARAM_"
    BUY_SIGNAL = "buy"
    SELL_SIGNAL = "sell"
    MARKET_SIGNAL = "market"
    LIMIT_SIGNAL = "limit"
    STOP_SIGNAL = "stop"
    CANCEL_SIGNAL = "cancel"
    SIDE_PARAM_KEY = "SIDE"
    # special signals, to be used programmatically
    ENSURE_EXCHANGE_BALANCE_SIGNAL = "ensure_exchange_balance"
    ENSURE_BLOCKCHAIN_WALLET_BALANCE_SIGNAL = "ensure_blockchain_wallet_balance"
    WITHDRAW_FUNDS_SIGNAL = "withdraw_funds" # disabled by default unless ALLOW_FUNDS_TRANSFER is True
    TRANSFER_FUNDS_SIGNAL = "transfer_funds" # disabled by default unless ALLOW_FUNDS_TRANSFER is True

    NON_ORDER_SIGNALS = {
        # signals that are not related to order management
        # they will be only be processed by the 1st trading mode on this matrix  
        ENSURE_EXCHANGE_BALANCE_SIGNAL,
        ENSURE_BLOCKCHAIN_WALLET_BALANCE_SIGNAL,
        WITHDRAW_FUNDS_SIGNAL,
        TRANSFER_FUNDS_SIGNAL,
    }
    META_ACTION_ONLY_SIGNALS = set()

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.USE_MARKET_ORDERS = True
        self.CANCEL_PREVIOUS_ORDERS = True
        self.merged_simple_symbol = None
        self.str_symbol = None

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        self.UI.user_input(
            "use_maximum_size_orders", commons_enums.UserInputTypes.BOOLEAN, False, inputs,
            title="All in trades: Trade with all available funds at each order.",
        )
        self.USE_MARKET_ORDERS = self.UI.user_input(
            "use_market_orders", commons_enums.UserInputTypes.BOOLEAN, True, inputs,
            title="Use market orders: If enabled, placed orders will be market orders only. Otherwise order prices "
                  "are set using the Fixed limit prices difference value.",
        )
        self.UI.user_input(
            "close_to_current_price_difference", commons_enums.UserInputTypes.FLOAT, 0.005, inputs,
            min_val=0,
            title="Fixed limit prices difference: Difference to take into account when placing a limit order "
                  "(used if fixed limit prices is enabled). For a 200 USD price and 0.005 in difference: "
                  "buy price would be 199 and sell price 201.",
        )
        self.CANCEL_PREVIOUS_ORDERS = self.UI.user_input(
            "cancel_previous_orders", commons_enums.UserInputTypes.BOOLEAN, True, inputs,
            title="Cancel previous orders: If enabled, cancel other orders associated to the same symbol when "
                  "receiving a signal. This way, only the latest signal will be taken into account.",
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
               self.producers[0].final_eval

    def get_mode_producer_classes(self) -> list:
        return [TradingViewSignalsModeProducer]

    def get_mode_consumer_classes(self) -> list:
        return [TradingViewSignalsModeConsumer]

    async def _get_feed_consumers(self):
        parsed_symbol = symbol_util.parse_symbol(self.symbol)
        self.str_symbol = str(parsed_symbol)
        self.merged_simple_symbol = parsed_symbol.merged_str_base_and_quote_only_symbol(market_separator="")
        feed_consumer = []
        if self.SERVICE_FEED_CLASS is None:
            if commons_constants.USE_MINIMAL_LIBS:
                self.logger.debug(
                    "Trading view service feed not installed, this trading mode won't be listening to trading view signals."
                )
            else:
                raise ImportError("TradingViewServiceFeed not installed")
        else:
            service_feed = services_api.get_service_feed(self.SERVICE_FEED_CLASS, self.bot_id)
            if service_feed is not None:
                feed_consumer = [await channels.get_chan(service_feed.FEED_CHANNEL.get_name()).new_consumer(
                    self._trading_view_signal_callback
                )]
            else:
                self.logger.error("Impossible to find the Trading view service feed, this trading mode can't work.")
        return feed_consumer

    async def create_consumers(self) -> list:
        consumers = await super().create_consumers()
        return consumers + await self._get_feed_consumers()

    @classmethod
    def _adapt_symbol(cls, parsed_data, exchange_name: typing.Optional[str]):
        if cls.SYMBOL_KEY not in parsed_data:
            return
        symbol = parsed_data[cls.SYMBOL_KEY]
        for suffix in cls.TRADINGVIEW_FUTURES_SUFFIXES:
            if symbol.endswith(suffix):
                parsed_data[cls.SYMBOL_KEY] = symbol.split(suffix)[0]
                break
        if exchange_name and cls.GENERIC_USD_STABLECOIN_SYMBOL in parsed_data[cls.SYMBOL_KEY]:
            # replace the generic USD stablecoin symbol with the actual stablecoin symbol for this exchange
            default_reference_market = scripting_library.get_default_exchange_reference_market(exchange_name)
            replaced_symbol = parsed_data[cls.SYMBOL_KEY].replace(cls.GENERIC_USD_STABLECOIN_SYMBOL, default_reference_market)
            commons_logging.get_logger(cls.__name__).info(
                f"Replaced generic USD stablecoin symbol {parsed_data[cls.SYMBOL_KEY]} with {replaced_symbol} for exchange {exchange_name} in signal data: {parsed_data}"
            )
            parsed_data[cls.SYMBOL_KEY] = replaced_symbol
        

    @classmethod
    def parse_signal_data(
        cls, signal_data: typing.Union[str, dict], exchange_name: typing.Optional[str], errors: list
    ) -> dict:
        if isinstance(signal_data, dict):
            # already parsed: return a deep copy to avoid modifying the original data
            return copy.deepcopy(signal_data)
        parsed_data = {}
        # replace all split char by a single one
        splittable_data = signal_data
        final_split_char = cls.PARAM_SEPARATORS[0]
        for split_char in cls.PARAM_SEPARATORS[1:]:
            splittable_data = splittable_data.replace(split_char, final_split_char)
        for line in splittable_data.split(final_split_char):
            if not line.strip():
                # ignore empty lines
                continue
            values = line.split("=")
            try:
                value = values[1].strip()
                # restore booleans
                lower_val = value.lower()
                if lower_val in ("true", "false"):
                    value = lower_val == "true"
                parsed_data[values[0].strip()] = value
            except IndexError:
                errors.append(f"Invalid signal line in trading view signal, ignoring it. Line: \"{line}\"")

        cls._adapt_symbol(parsed_data, exchange_name)
        return parsed_data


    @classmethod
    def is_compatible_trading_type(cls, parsed_signal: dict, trading_type: trading_enums.ExchangeTypes) -> bool:
        if parsed_trading_type := parsed_signal.get(cls.TRADING_TYPE_KEY):
            return parsed_trading_type == trading_type.value
        return True

    def _log_error_message_if_relevant(self, parsed_data: dict, signal_data: str):
        # only log error messages on one TradingViewSignalsTradingMode instance to avoid logging errors multiple times
        if self.is_first_trading_mode_on_this_matrix():
            all_trading_modes = trading_modes.get_trading_modes_of_this_type_on_this_matrix(self)
            # Can log error message: this is the first trading mode on this matrix. 
            # Each is notified by signals and only this one will log errors to avoid duplicating logs
            if not any(
                trading_mode.is_relevant_signal(parsed_data)
                for trading_mode in all_trading_modes
            ):
                # only log error if the signal is not relevant to any other trading mode on this matrix
                enabled_exchanges = set()
                enabled_symbols = set()
                for trading_mode in all_trading_modes:
                    enabled_exchanges.add(trading_mode.exchange_manager.exchange_name)
                    enabled_symbols.add(f"{trading_mode.str_symbol} (or {self.merged_simple_symbol})")
                self.logger.error(
                    f"Ignored TradingView alert - unrelated to profile exchanges: {', '.join(enabled_exchanges)} and symbols: {', '.join(enabled_symbols)} (alert: {signal_data})"
                )

    def is_relevant_signal(self, parsed_data: dict) -> bool:
        if not self.is_compatible_trading_type(parsed_data, trading_exchanges.get_exchange_type(self.exchange_manager)):
            return False
        elif parsed_data[self.EXCHANGE_KEY].lower() not in self.exchange_manager.exchange_name:
            return False
        elif parsed_data[self.SYMBOL_KEY] not in (self.merged_simple_symbol, self.str_symbol):
            return False
        return True

    @classmethod
    def get_signal(cls, parsed_data: dict) -> str:
        return parsed_data.get(cls.SIGNAL_KEY, "").casefold()

    @classmethod
    def is_non_order_signal(cls, parsed_data: dict) -> bool:
        try:
            return cls.get_signal(parsed_data) in cls.NON_ORDER_SIGNALS
        except KeyError:
            return False

    @classmethod
    def is_meta_action_only(cls, parsed_data: dict) -> bool:
        return cls.get_signal(parsed_data) in cls.META_ACTION_ONLY_SIGNALS

    async def _process_or_ignore_non_order_signal(self, parsed_data: dict) -> bool:
        if self.is_non_order_signal(parsed_data):
            if self.is_first_trading_mode_on_this_matrix():
                self.logger.info(f"Non order signal {parsed_data[self.SIGNAL_KEY]} processing")
                await self.producers[0].signal_callback(parsed_data, script_keywords.get_base_context(self))
            else:
                self.logger.info(f"Non order signal {parsed_data[self.SIGNAL_KEY]} ignored: another trading mode on this matrix will process it")
            return True
        return False

    async def _trading_view_signal_callback(self, data):
        signal_data = data.get("metadata", "")
        errors = []
        parsed_data = self.parse_signal_data(signal_data, self.exchange_manager.exchange_name, errors)
        for error in errors:
            self.logger.error(error)
        try:
            if self.is_relevant_signal(parsed_data):
                await self.producers[0].signal_callback(parsed_data, script_keywords.get_base_context(self))
            else:
                self._log_error_message_if_relevant(parsed_data, signal_data)
        except (
            trading_errors.InvalidArgumentError,
            trading_errors.InvalidCancelPolicyError,
            trading_errors.ConfigurationPermissionError,
            trading_errors.TraderDisabledError,
        ) as e:
            self.logger.error(f"Error when processing trading view signal: {e} (signal: {signal_data})")
        except trading_errors.MissingFunds as e:
            self.logger.error(f"Error when processing trading view signal: not enough funds: {e} (signal: {signal_data})")
        except KeyError as e:
            if not await self._process_or_ignore_non_order_signal(parsed_data):
                self.logger.error(f"Error when processing trading view signal: missing {e} required value (signal: {signal_data})")
        except Exception as e:
            self.logger.error(
                f"Unexpected error when processing trading view signal: {e} {e.__class__.__name__} (signal: {signal_data})"
            )

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return False

    @staticmethod
    def is_backtestable():
        return False


class TradingViewSignalsModeConsumer(daily_trading_mode.DailyTradingModeConsumer):
    def __init__(self, trading_mode):
        super().__init__(trading_mode)
        self.QUANTITY_MIN_PERCENT = decimal.Decimal(str(0.1))
        self.QUANTITY_MAX_PERCENT = decimal.Decimal(str(0.9))

        self.QUANTITY_MARKET_MIN_PERCENT = decimal.Decimal(str(0.5))
        self.QUANTITY_MARKET_MAX_PERCENT = trading_constants.ONE
        self.QUANTITY_BUY_MARKET_ATTENUATION = decimal.Decimal(str(0.2))

        self.BUY_LIMIT_ORDER_MAX_PERCENT = decimal.Decimal(str(0.995))
        self.BUY_LIMIT_ORDER_MIN_PERCENT = decimal.Decimal(str(0.99))

        self.USE_CLOSE_TO_CURRENT_PRICE = True
        self.CLOSE_TO_CURRENT_PRICE_DEFAULT_RATIO = decimal.Decimal(str(trading_mode.trading_config.get("close_to_current_price_difference",
                                                                                    0.02)))
        self.BUY_WITH_MAXIMUM_SIZE_ORDERS = trading_mode.trading_config.get("use_maximum_size_orders", False)
        self.SELL_WITH_MAXIMUM_SIZE_ORDERS = trading_mode.trading_config.get("use_maximum_size_orders", False)
        self.USE_STOP_ORDERS = False


class TradingViewSignalsModeProducer(daily_trading_mode.DailyTradingModeProducer):
    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        self.EVAL_BY_STATES = {
            trading_enums.EvaluatorStates.LONG: -0.6,
            trading_enums.EvaluatorStates.SHORT: 0.6,
            trading_enums.EvaluatorStates.VERY_LONG: -1,
            trading_enums.EvaluatorStates.VERY_SHORT: 1,
            trading_enums.EvaluatorStates.NEUTRAL: 0,
        }

    def get_channels_registration(self):
        # do not register on matrix or candles channels
        return []

    async def set_final_eval(self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame, trigger_source: str):
        # Ignore matrix calls
        pass

    def _parse_pre_update_order_details(self, parsed_data):
        return {
            TradingViewSignalsModeConsumer.LEVERAGE:
                parsed_data.get(TradingViewSignalsTradingMode.LEVERAGE, None),
        }

    async def _parse_order_details(self, ctx, parsed_data) -> tuple[SignalActions, trading_enums.EvaluatorStates, dict]:
        signal = parsed_data[TradingViewSignalsTradingMode.SIGNAL_KEY].casefold()
        order_type = parsed_data.get(TradingViewSignalsTradingMode.ORDER_TYPE_SIGNAL, "").casefold()
        order_exchange_creation_params = {
            param_name.split(TradingViewSignalsTradingMode.PARAM_PREFIX_KEY)[1]: param_value
            for param_name, param_value in parsed_data.items()
            if param_name.startswith(TradingViewSignalsTradingMode.PARAM_PREFIX_KEY)
        }
        parsed_side = None
        action = None
        if signal == TradingViewSignalsTradingMode.SELL_SIGNAL:
            action = SignalActions.CREATE_ORDERS
            parsed_side = trading_enums.TradeOrderSide.SELL.value
            if order_type == TradingViewSignalsTradingMode.MARKET_SIGNAL:
                state = trading_enums.EvaluatorStates.VERY_SHORT
            elif order_type in (TradingViewSignalsTradingMode.LIMIT_SIGNAL, TradingViewSignalsTradingMode.STOP_SIGNAL):
                state = trading_enums.EvaluatorStates.SHORT
            else:
                state = trading_enums.EvaluatorStates.VERY_SHORT if self.trading_mode.USE_MARKET_ORDERS \
                    else trading_enums.EvaluatorStates.SHORT
        elif signal == TradingViewSignalsTradingMode.BUY_SIGNAL:
            action = SignalActions.CREATE_ORDERS
            parsed_side = trading_enums.TradeOrderSide.BUY.value
            if order_type == TradingViewSignalsTradingMode.MARKET_SIGNAL:
                state = trading_enums.EvaluatorStates.VERY_LONG
            elif order_type in (TradingViewSignalsTradingMode.LIMIT_SIGNAL, TradingViewSignalsTradingMode.STOP_SIGNAL):
                state = trading_enums.EvaluatorStates.LONG
            else:
                state = trading_enums.EvaluatorStates.VERY_LONG if self.trading_mode.USE_MARKET_ORDERS \
                    else trading_enums.EvaluatorStates.LONG
        else:
            state = trading_enums.EvaluatorStates.NEUTRAL
            if signal == TradingViewSignalsTradingMode.CANCEL_SIGNAL:
                action = SignalActions.CANCEL_ORDERS
            elif signal == TradingViewSignalsTradingMode.ENSURE_EXCHANGE_BALANCE_SIGNAL:
                action = SignalActions.ENSURE_EXCHANGE_BALANCE
            elif signal == TradingViewSignalsTradingMode.ENSURE_BLOCKCHAIN_WALLET_BALANCE_SIGNAL:
                action = SignalActions.ENSURE_BLOCKCHAIN_WALLET_BALANCE
            elif signal == TradingViewSignalsTradingMode.WITHDRAW_FUNDS_SIGNAL:
                if not trading_constants.ALLOW_FUNDS_TRANSFER:
                    raise trading_errors.DisabledFundsTransferError(
                        "Withdraw funds signal is not allowed when ALLOW_FUNDS_TRANSFER is disabled"
                    )
                action = SignalActions.WITHDRAW_FUNDS
            elif signal == TradingViewSignalsTradingMode.TRANSFER_FUNDS_SIGNAL:
                if not trading_constants.ALLOW_FUNDS_TRANSFER:
                    raise trading_errors.DisabledFundsTransferError(
                        "Transfer funds signal is not allowed when ALLOW_FUNDS_TRANSFER is disabled"
                    )
                action = SignalActions.TRANSFER_FUNDS
        if action is None:
            raise trading_errors.InvalidArgumentError(
                f"Unknown signal: {parsed_data[TradingViewSignalsTradingMode.SIGNAL_KEY]}, full data= {parsed_data}"
            )
        target_price = 0 if order_type == TradingViewSignalsTradingMode.MARKET_SIGNAL else (
            await self._parse_element(ctx, parsed_data, TradingViewSignalsTradingMode.PRICE_KEY, 0, True))
        stop_price = await self._parse_element(
            ctx, parsed_data, TradingViewSignalsTradingMode.STOP_PRICE_KEY, math.nan, True
        )
        tp_price = await self._parse_element(
            ctx, parsed_data, TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY, math.nan, True
        )
        additional_tp_volume_ratios = []
        if first_volume := await self._parse_element(
            ctx, parsed_data, TradingViewSignalsTradingMode.TAKE_PROFIT_VOLUME_RATIO_KEY, 0, False
        ):
            additional_tp_volume_ratios.append(first_volume)
        additional_tp_prices = await self._parse_additional_decimal_elements(
            ctx, parsed_data, f"{TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY}_", math.nan, True
        )
        additional_tp_volume_ratios += await self._parse_additional_decimal_elements(
            ctx, parsed_data, f"{TradingViewSignalsTradingMode.TAKE_PROFIT_VOLUME_RATIO_KEY}_", 0, False
        )
        allow_holdings_adaptation = parsed_data.get(TradingViewSignalsTradingMode.ALLOW_HOLDINGS_ADAPTATION_KEY, False)
        reduce_only = parsed_data.get(TradingViewSignalsTradingMode.REDUCE_ONLY_KEY, False)
        amount = await self._parse_volume(
            ctx, parsed_data, parsed_side, target_price, allow_holdings_adaptation, reduce_only
        )
        trailing_profile = parsed_data.get(TradingViewSignalsTradingMode.TRAILING_PROFILE)
        maybe_cancel_policy, cancel_policy_params = self._parse_cancel_policy(parsed_data)
        order_data = {
            TradingViewSignalsModeConsumer.PRICE_KEY: target_price,
            TradingViewSignalsModeConsumer.VOLUME_KEY: amount,
            TradingViewSignalsModeConsumer.STOP_PRICE_KEY: stop_price,
            TradingViewSignalsModeConsumer.STOP_ONLY: order_type == TradingViewSignalsTradingMode.STOP_SIGNAL,
            TradingViewSignalsModeConsumer.TAKE_PROFIT_PRICE_KEY: tp_price,
            TradingViewSignalsModeConsumer.ADDITIONAL_TAKE_PROFIT_PRICES_KEY: additional_tp_prices,
            TradingViewSignalsModeConsumer.ADDITIONAL_TAKE_PROFIT_VOLUME_RATIOS_KEY: additional_tp_volume_ratios,
            TradingViewSignalsModeConsumer.REDUCE_ONLY_KEY: reduce_only,
            TradingViewSignalsModeConsumer.TAG_KEY:
                parsed_data.get(TradingViewSignalsTradingMode.TAG_KEY, None),
            TradingViewSignalsModeConsumer.TRAILING_PROFILE: trailing_profile.casefold() if trailing_profile else None,
            TradingViewSignalsModeConsumer.CANCEL_POLICY: maybe_cancel_policy,
            TradingViewSignalsModeConsumer.CANCEL_POLICY_PARAMS: cancel_policy_params,
            TradingViewSignalsModeConsumer.EXCHANGE_ORDER_IDS:
                parsed_data.get(TradingViewSignalsTradingMode.EXCHANGE_ORDER_IDS, None),
            TradingViewSignalsModeConsumer.LEVERAGE:
                parsed_data.get(TradingViewSignalsTradingMode.LEVERAGE, None),
            TradingViewSignalsModeConsumer.ORDER_EXCHANGE_CREATION_PARAMS: order_exchange_creation_params,
        }
        return action, state, order_data

    def _parse_cancel_policy(self, parsed_data):
        if policy := parsed_data.get(TradingViewSignalsTradingMode.CANCEL_POLICY, None):
            lowercase_policy = policy.casefold()
            if not _CANCEL_POLICIES_CACHE:
                _CANCEL_POLICIES_CACHE.update({
                    policy.__name__.casefold(): policy.__name__
                    for policy in tentacles_management.get_all_classes_from_parent(trading_personal_data.OrderCancelPolicy)
                })
            try:
                policy_class = _CANCEL_POLICIES_CACHE[lowercase_policy]
                policy_params = parsed_data.get(TradingViewSignalsTradingMode.CANCEL_POLICY_PARAMS)
                parsed_policy_params = json.loads(policy_params.replace("'", '"')) if isinstance(policy_params, str) else policy_params
                return policy_class, parsed_policy_params
            except KeyError:
                raise trading_errors.InvalidCancelPolicyError(
                    f"Unknown cancel policy: {policy}. Available policies: {', '.join(_CANCEL_POLICIES_CACHE.keys())}"
                )

        return None, None

    async def _parse_additional_decimal_elements(self, ctx, parsed_data, element_prefix, default, is_price):
        values: list[decimal.Decimal] = []
        for key, value in parsed_data.items():
            if key.startswith(element_prefix) and len(key.split(element_prefix)) == 2:
                values.append(await self._parse_element(ctx, parsed_data, key, default, is_price))
        return values

    async def _parse_element(self, ctx, parsed_data, key, default, is_price)-> decimal.Decimal:
        target_value = decimal.Decimal(str(default))
        value = parsed_data.get(key, 0)
        if is_price:
            if input_price_or_offset := value:
                target_value = await script_keywords.get_price_with_offset(
                    ctx, input_price_or_offset, use_delta_type_as_flat_value=True
                )
        else:
            target_value = decimal.Decimal(str(value))
        return target_value

    async def _parse_volume(self, ctx, parsed_data, side, target_price, allow_holdings_adaptation, reduce_only):
        user_volume = str(parsed_data.get(TradingViewSignalsTradingMode.VOLUME_KEY, 0))
        if user_volume == "0":
            return trading_constants.ZERO
        return await script_keywords.get_amount_from_input_amount(
            context=ctx,
            input_amount=user_volume,
            side=side,
            reduce_only=reduce_only,
            is_stop_order=False,
            use_total_holding=False,
            target_price=target_price,
            # raise when not enough funds to create an order according to user input
            allow_holdings_adaptation=allow_holdings_adaptation,
        )

    @trading_modes.enabled_trader_only(raise_when_disabled=True)
    async def signal_callback(self, parsed_data: dict, ctx):
        _, dependencies = await self.apply_cancel_policies()
        is_order_signal = not self.trading_mode.is_non_order_signal(parsed_data)
        if is_order_signal and self.trading_mode.CANCEL_PREVIOUS_ORDERS:
            # cancel open orders
            _, new_dependencies = await self.cancel_symbol_open_orders(self.trading_mode.symbol)
            if new_dependencies:
                if dependencies:
                    dependencies.extend(new_dependencies)
                else:
                    dependencies = new_dependencies
        pre_update_data = self._parse_pre_update_order_details(parsed_data)
        await self._process_pre_state_update_actions(ctx, pre_update_data)
        await self._process_meta_actions(parsed_data)
        if self.trading_mode.is_meta_action_only(parsed_data):
            return
        action, state, order_data = await self._parse_order_details(ctx, parsed_data)
        self.final_eval = self.EVAL_BY_STATES[state]
        # Use daily trading mode state system
        await self._set_state(
            self.trading_mode.cryptocurrency, ctx.symbol, action, state, order_data, parsed_data, dependencies=dependencies
        )

    async def _process_pre_state_update_actions(self, context, data: dict):
        try:
            if leverage := data.get(TradingViewSignalsModeConsumer.LEVERAGE):
                await self.trading_mode.set_leverage(context.symbol, None, decimal.Decimal(str(leverage)))
        except Exception as err:
            self.logger.exception(
                err, True, f"Error when processing pre_state_update_actions: {err} (data: {data})"
            )

    async def _process_meta_actions(self, parsed_data: dict):
        # implement in subclass if needed
        pass

    async def _set_state(
        self, cryptocurrency: str, symbol: str, action: SignalActions,
        new_state: trading_enums.EvaluatorStates, order_data: dict, parsed_data: dict, 
        dependencies: typing.Optional[commons_signals.SignalDependencies] = None
    ):
        async with self.trading_mode_trigger():
            if self.state != new_state:
                self.state = new_state
                self.logger.info(f"[{symbol}] new state: {self.state.name}")

            # if new state is not neutral --> cancel orders and create new else keep orders
            if action == SignalActions.CREATE_ORDERS:
                # call orders creation from consumers
                await self.submit_trading_evaluation(cryptocurrency=cryptocurrency,
                                                     symbol=symbol,
                                                     time_frame=None,
                                                     final_note=self.final_eval,
                                                     state=self.state,
                                                     data=order_data,
                                                     dependencies=dependencies)

                # send_notification
                if not self.exchange_manager.is_backtesting:
                    await self._send_alert_notification(symbol, new_state)
            else:
                await self.process_non_creating_orders_actions(action, symbol, order_data, parsed_data)

    async def process_non_creating_orders_actions(
        self, action: SignalActions, symbol: str, order_data: dict, parsed_data: dict
    ):
        match (action):
            case SignalActions.CANCEL_ORDERS:
                await self.cancel_orders_from_order_data(symbol, order_data, parsed_data)
            case SignalActions.ENSURE_EXCHANGE_BALANCE:
                await self.ensure_exchange_balance(parsed_data)
            case SignalActions.ENSURE_BLOCKCHAIN_WALLET_BALANCE:
                await self.ensure_blockchain_wallet_balance(parsed_data)
            case SignalActions.WITHDRAW_FUNDS:
                await self.withdraw_funds(parsed_data)
            case SignalActions.TRANSFER_FUNDS:
                await self.transfer_funds(parsed_data)
            case _:
                raise trading_errors.InvalidArgumentError(f"Unknown action: {action}.")

    async def cancel_orders_from_order_data(self, symbol: str, order_data: dict, parsed_data: dict) -> tuple[bool, typing.Optional[commons_signals.SignalDependencies]]:
        if not self.trading_mode.consumers:
            return False, None

        exchange_ids = order_data.get(TradingViewSignalsModeConsumer.EXCHANGE_ORDER_IDS, None)
        cancel_order_raw_side = order_data.get(
            TradingViewSignalsModeConsumer.ORDER_EXCHANGE_CREATION_PARAMS, {}
        ).get(TradingViewSignalsTradingMode.SIDE_PARAM_KEY, None) or parsed_data.get(TradingViewSignalsTradingMode.SIDE_PARAM_KEY, None)
        cancel_order_raw_side = cancel_order_raw_side.lower() if cancel_order_raw_side else None
        cancel_order_side = trading_enums.TradeOrderSide.BUY if cancel_order_raw_side == trading_enums.TradeOrderSide.BUY.value \
            else trading_enums.TradeOrderSide.SELL if cancel_order_raw_side == trading_enums.TradeOrderSide.SELL.value else None
        cancel_order_tag = order_data.get(TradingViewSignalsModeConsumer.TAG_KEY, None)

        # cancel open orders
        return await self.cancel_symbol_open_orders(
            symbol, side=cancel_order_side, tag=cancel_order_tag, exchange_order_ids=exchange_ids
        )

    async def ensure_exchange_balance(self, parsed_data: dict) -> decimal.Decimal:
        ensure_exchange_balance_params = actions_params.EnsureExchangeBalanceParams.from_dict(parsed_data)
        holdings = trading_api.get_portfolio_currency(self.exchange_manager, ensure_exchange_balance_params.asset).available
        if holdings < decimal.Decimal(str(ensure_exchange_balance_params.holdings)):
            raise trading_view_signals_trading_mode_errors.MissingFundsError(
                f"Not enough {ensure_exchange_balance_params.asset} available on {self.exchange_manager.exchange_name} exchange account: available: {holdings}, required: {ensure_exchange_balance_params.holdings}"
            )
        else:
            self.logger.info(
                f"Enough {ensure_exchange_balance_params.asset} available on {self.exchange_manager.exchange_name} exchange account: available: {holdings}, required: {ensure_exchange_balance_params.holdings}"
            )
        return holdings

    async def ensure_blockchain_wallet_balance(self, parsed_data: dict) -> decimal.Decimal:
        ensure_blockchain_wallet_balance_params = actions_params.EnsureBlockchainWalletBalanceParams.from_dict(parsed_data)
        async with trading_api.blockchain_wallet_context(
            ensure_blockchain_wallet_balance_params.wallet_details, 
            self.exchange_manager.trader
        ) as wallet:
            wallet_balance = await wallet.get_balance()
        balance = wallet_balance[ensure_blockchain_wallet_balance_params.asset][
            trading_constants.CONFIG_PORTFOLIO_FREE
        ] if ensure_blockchain_wallet_balance_params.asset in wallet_balance else trading_constants.ZERO

        if balance < decimal.Decimal(str(ensure_blockchain_wallet_balance_params.holdings)):
            raise trading_view_signals_trading_mode_errors.MissingFundsError(
                f"Not enough {ensure_blockchain_wallet_balance_params.asset} available on "
                f"{ensure_blockchain_wallet_balance_params.wallet_details.blockchain_descriptor.network} "
                f"blockchain wallet: available: {balance}, required: {ensure_blockchain_wallet_balance_params.holdings}"
            )
        else:
            self.logger.info(
                f"Enough {ensure_blockchain_wallet_balance_params.asset} available on "
                f"{ensure_blockchain_wallet_balance_params.wallet_details.blockchain_descriptor.network} "
                f"blockchain wallet: available: {balance}, required: {ensure_blockchain_wallet_balance_params.holdings}"
            )
        return balance

    async def withdraw_funds(self, parsed_data: dict) -> dict:
        withdraw_funds_params = actions_params.WithdrawFundsParams.from_dict(parsed_data)
        # requires ALLOW_FUNDS_TRANSFER env to be True (disabled by default to protect funds)
        amount = withdraw_funds_params.amount or (
            trading_api.get_portfolio_currency(self.exchange_manager, withdraw_funds_params.asset).available
        )
        transaction = await self.exchange_manager.trader.withdraw(
            withdraw_funds_params.asset,
            decimal.Decimal(str(amount)),
            withdraw_funds_params.network,
            withdraw_funds_params.address,
            tag=withdraw_funds_params.tag,
            params=withdraw_funds_params.params
        )
        self.logger.info(
            f"Withdrawn {amount} {withdraw_funds_params.asset} "
            f"from {self.exchange_manager.exchange_name}: {transaction}"
        )
        return transaction
    
    async def transfer_funds(self, parsed_data: dict) -> dict:
        transfer_funds_params = actions_params.TransferFundsParams.from_dict(parsed_data)
        async with trading_api.blockchain_wallet_context(
            transfer_funds_params.wallet_details, 
            self.exchange_manager.trader
        ) as wallet:
            if transfer_funds_params.address:
                address = transfer_funds_params.address
            elif transfer_funds_params.destination_exchange == self.exchange_manager.exchange_name:
                address = (
                    await self.exchange_manager.trader.get_deposit_address(transfer_funds_params.asset)
                )[trading_enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value]
            else:
                raise trading_errors.InvalidArgumentError(
                    f"Unsupported destination exchange: {transfer_funds_params.destination_exchange}"
                )
            # requires ALLOW_FUNDS_TRANSFER env to be True (disabled by default to protect funds)
            transaction = await wallet.withdraw(
                transfer_funds_params.asset,
                decimal.Decimal(str(transfer_funds_params.amount)),
                transfer_funds_params.wallet_details.blockchain_descriptor.network,
                address,
            )
        self.logger.info(f"Transferred {transfer_funds_params.amount} {transfer_funds_params.asset}: {transaction}")
        return transaction
