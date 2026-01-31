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
import re

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_services.constants as services_constants
import octobot_evaluators.evaluators as evaluators
import tentacles.Services.Services_feeds as Services_feeds


class TelegramSignalEvaluator(evaluators.SocialEvaluator):
    SERVICE_FEED_CLASS = Services_feeds.TelegramServiceFeed if hasattr(Services_feeds, 'TelegramServiceFeed') else None

    def init_user_inputs(self, inputs: dict) -> None:
        channels_config = self.UI.user_input(services_constants.CONFIG_TELEGRAM_CHANNEL,
                                          commons_enums.UserInputTypes.STRING_ARRAY,
                                          [], inputs, item_title="Channel name",
                                          title="Name of the watched channels")
        self.feed_config[services_constants.CONFIG_TELEGRAM_CHANNEL] = channels_config

    async def _feed_callback(self, data):
        if self._is_interested_by_this_notification(data[services_constants.CONFIG_GROUP_MESSAGE_DESCRIPTION]):
            await self.analyse_notification(data)
            await self.evaluation_completed(self.cryptocurrency, self.symbol,
                                            eval_time=self.get_current_exchange_time())
        else:
            self.logger.debug(f"Ignored telegram feed: \"{self.symbol.lower()}\" pattern not found in "
                              f"\"{data[services_constants.CONFIG_GROUP_MESSAGE_DESCRIPTION].lower()}\"")

    # return true if the given notification is relevant for this client
    def _is_interested_by_this_notification(self, notification_description):
        if self.symbol:
            return self.symbol.lower() in notification_description.lower()
        else:
            return True

    async def analyse_notification(self, notification):
        notification_test = notification[services_constants.CONFIG_GROUP_MESSAGE_DESCRIPTION]
        self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        start_eval_chars = "["
        end_eval_chars = "]"
        if start_eval_chars in notification_test and end_eval_chars in notification_test:
            try:
                split_test = notification_test.split(start_eval_chars)
                notification_eval = split_test[1].split(end_eval_chars)[0]
                potential_note = float(notification_eval)
                if -1 <= potential_note <= 1:
                    self.eval_note = potential_note
                else:
                    self.logger.error(f"Impossible to use notification evaluation: {notification_eval}: "
                                      f"evaluation should be between -1 and 1.")
            except Exception as e:
                self.logger.error(f"Impossible to parse notification {notification_test}: {e}. Please refer to this "
                                  f"evaluator documentation to check the notification pattern.")
        else:
            self.logger.error(f"Impossible to parse notification {notification_test}. Please refer to this evaluator "
                              f"documentation to check the notification pattern.")

    @classmethod
    def get_is_cryptocurrencies_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency dependant else False
        """
        return False

    @classmethod
    def get_is_cryptocurrency_name_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency name dependant else False
        """
        return False

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not symbol dependant else False
        """
        return False

    def _get_tentacle_registration_topic(self, all_symbols_by_crypto_currencies, time_frames, real_time_time_frames):
        currencies = [self.cryptocurrency]
        symbols = [self.symbol]
        to_handle_time_frames = [self.time_frame]
        if self.get_is_cryptocurrencies_wildcard():
            currencies = all_symbols_by_crypto_currencies.keys()
        if self.get_is_symbol_wildcard():
            symbols = []
            for currency_symbols in all_symbols_by_crypto_currencies.values():
                symbols += currency_symbols
        # by default no time frame registration for social evaluators
        return currencies, symbols, to_handle_time_frames


class TelegramChannelSignalEvaluator(evaluators.SocialEvaluator):
    SERVICE_FEED_CLASS = Services_feeds.TelegramApiServiceFeed if hasattr(Services_feeds, 'TelegramApiServiceFeed') else None

    SIGNAL_PATTERN_KEY = "signal_pattern"
    SIGNAL_PATTERN_MARKET_BUY_KEY = "MARKET_BUY"
    SIGNAL_PATTERN_MARKET_SELL_KEY = "MARKET_SELL"
    SIGNAL_PAIR_KEY = "signal_pair"
    SIGNAL_CHANNEL_NAME_KEY = "channel_name"

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.channels_config_by_channel_name = {}

    def init_user_inputs(self, inputs: dict) -> None:
        channels = []
        config_channels = self.UI.user_input(services_constants.CONFIG_TELEGRAM_CHANNEL,
                                          commons_enums.UserInputTypes.OBJECT_ARRAY,
                                          channels, inputs, item_title="Channel",
                                          other_schema_values={"minItems": 1, "uniqueItems": True},
                                          title="Channels to watch")
        channels.append(self._init_channel_config(inputs, "Test-Channel", "Pair: (.*)$",
                                                  "Side: (BUY)$", "Side: (SELL)$"))
        self.channels_config_by_channel_name = {
            channel[self.SIGNAL_CHANNEL_NAME_KEY]: channel
            for channel in config_channels
        }
        self.feed_config[services_constants.CONFIG_TELEGRAM_CHANNEL] = list(self.channels_config_by_channel_name)

    def _init_channel_config(self, inputs, channel_name, signal_pair, buy_regex, sell_regex):
        return {
            self.SIGNAL_CHANNEL_NAME_KEY: self.UI.user_input(
                self.SIGNAL_CHANNEL_NAME_KEY, commons_enums.UserInputTypes.TEXT,
                channel_name, inputs,
                parent_input_name=services_constants.CONFIG_TELEGRAM_CHANNEL,
                array_indexes=[0],
                title="Channel name"),
            self.SIGNAL_PAIR_KEY: self.UI.user_input(
                self.SIGNAL_PAIR_KEY, commons_enums.UserInputTypes.TEXT,
                signal_pair, inputs,
                parent_input_name=services_constants.CONFIG_TELEGRAM_CHANNEL,
                array_indexes=[0],
                title="Trading pair regex, ex: Pair: (.*)$"),
            self.SIGNAL_PATTERN_KEY: self.UI.user_input(
                self.SIGNAL_PATTERN_KEY, commons_enums.UserInputTypes.OBJECT,
                self._init_pattern_config(inputs, buy_regex, sell_regex), inputs,
                parent_input_name=services_constants.CONFIG_TELEGRAM_CHANNEL,
                array_indexes=[0],
                title="Signal patterns"),
        }

    def _init_pattern_config(self, inputs, buy_regex, sell_regex):
        return {
            self.SIGNAL_PATTERN_MARKET_BUY_KEY: self.UI.user_input(
                self.SIGNAL_PATTERN_MARKET_BUY_KEY, commons_enums.UserInputTypes.TEXT,
                buy_regex, inputs, parent_input_name=self.SIGNAL_PATTERN_KEY,
                array_indexes=[0],
                title="Market buy signal regex, ex: Side: (BUY)$"),
            self.SIGNAL_PATTERN_MARKET_SELL_KEY: self.UI.user_input(
                self.SIGNAL_PATTERN_MARKET_SELL_KEY,
                commons_enums.UserInputTypes.TEXT,
                sell_regex, inputs,
                parent_input_name=self.SIGNAL_PATTERN_KEY,
                array_indexes=[0],
                title="Market sell signal regex, ex: Side: (SELL)$"),
        }

    async def _feed_callback(self, data):
        if not data:
            return
        is_from_channel = data.get(services_constants.CONFIG_IS_CHANNEL_MESSAGE, False)
        if is_from_channel:
            sender = data.get(services_constants.CONFIG_MESSAGE_SENDER, "")
            if sender in self.channels_config_by_channel_name:
                try:
                    message = data.get(services_constants.CONFIG_MESSAGE_CONTENT, "")
                    channel_data = self.channels_config_by_channel_name[sender]
                    is_buy_market_signal = self._get_signal_message(
                        channel_data[self.SIGNAL_PATTERN_KEY][self.SIGNAL_PATTERN_MARKET_BUY_KEY], message)
                    is_sell_market_signal = self._get_signal_message(
                        channel_data[self.SIGNAL_PATTERN_KEY][self.SIGNAL_PATTERN_MARKET_SELL_KEY], message)
                    pair = self._get_signal_message(channel_data[self.SIGNAL_PAIR_KEY], message)
                    if (is_buy_market_signal or is_sell_market_signal) and pair is not None:
                        self.eval_note = -1 if is_buy_market_signal else 1
                        await self.evaluation_completed(symbol=pair.strip(), eval_time=self.get_current_exchange_time())
                    else:
                        self.logger.warning(f"Unable to parse message from {sender} : {message}")
                except KeyError:
                    self.logger.warning(f"Unable to parse message from {sender}")
            else:
                self.logger.debug(f"Ignored message : from an unsupported channel ({sender})")
        else:
            self.logger.debug("Ignored message : not a channel message")

    def _get_signal_message(self, expected_pattern, message):
        try:
            match = re.search(expected_pattern, message)
            return match.group(1)
        except AttributeError:
            self.logger.debug(f"Ignored message : not matching channel pattern ({message})")
        return None
