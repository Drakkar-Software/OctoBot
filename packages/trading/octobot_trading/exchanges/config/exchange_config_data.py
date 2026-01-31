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
import copy
import typing

import octobot_commons.symbols
import octobot_commons.symbols.symbol_util as symbols_util
import octobot_commons.time_frame_manager as time_frame_manager
import octobot_commons.constants as constants
import octobot_commons.logging as logging
import octobot_commons.errors as errors
import octobot_commons.enums as commons_enums
import octobot_commons.tree as commons_tree

import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.exchanges.config.backtesting_exchange_config as backtesting_exchange_config
import octobot_trading.exchanges.util as exchange_util
import octobot_trading.exchanges.exchange_websocket_factory as exchange_websocket_factory
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.util as util


class ExchangeConfig(util.Initializable):
    def __init__(self, exchange_manager):
        super().__init__()
        self._logger = logging.get_logger(f"{self.__class__.__name__}[{exchange_manager.exchange_name}]")

        self.exchange_manager = exchange_manager
        self.config: dict[str, typing.Any] = exchange_manager.config

        # dict of exchange supported pairs by enabled currencies from self.config
        self.traded_cryptocurrencies: dict[str, list[str]] = {}

        # list of exchange supported enabled pairs from self.config
        self.traded_symbol_pairs: list[str] = []

        # Same as traded_symbol_pairs but with parsed symbols
        self.traded_symbols: list[octobot_commons.symbols.Symbol] = []

        # list of exchange supported pairs on which we want to collect data through updaters or websocket
        self.watched_pairs: list[str] = []

        # list of exchange supported pairs on which we want to collect data through updaters or websocket
        self.additional_traded_pairs: list[str] = []

        # list of exchange supported pairs that have been removed from the traded_symbol_pairs or additional_traded_pairs
        self.removed_traded_pairs: list[str] = []

        # list of required time frames from configuration that are available
        self.available_required_time_frames: list[commons_enums.TimeFrames] = []

        # list of exchange supported time frames that are also required (config + real time)
        self.traded_time_frames: list[commons_enums.TimeFrames] = []

        # list of time frames to be used for real-time purposes (short time frames)
        self.real_time_time_frames: list[commons_enums.TimeFrames] = []

        # list of exchange supported time frames that are traded (config + real time) and that are used for display only
        self.available_time_frames: list[commons_enums.TimeFrames] = []

        # list of potential additional time frames to be used by additional_traded_pairs only
        self.additional_time_frames: list[commons_enums.TimeFrames] = []

        # number of required historical candles
        self.required_historical_candles_count: int = constants.DEFAULT_IGNORED_VALUE

        # When False, cancelled orders won't be saved in trades history
        self.is_saving_cancelled_orders_as_trade: bool = True

        # When True, short timeframes will be added for real-time evaluators
        self.realtime_data_fetching: bool = False

        self.backtesting_exchange_config = None

    async def initialize_impl(self):
        pass

    def get_all_traded_currencies(self):
        currencies = []
        for symbol in self.traded_symbols:
            currencies.append(symbol.base)
            currencies.append(symbol.quote)
        return list(set(currencies))

    def set_config_traded_pairs(self):
        self._set_config_traded_pairs()

    def set_config_time_frame(self):
        self._set_config_time_frame()

    def init_backtesting_exchange_config(self):
        self.backtesting_exchange_config = backtesting_exchange_config.BacktestingExchangeConfig()

    def set_historical_settings(self):
        self.required_historical_candles_count = self.config.get(constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT,
                                                                 constants.DEFAULT_IGNORED_VALUE)

    def get_shortest_time_frame(self):
        return self.traded_time_frames[-1]

    def initialize_exchange_event_tree(self):
        tree_provider = commons_tree.EventProvider.instance()
        for topic in trading_constants.DEFAULT_FUTURES_INITIALIZATION_EVENT_TOPICS \
                if self.exchange_manager.is_future \
                else trading_constants.DEFAULT_INITIALIZATION_EVENT_TOPICS:
            if topic in (
                commons_enums.InitializationEventExchangeTopics.POSITIONS,
                commons_enums.InitializationEventExchangeTopics.TRADES,
                commons_enums.InitializationEventExchangeTopics.ORDERS,
                commons_enums.InitializationEventExchangeTopics.CONTRACTS,
                commons_enums.InitializationEventExchangeTopics.CANDLES,
                commons_enums.InitializationEventExchangeTopics.PRICE,
                commons_enums.InitializationEventExchangeTopics.ORDER_BOOK,
                commons_enums.InitializationEventExchangeTopics.FUNDING,
            ):
                for symbol in self.traded_symbol_pairs:
                    if topic in (
                        commons_enums.InitializationEventExchangeTopics.CANDLES,
                    ):
                        for time_frame in self.traded_time_frames:
                            tree_provider.create_event_at_path(
                                self.exchange_manager.bot_id, commons_tree.get_exchange_path(
                                    self.exchange_manager.exchange_name,
                                    topic.value,
                                    symbol=symbol,
                                    time_frame=time_frame.value
                                )
                            )
                    else:
                        tree_provider.create_event_at_path(
                            self.exchange_manager.bot_id, commons_tree.get_exchange_path(
                                self.exchange_manager.exchange_name,
                                topic.value,
                                symbol=symbol
                            )
                        )
            else:
                tree_provider.create_event_at_path(
                    self.exchange_manager.bot_id, commons_tree.get_exchange_path(
                        self.exchange_manager.exchange_name,
                        topic.value
                    )
                )

    def get_relevant_time_frames(self):
        # If required timeframes: use those. Use traded timeframes otherwise
        return self.available_required_time_frames or self.traded_time_frames

    def set_is_saving_cancelled_orders_as_trade(self, value: bool):
        self.is_saving_cancelled_orders_as_trade = value

    async def add_watched_symbols(self, symbols: list[str]):
        await self.update_traded_symbol_pairs(
            added_pairs=symbols, removed_pairs=[], added_time_frames=[], watch_only=True
        )

    async def add_traded_symbols(self, symbols: list[str], time_frames: list[commons_enums.TimeFrames]):
        await self.update_traded_symbol_pairs(
            added_pairs=symbols, removed_pairs=[], added_time_frames=time_frames, watch_only=False
        )

    async def remove_traded_symbols(self, symbols: list[str]):
        await self.update_traded_symbol_pairs(
            added_pairs=[], removed_pairs=symbols, added_time_frames=[], watch_only=False
        )

    async def update_traded_symbol_pairs(
        self,
        added_pairs: list[str],
        removed_pairs: list[str],
        added_time_frames: list[commons_enums.TimeFrames],
        watch_only: bool = False,
    ):
        # All channels with a modify() method should be added here
        watch_only_channels_to_notify = [trading_constants.TICKER_CHANNEL]
        traded_channels_to_notify_when_no_websocket = exchange_channel.get_to_notify_on_traded_symbols_update_channels(
            self.exchange_manager.id
        )
        traded_channels_to_notify = {
            name: channel 
            for name, channel in traded_channels_to_notify_when_no_websocket.items()
            if (
                not exchange_websocket_factory.is_channel_managed_by_websocket(
                    self.exchange_manager, name
                )
            ) or (
                exchange_websocket_factory.is_channel_managed_by_websocket(
                    self.exchange_manager, name
                )
                and exchange_websocket_factory.is_websocket_feed_requiring_init(self.exchange_manager, name) 
            )
        }
        new_valid_symbol_pairs = [
            symbol_pair
            for symbol_pair in added_pairs
            if symbols_util.is_symbol(symbol_pair) 
            and self._is_valid_symbol(symbol_pair, [])
            and symbol_pair not in self.traded_symbol_pairs 
            and symbol_pair not in self.additional_traded_pairs 
            and symbol_pair not in self.removed_traded_pairs
            and (not watch_only or symbol_pair not in self.watched_pairs)
        ]
        removed_valid_symbol_pairs = [
            symbol_pair
            for symbol_pair in removed_pairs
            if symbols_util.is_symbol(symbol_pair) 
            and self._is_valid_symbol(symbol_pair, [])
            and (symbol_pair in self.traded_symbol_pairs or symbol_pair in self.additional_traded_pairs or (not watch_only or symbol_pair in self.watched_pairs))
            and symbol_pair not in self.removed_traded_pairs
        ]
        new_valid_time_frames = [
            time_frame
            for time_frame in added_time_frames
            if time_frame not in self.additional_time_frames
            and time_frame not in self.available_time_frames
            and self.exchange_manager.time_frame_exists(time_frame.value)
        ]
        if not (new_valid_symbol_pairs or removed_valid_symbol_pairs):
            # nothing to do
            if new_valid_time_frames:
                self._logger.error(
                    f"Ignored additional time frames for watched pairs: {new_valid_time_frames} "
                    f"(no traded or watched pairs to add)"
                )
            return
        try:
            if watch_only:
                self.watched_pairs += new_valid_symbol_pairs
                self.watched_pairs = [pair for pair in self.watched_pairs if pair not in removed_valid_symbol_pairs]
                if new_valid_time_frames:
                    self._logger.error(
                        f"Ignored additional time frames for watched pairs: {new_valid_time_frames} "
                        f"(watched pairs are not bound to any time frame)"
                    )
            else:
                self.additional_traded_pairs += new_valid_symbol_pairs
                self.additional_traded_pairs = [pair for pair in self.additional_traded_pairs if pair not in removed_valid_symbol_pairs]
                if new_valid_time_frames:
                    self.additional_time_frames += new_valid_time_frames
                    self._logger.debug(f"Adding additional time frames: {new_valid_time_frames}")
                elif not self.available_time_frames:
                    # if no available time frames, use a default time as at least one is required
                    self.additional_time_frames.append(commons_enums.TimeFrames.ONE_HOUR)
                    self._logger.info(
                        f"No available time frames found for {self.exchange_manager.exchange_name}, using default time frame: {self.additional_time_frames[0]}"
                    )
            removing = f" and removing {removed_valid_symbol_pairs}" if removed_valid_symbol_pairs else ""
            self._logger.debug(
                f"Updated {'watched' if watch_only else 'traded'} symbol pairs: adding {new_valid_symbol_pairs}{removing}"
            )
            if self.exchange_manager.has_websocket:
                if new_valid_symbol_pairs:
                    self.exchange_manager.exchange_web_socket.add_pairs(new_valid_symbol_pairs, watching_only=watch_only)
                if removed_valid_symbol_pairs:
                    self.exchange_manager.exchange_web_socket.remove_pairs(removed_valid_symbol_pairs, watching_only=watch_only)
                await self.exchange_manager.exchange_web_socket.handle_updated_pairs(debounce_duration=1)

            for channel in watch_only_channels_to_notify:
                await exchange_channel.get_chan(channel, self.exchange_manager.id).modify(
                    added_pairs=new_valid_symbol_pairs, removed_pairs=removed_valid_symbol_pairs
                )

            if not watch_only:
                for channel in traded_channels_to_notify.values():
                    await channel.modify(
                        added_pairs=new_valid_symbol_pairs, removed_pairs=removed_valid_symbol_pairs
                    )

            if removed_valid_symbol_pairs:
                self.traded_symbol_pairs = [pair for pair in self.traded_symbol_pairs if pair not in removed_valid_symbol_pairs]
                self.additional_traded_pairs = [pair for pair in self.additional_traded_pairs if pair not in removed_valid_symbol_pairs]
                self.watched_pairs = [pair for pair in self.watched_pairs if pair not in removed_valid_symbol_pairs]
                self.removed_traded_pairs += removed_valid_symbol_pairs
        except Exception as e:
            self._logger.exception(e, True, f"Failed to update {'watched' if watch_only else 'traded'} symbol pairs {added_pairs} and {removed_pairs} : {e}")

    def _set_config_traded_pairs(self):
        self.traded_cryptocurrencies = {}
        traded_symbol_pairs_set = set()
        existing_pairs = set()
        for cryptocurrency in self.config[constants.CONFIG_CRYPTO_CURRENCIES]:
            traded_symbol_pairs_set = self._set_config_traded_pair(cryptocurrency,
                                                                   traded_symbol_pairs_set,
                                                                   existing_pairs)
        # sort lists to avoid set insert randomness issues
        self.traded_symbol_pairs = sorted(list(traded_symbol_pairs_set))
        self.traded_symbols = [
            octobot_commons.symbols.parse_symbol(symbol)
            for symbol in self.traded_symbol_pairs
        ]

        # only add self.traded_symbol_pairs to watched pairs as not every existing_pairs are being collected
        self.watched_pairs = copy.deepcopy(self.traded_symbol_pairs)

    def _set_config_traded_pair(self, cryptocurrency, traded_symbol_pairs_set, existing_pairs):
        try:
            is_enabled = util.is_currency_enabled(self.config, cryptocurrency, True)
            if self.config[constants.CONFIG_CRYPTO_CURRENCIES][cryptocurrency].get(constants.CONFIG_CRYPTO_PAIRS, []):
                if self.config[constants.CONFIG_CRYPTO_CURRENCIES][cryptocurrency][constants.CONFIG_CRYPTO_PAIRS] != \
                        constants.CONFIG_SYMBOLS_WILDCARD:
                    self._populate_non_wildcard_pairs(cryptocurrency, existing_pairs, is_enabled)
                else:
                    self._populate_wildcard_pairs(cryptocurrency, existing_pairs, is_enabled)
                # add to global traded pairs
                if is_enabled:
                    if not self.traded_cryptocurrencies[cryptocurrency]:
                        self._logger.warning(
                            f"{self.exchange_manager.exchange_name} is not supporting any {cryptocurrency} trading pair"
                            f" from the current configuration.")
                    traded_symbol_pairs_set = traded_symbol_pairs_set.union(
                        self.traded_cryptocurrencies[cryptocurrency]
                    )
            elif is_enabled:
                self._logger.error(f"Current configuration for {cryptocurrency} is not including any trading pair, "
                                   f"this asset can't be traded and related orders won't be loaded. "
                                   f"OctoBot requires at least one trading pair in configuration to handle an asset. "
                                   f"You can add trading pair(s) for each asset in the configuration section.")
        except errors.ConfigError as err:
            self._logger.error(str(err))
        return traded_symbol_pairs_set

    def _populate_non_wildcard_pairs(self, cryptocurrency, existing_pairs, is_enabled):
        exchange_type = exchange_util.get_exchange_type(self.exchange_manager)
        if self.config[constants.CONFIG_CRYPTO_CURRENCIES][cryptocurrency][constants.CONFIG_CRYPTO_PAIRS] != \
                constants.CONFIG_SYMBOLS_WILDCARD:
            currency_pairs = []
            for symbol in self.config[constants.CONFIG_CRYPTO_CURRENCIES][cryptocurrency][
               constants.CONFIG_CRYPTO_PAIRS]:
                self._add_compatible_pairs(currency_pairs, symbol, existing_pairs, is_enabled, exchange_type)
            if is_enabled:
                self.traded_cryptocurrencies[cryptocurrency] = currency_pairs

    def _add_compatible_pairs(self, currency_pairs, symbol, existing_pairs, is_enabled, exchange_type):
        if self.exchange_manager.symbol_exists(symbol):
            if is_enabled:
                if self._is_pair_compatible(exchange_type, symbol):
                    currency_pairs.append(symbol)
                else:
                    self._logger.warning(f"Ignored {symbol} trading pair: only {exchange_type.value} "
                                         f"pairs are allowed on {self.exchange_manager.exchange_name} when "
                                         f"using {exchange_type.value} trading")
            # also add disabled pairs to existing pairs since they still exist on exchange
            existing_pairs.add(symbol)
        elif is_enabled:
            additional_details = ""
            if self.exchange_manager.is_sandboxed:
                additional_details = f" Exchange sandbox is enabled, please make sure this pair is traded on " \
                                     f" the {self.exchange_manager.exchange_name} sandbox as sandboxes " \
                                     f"usually only support a subset of the real exchange's pairs."
            self._logger.warning(f"{self.exchange_manager.exchange_name} is not supporting the "
                               f"{symbol} trading pair.{additional_details}")

    @staticmethod
    def _is_pair_compatible(exchange_type, symbol):
        parsed_symbol = octobot_commons.symbols.parse_symbol(symbol)
        if exchange_type is trading_enums.ExchangeTypes.FUTURE:
            return parsed_symbol.is_future()
        if exchange_type is trading_enums.ExchangeTypes.OPTION:
            return parsed_symbol.is_option()
        # allow futures symbols for spot
        return True

    def _populate_wildcard_pairs(self, cryptocurrency, existing_pairs, is_enabled):
        try:
            wildcard_pairs_list = self._create_wildcard_symbol_list(self.config[constants.CONFIG_CRYPTO_CURRENCIES]
                                                                    [cryptocurrency][constants.CONFIG_CRYPTO_QUOTE])
        except KeyError as e:
            raise errors.ConfigError(f"Impossible to use a wildcard configuration for {cryptocurrency}: missing {e} "
                                     f"value in {cryptocurrency} {constants.CONFIG_CRYPTO_CURRENCIES} "
                                     f"configuration.")

        # additional pairs
        if constants.CONFIG_CRYPTO_ADD in self.config[constants.CONFIG_CRYPTO_CURRENCIES][cryptocurrency]:
            wildcard_pairs_list += self._add_tradable_symbols_from_config(cryptocurrency,
                                                                          wildcard_pairs_list)

        if is_enabled:
            self.traded_cryptocurrencies[cryptocurrency] = wildcard_pairs_list

        # also add disabled pairs to existing pairs since they still exist on exchange
        existing_pairs.update(wildcard_pairs_list)

    def _set_config_time_frame(self):
        display_time_frames = []
        for time_frame in time_frame_manager.get_config_time_frame(self.config):
            if self.exchange_manager.time_frame_exists(time_frame.value):
                self.available_required_time_frames.append(time_frame)
        if self.realtime_data_fetching and (
            (
                not self.exchange_manager.is_backtesting or
                (self.exchange_manager.is_backtesting and self.exchange_manager.exchange.use_accurate_price_time_frame())
            ) or not self.available_required_time_frames
        ):
            # add shortest time frame for realtime evaluators
            client_shortest_time_frame = time_frame_manager.find_min_time_frame(
                self.exchange_manager.client_time_frames,
                constants.MIN_EVAL_TIME_FRAME)
            self.real_time_time_frames.append(client_shortest_time_frame)
        if self.exchange_manager.time_frame_exists(trading_constants.DISPLAY_TIME_FRAME.value):
            # add display time frame if not available already
            display_time_frames.append(trading_constants.DISPLAY_TIME_FRAME)
        self.available_required_time_frames = time_frame_manager.sort_time_frames(self.available_required_time_frames,
                                                                                  reverse=True)
        self.traded_time_frames = list(set().union(
            self.available_required_time_frames,
            self.real_time_time_frames,
        ))
        self.available_time_frames = list(set().union(
            self.traded_time_frames,
            display_time_frames,
        ))
        self.traded_time_frames = time_frame_manager.sort_time_frames(self.traded_time_frames, reverse=True)
        self.available_time_frames = time_frame_manager.sort_time_frames(self.available_time_frames, reverse=True)

    @staticmethod
    def _is_tradable_with_cryptocurrency(symbol, cryptocurrency):
        return symbol if octobot_commons.symbols.parse_symbol(symbol).quote == cryptocurrency else None

    def _add_tradable_symbols_from_config(self, cryptocurrency, filtered_symbols):
        return [
            symbol
            for symbol in self.config[constants.CONFIG_CRYPTO_CURRENCIES][cryptocurrency][constants.CONFIG_CRYPTO_ADD]
            if self._is_valid_symbol(symbol, filtered_symbols)
        ]

    def _is_valid_symbol(self, symbol, filtered_symbols):
        return self.exchange_manager.symbol_exists(symbol) and symbol not in filtered_symbols

    def _create_wildcard_symbol_list(self, cryptocurrency):
        return [s for s in [ExchangeConfig._is_tradable_with_cryptocurrency(symbol, cryptocurrency)
                            for symbol in self.exchange_manager.client_symbols]
                if s is not None]
