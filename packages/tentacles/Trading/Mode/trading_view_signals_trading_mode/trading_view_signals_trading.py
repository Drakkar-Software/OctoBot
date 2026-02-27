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
import typing
import copy
import enum

import async_channel.channels as channels
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.signals as commons_signals
import octobot_commons.errors as commons_errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_services.api as services_api
import octobot_trading.constants as trading_constants
import octobot_trading.blockchain_wallets as blockchain_wallets
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
import tentacles.Trading.Mode.dsl_trading_mode.dsl_trading as dsl_trading_mode
import tentacles.Trading.Mode.trading_view_signals_trading_mode.actions_params as actions_params
import tentacles.Trading.Mode.trading_view_signals_trading_mode.errors as trading_view_signals_trading_mode_errors
import tentacles.Meta.Keywords.scripting_library as scripting_library
import tentacles.Trading.Mode.trading_view_signals_trading_mode.tradingview_signal_to_dsl_translator as tradingview_signal_to_dsl_translator

_CANCEL_POLICIES_CACHE = {}


class SignalActions(enum.Enum):
    CREATE_ORDERS = "create_orders"
    CANCEL_ORDERS = "cancel_orders"
    ENSURE_EXCHANGE_BALANCE = "ensure_exchange_balance"
    ENSURE_BLOCKCHAIN_WALLET_BALANCE = "ensure_blockchain_wallet_balance"
    NO_ACTION = "no_action"
    WITHDRAW_FUNDS = "withdraw_funds"  # requires ALLOW_FUNDS_TRANSFER env to be True (disabled by default to protect funds)
    TRANSFER_FUNDS = "transfer_funds"  # requires ALLOW_FUNDS_TRANSFER env to be True (disabled by default to protect funds)


class TradingViewSignalsTradingMode(dsl_trading_mode.DSLTradingMode):
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
    ALLOW_HOLDINGS_ADAPTATION_KEY = "ALLOW_HOLDINGS_ADAPTATION"
    # special signals, to be used programmatically
    ENSURE_EXCHANGE_BALANCE_SIGNAL = "ensure_exchange_balance"
    ENSURE_BLOCKCHAIN_WALLET_BALANCE_SIGNAL = "ensure_blockchain_wallet_balance"
    WITHDRAW_FUNDS_SIGNAL = "withdraw_funds" # disabled by default unless ALLOW_FUNDS_TRANSFER is True
    TRANSFER_FUNDS_SIGNAL = "transfer_funds" # disabled by default unless ALLOW_FUNDS_TRANSFER is True

    TRADINGVIEW_TO_DSL_PARAM = {
        # translation of TradingView signal parameters to DSL keywords parameters
        SYMBOL_KEY: "symbol",
        VOLUME_KEY: "amount",
        PRICE_KEY: "price",
        REDUCE_ONLY_KEY: "reduce_only",
        TAG_KEY: "tag",
        STOP_PRICE_KEY: "stop_loss_price",
        TAKE_PROFIT_PRICE_KEY: "take_profit_prices",
        TAKE_PROFIT_VOLUME_RATIO_KEY: "take_profit_volume_percents",
        EXCHANGE_ORDER_IDS: "exchange_order_ids",
        SIDE_PARAM_KEY: "side",
        TRAILING_PROFILE: "trailing_profile",
        CANCEL_POLICY: "cancel_policy",
        CANCEL_POLICY_PARAMS: "cancel_policy_params",
        ALLOW_HOLDINGS_ADAPTATION_KEY: "allow_holdings_adaptation",
    }

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
    def _adapt_symbol(
        cls, parsed_data, exchange_name: typing.Optional[str],
        exchange_type: typing.Optional[trading_enums.ExchangeTypes], reference_market: typing.Optional[str]
    ):
        if cls.SYMBOL_KEY not in parsed_data:
            return
        symbol = parsed_data[cls.SYMBOL_KEY]
        for suffix in cls.TRADINGVIEW_FUTURES_SUFFIXES:
            if symbol.endswith(suffix):
                parsed_data[cls.SYMBOL_KEY] = symbol.split(suffix)[0]
                break
        if exchange_name and cls.GENERIC_USD_STABLECOIN_SYMBOL in parsed_data[cls.SYMBOL_KEY]:
            if exchange_type == trading_enums.ExchangeTypes.FUTURE and reference_market is not None:
                # futures: use the reference market value
                default_reference_market = reference_market
            else:
                # replace the generic USD stablecoin symbol with the actual stablecoin symbol for this exchange
                default_reference_market = scripting_library.get_default_exchange_reference_market(exchange_name)
            replaced_symbol = parsed_data[cls.SYMBOL_KEY].replace(cls.GENERIC_USD_STABLECOIN_SYMBOL, default_reference_market)
            commons_logging.get_logger(cls.__name__).info(
                f"Replaced generic USD stablecoin symbol {parsed_data[cls.SYMBOL_KEY]} with {replaced_symbol} for exchange {exchange_name} in signal data: {parsed_data}"
            )
            parsed_data[cls.SYMBOL_KEY] = replaced_symbol
        

    @classmethod
    def parse_signal_data(
        cls, signal_data: typing.Union[str, dict], exchange_name: typing.Optional[str],
        exchange_type: typing.Optional[trading_enums.ExchangeTypes], reference_market: typing.Optional[str], errors: list
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

        cls._adapt_symbol(parsed_data, exchange_name, exchange_type, reference_market)
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
                try:
                    await self.producers[0].signal_callback(parsed_data, script_keywords.get_base_context(self))
                except commons_errors.DSLInterpreterError as err:
                    self.logger.exception(err, True, f"Error when calling DSL script: {err}")
            else:
                self.logger.info(f"Non order signal {parsed_data[self.SIGNAL_KEY]} ignored: another trading mode on this matrix will process it")
            return True
        return False

    async def _trading_view_signal_callback(self, data):
        signal_data = data.get("metadata", "")
        errors = []
        parsed_data = self.parse_signal_data(
            signal_data, self.exchange_manager.exchange_name, 
            trading_exchanges.get_exchange_type(self.exchange_manager), 
            self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market, 
            errors
        )
        for error in errors:
            self.logger.error(error)
        try:
            if self.is_relevant_signal(parsed_data):
                parsed_data[self.SYMBOL_KEY] = self.str_symbol # make sure symbol is in the correct format
                await self.producers[0].signal_callback(parsed_data, script_keywords.get_base_context(self))
            else:
                self._log_error_message_if_relevant(parsed_data, signal_data)
        except commons_errors.DSLInterpreterError as err:
            self.logger.exception(err, True, f"Error when calling DSL script: {err}")
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


class TradingViewSignalsModeProducer(dsl_trading_mode.DSLTradingModeProducer):

    def get_channels_registration(self):
        # do not register on matrix or candles channels
        return []

    async def set_final_eval(self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame, trigger_source: str):
        # Ignore matrix calls
        pass

    async def call_dsl_script(
        self, parsed_data: dict,
        dependencies: typing.Optional[commons_signals.SignalDependencies] = None
    ) -> dsl_interpreter.DSLCallResult:
        dsl_script = tradingview_signal_to_dsl_translator.TradingViewSignalToDSLTranslator.translate_signal(
            parsed_data
        )
        self.trading_mode.set_dsl_script(dsl_script, raise_on_error=True, dependencies=dependencies) # type: ignore
        return await self.trading_mode.interpret_dsl_script() # type: ignore

    @trading_modes.enabled_trader_only(raise_when_disabled=True)
    async def signal_callback(self, parsed_data: dict, ctx):
        dependencies = await self._before_signal_processing(parsed_data)
        try:
            signal = parsed_data[TradingViewSignalsTradingMode.SIGNAL_KEY].casefold()
        except KeyError:
            raise trading_errors.InvalidArgumentError(
                f"{TradingViewSignalsTradingMode.SIGNAL_KEY} key "
                f"not found in parsed data: {parsed_data}"
            )
        match signal:
            # special cases for non-order signals
            case SignalActions.ENSURE_EXCHANGE_BALANCE:
                return await self.ensure_exchange_balance(parsed_data)
            case SignalActions.ENSURE_BLOCKCHAIN_WALLET_BALANCE:
                return await self.ensure_blockchain_wallet_balance(parsed_data)
            case _:
                # default case: most signal
                result = await self.call_dsl_script(parsed_data, dependencies)
                if result.result:
                    self.logger.info(f"DSL script successfully executed. Result: {result.result}")
                else:
                    self.logger.error(f"Error when executing DSL script: {result.error}")
                return result

    async def _before_signal_processing(self, parsed_data: dict):
        dependencies = await self._updated_orders_to_cancel(parsed_data)
        await self._update_leverage_if_necessary(parsed_data)
        return dependencies

    async def _updated_orders_to_cancel(self, parsed_data: dict):
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
        return dependencies

    async def _update_leverage_if_necessary(self, parsed_data: dict):
        try:
            if leverage := parsed_data.get(self.trading_mode.LEVERAGE):
                if symbol := parsed_data.get(TradingViewSignalsTradingMode.SYMBOL_KEY):
                    await self.trading_mode.set_leverage(symbol, None, decimal.Decimal(str(leverage)))
                else:
                    self.logger.error(f"Impossible to update leverage: symbol not found in parsed data: {parsed_data}")
        except Exception as err:
            self.logger.exception(
                err, True, f"Error when updating leverage: {err} (data: {parsed_data})"
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
            blockchain_wallets.BlockchainWalletParameters(
                blockchain_descriptor=ensure_blockchain_wallet_balance_params.blockchain_descriptor,
                wallet_descriptor=ensure_blockchain_wallet_balance_params.wallet_descriptor,
            ), 
            self.exchange_manager.trader
        ) as wallet:
            wallet_balance = await wallet.get_balance()
        balance = wallet_balance[ensure_blockchain_wallet_balance_params.asset][
            trading_constants.CONFIG_PORTFOLIO_FREE
        ] if ensure_blockchain_wallet_balance_params.asset in wallet_balance else trading_constants.ZERO

        if balance < decimal.Decimal(str(ensure_blockchain_wallet_balance_params.holdings)):
            raise trading_view_signals_trading_mode_errors.MissingFundsError(
                f"Not enough {ensure_blockchain_wallet_balance_params.asset} available on "
                f"{ensure_blockchain_wallet_balance_params.blockchain_descriptor.network} "
                f"blockchain wallet: available: {balance}, required: {ensure_blockchain_wallet_balance_params.holdings}"
            )
        else:
            self.logger.info(
                f"Enough {ensure_blockchain_wallet_balance_params.asset} available on "
                f"{ensure_blockchain_wallet_balance_params.blockchain_descriptor.network} "
                f"blockchain wallet: available: {balance}, required: {ensure_blockchain_wallet_balance_params.holdings}"
            )
        return balance
