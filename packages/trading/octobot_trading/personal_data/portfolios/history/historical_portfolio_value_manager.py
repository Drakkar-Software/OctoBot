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
import time
import typing

import sortedcontainers
import copy

import octobot_commons.logging as logging
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.symbols as symbol_util

import octobot_trading.util as util
import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.personal_data.portfolios.portfolio_util as portfolio_util
import octobot_trading.personal_data.portfolios.history.historical_asset_value as historical_asset_value
import octobot_trading.personal_data.portfolios.history.historical_asset_value_factory as historical_asset_value_factory
import octobot_trading.personal_data.portfolios


class HistoricalPortfolioValueManager(util.Initializable):
    """
    HistoricalPortfolioValueManager stores and make the portfolio value through time as HistoricalAssetValue
    """
    TABLE_NAME = "historical_portfolio_value"
    DATA_SOURCE_KEY = "data_source"
    DATA_VERSION_KEY = "data_version"
    STARTING_PORTFOLIO = "starting_portfolio"
    ENDING_PORTFOLIO = "ending_portfolio"
    STARTING_TIME = "starting_time"
    LAST_UPDATE_TIME = "last_update_time"
    DEFAULT_DATA_SOURCE = "portfolio_value_holder"  # for later versions: consolidate data with transaction history
    DEFAULT_DATA_VERSION = "1.0.0"
    MIN_TIME_FRAME_RELEVANCY_SECONDS = 29   # less than 30s to support 1m time frames
    TIME_FRAME_RELEVANCY_TIME_RATIO = 0.45   # allow for 45% error in timestamp rounding (only used after the ideal
    # time passed to avoid using past data: use future data at worse). use high value to still take value if users
    # start it in the 1st part of the day for example
    MAX_HISTORY_SIZE = 250000

    def __init__(self, portfolio_manager, data_source=None, version=None):
        super().__init__()
        self.portfolio_manager: octobot_trading.personal_data.portfolios.PortfolioManager = portfolio_manager
        self.logger: logging.BotLogger = logging.get_logger(f"{self.__class__.__name__}"
                                         f"[{self.portfolio_manager.exchange_manager.exchange_name}]")
        self.saved_time_frames: list[str] = self.portfolio_manager.exchange_manager.config.get(
            commons_constants.CONFIG_SAVED_HISTORICAL_TIMEFRAMES,
            constants.DEFAULT_SAVED_HISTORICAL_TIMEFRAMES
        )
        self.data_source: str = data_source or self.__class__.DEFAULT_DATA_SOURCE
        self.version: str = version or self.__class__.DEFAULT_DATA_VERSION
        try:
            self.starting_time: float = self.portfolio_manager.exchange_manager.exchange.get_exchange_current_time()
        except AttributeError:
            if self.portfolio_manager.exchange_manager.is_backtesting and \
               not self.portfolio_manager.exchange_manager.exchange.connector.exchange_importers:
                # Can happen on backtesting without datafiles (used in particular setups). Only this case is acceptable
                self.starting_time = 0
            else:
                raise
        self.last_update_time: float = self.starting_time
        self.starting_portfolio: typing.Optional[dict[str, float]] = None
        self.historical_ending_portfolio: typing.Optional[dict[str, float]] = None
        self.historical_starting_portfolio_values: dict[str, float] = {}
        self.ending_portfolio: typing.Optional[dict[str, float]] = None

        self.max_history_size: int = self.__class__.MAX_HISTORY_SIZE
        self.historical_portfolio_value: dict[float, historical_asset_value.HistoricalAssetValue] = sortedcontainers.SortedDict()

    async def initialize_impl(self):
        """
        Reset the portfolio instance
        """
        # don't load any previous portfolio value on backtesting
        if not self.portfolio_manager.exchange_manager.is_backtesting:
            await self._reload_historical_portfolio_value()

    async def reset_history(self):
        self.starting_time = self.portfolio_manager.exchange_manager.exchange.get_exchange_current_time()
        self.last_update_time = self.starting_time
        self.starting_portfolio = None
        self.ending_portfolio = None
        self.historical_portfolio_value = sortedcontainers.SortedDict()
        # reset uploaded portfolio history
        await self.save_historical_portfolio_value(reset=True)

    def has_previous_session_portfolio(self):
        return self.historical_ending_portfolio is not None

    def has_historical_starting_portfolio_value(self, unit):
        return unit in self.historical_starting_portfolio_values

    def get_historical_starting_starting_portfolio_value(self, unit):
        return self.historical_starting_portfolio_values[unit]

    async def on_portfolio_update(self):
        """
        Updates the historical portfolio if changed
        """
        if self.portfolio_manager.portfolio is not None \
           and self.portfolio_manager.portfolio.portfolio is not None \
           and self.ending_portfolio != portfolio_util.portfolio_to_float(
            self.portfolio_manager.portfolio.portfolio
        ):
            await self.save_historical_portfolio_value()

    async def on_new_value(self, timestamp, value_by_currency, force_update=False, save_changes=True,
                           include_past_data=False):
        """
        Updates the historical value only if the current timestamp or currency is missing, unless force_update is True
        :param timestamp: timestamp associated to the current portfolio value. Will be adapted for each timeframe
        :param value_by_currency: dict of currency and values
        :param force_update: when True, even if timestamp is already associated to a value, the value is still updated
        :param save_changes: when True, updates the database via save_historical_portfolio_value()
        :param include_past_data: when True, also save data from past time periods using their closest relevant
        timestamp
        :return: True if something changed
        """
        # TODO replace by := when cython will support it
        relevant_timestamps = self._get_relevant_timestamps(
            timestamp, value_by_currency, self.saved_time_frames, force_update, include_past_data
        )
        if relevant_timestamps:
            return await self._upsert_value(relevant_timestamps, value_by_currency, save_changes)
        return False

    async def on_new_values(self, value_by_currency_by_timestamp, force_update=False, save_changes=True):
        changed = False
        for timestamp, value_by_currency in value_by_currency_by_timestamp.items():
            changed |= await self.on_new_value(timestamp, value_by_currency,
                                               force_update=force_update, save_changes=False,
                                               include_past_data=True)
        if changed and save_changes:
            await self.save_historical_portfolio_value()
        return changed

    def get_historical_values(self, currency, time_frame, from_timestamp=0, to_timestamp=None):
        """
        Returns a dict with timestamps and their associated portfolio historical value. Does not include the current
        portfolio value
        :param currency: the currency to compute value in
        :param time_frame: intervals between values
        :param from_timestamp: selected time window start time
        :param to_timestamp: selected time window end time
        """
        to_timestamp = to_timestamp or self.portfolio_manager.exchange_manager.exchange.get_exchange_current_time()
        time_frame_seconds = commons_enums.TimeFramesMinutes[time_frame] * commons_constants.MINUTE_TO_SECONDS
        sorted_available_timestamps = list(self.historical_portfolio_value)
        relevant_historical_values = [
            value
            for timestamp, value in self.historical_portfolio_value.items()
            if self._is_historical_timestamp_relevant(
                timestamp, time_frame_seconds, from_timestamp, to_timestamp, sorted_available_timestamps
            )
        ]
        historical_values = {}
        for historical_value in relevant_historical_values:
            try:
                historical_values[historical_value.get_timestamp()] = \
                    self._get_value_in_currency(historical_value, currency)
            except errors.MissingPriceDataError as e:
                # do not add missing historical values
                self.logger.debug(f"Missing price data when computing historical portfolio value: {e}")
        return historical_values

    def get_historical_value(self, timestamp):
        return self.historical_portfolio_value[timestamp]

    async def _upsert_value(self, timestamps, value_by_currency, save_changes):
        changed = False
        for timestamp in timestamps:
            try:
                changed = self.get_historical_value(timestamp).update(value_by_currency) or changed
            except KeyError:
                self._add_historical_portfolio_value(timestamp, value_by_currency)
                changed = True
        if changed and save_changes:
            await self.save_historical_portfolio_value()
        return changed

    def _add_historical_portfolio_value(self, timestamp, value_by_currency):
        if len(self.historical_portfolio_value) >= self.max_history_size:
            self.logger.info(
                f"Clearing oldest historical portfolio value as the maximum historical values ({self.max_history_size}) "
                f"has been reached"
            )
            # remove the oldest element
            self.historical_portfolio_value.popitem(0)
        self.historical_portfolio_value[timestamp] = \
            historical_asset_value.HistoricalAssetValue(timestamp, value_by_currency)

    def _update_portfolios(self):
        if self.portfolio_manager.portfolio is None or self.portfolio_manager.portfolio.portfolio is None:
            self.logger.debug("Ignoring portfolio values in history: portfolio_manager.portfolio is not initialized")
            return
        self.ending_portfolio = portfolio_util.filter_empty_values(portfolio_util.portfolio_to_float(
            self.portfolio_manager.portfolio.portfolio
        ))
        if self.starting_portfolio is None:
            if self.portfolio_manager.portfolio_value_holder.origin_portfolio is None \
                    or not self.portfolio_manager.portfolio_value_holder.origin_portfolio.portfolio:
                # origin portfolio might not be initialized, use ending_portfolio
                self.starting_portfolio = copy.deepcopy(self.ending_portfolio)
            else:
                self.starting_portfolio = portfolio_util.filter_empty_values(portfolio_util.portfolio_to_float(
                    self.portfolio_manager.portfolio_value_holder.origin_portfolio.portfolio
                ))

    async def save_historical_portfolio_value(self, update_data=True, reset=False):
        if update_data:
            self.last_update_time = self.portfolio_manager.exchange_manager.exchange.get_exchange_current_time()
            self._update_portfolios()
        if not self.portfolio_manager.exchange_manager.is_backtesting:
            # in backtesting, history is stored at the end
            await self.portfolio_manager.exchange_manager.storage_manager.portfolio_storage.store_history(reset=reset)

    async def _reload_historical_portfolio_value(self):
        db = self.portfolio_manager.exchange_manager.storage_manager.portfolio_storage.get_db()
        try:
            self._load_historical_values(await db.all(self.TABLE_NAME))
            self._load_metadata(await db.all(commons_enums.RunDatabases.METADATA.value))
        except Exception as err:
            self.logger.exception(err, True, f"Error when ready portfolio history: {err}")

    def _load_historical_values(self, dict_values):
        self.historical_portfolio_value = sortedcontainers.SortedDict({
            element[historical_asset_value.HistoricalAssetValue.TIMESTAMP_KEY]:
                historical_asset_value_factory.create_historical_asset_value_from_dict_like_object(
                    historical_asset_value.HistoricalAssetValue, element
                )
            for element in dict_values
        })
        self._load_historical_starting_portfolio_values()

    def _load_metadata(self, metadata_list):
        if metadata_list:
            # metadata are always stored as the 1st element of the table
            metadata = metadata_list[0]
            self.starting_time = metadata.get(self.STARTING_TIME, self.starting_time)
            self.starting_portfolio = metadata.get(self.STARTING_PORTFOLIO, None)
            self.historical_ending_portfolio = metadata.get(self.ENDING_PORTFOLIO, None)

    def _load_historical_starting_portfolio_values(self):
        self.historical_starting_portfolio_values = {}
        for value in self.historical_portfolio_value.values():
            for currency in value.get_currencies():
                if currency not in self.historical_starting_portfolio_values:
                    self.historical_starting_portfolio_values[currency] = value.get(currency)

    def _is_historical_timestamp_relevant(
        self, timestamp, time_frame_seconds, from_timestamp, to_timestamp, sorted_available_timestamps: list
    ):
        from_timestamp = from_timestamp or 0
        to_timestamp = to_timestamp or time.time()
        return self._is_timestamp_relevant(timestamp, time_frame_seconds, sorted_available_timestamps) and \
           from_timestamp <= timestamp <= to_timestamp

    @staticmethod
    def _is_timestamp_relevant(timestamp, time_frame_seconds, sorted_available_timestamps: list):
        if timestamp % time_frame_seconds == 0:
            # timestamp is expected at this time
            return True
        else:
            # timestamp is relevant only if there is no other available timestamp within the given timeframe range
            current_timestamp_index = sorted_available_timestamps.index(timestamp)
            allowed_delta = time_frame_seconds / 2
            previous_timestamp = (
                sorted_available_timestamps[current_timestamp_index - 1]
                if current_timestamp_index > 0
                else 0
            )
            next_timestamp = (
                sorted_available_timestamps[current_timestamp_index + 1]
                if current_timestamp_index < len(sorted_available_timestamps) - 1
                else (timestamp + allowed_delta)
            )
            return previous_timestamp + allowed_delta <= timestamp <= next_timestamp - allowed_delta

    @staticmethod
    def convert_to_historical_timestamp(timestamp, time_frame):
        return timestamp - (timestamp % (
                commons_enums.TimeFramesMinutes[time_frame] * commons_constants.MINUTE_TO_SECONDS
        ))

    def _get_relevant_timestamps(self, timestamp, value_by_currency, time_frames, force_update, include_past_data):
        relevant_timestamps = set()
        current_time = self.portfolio_manager.exchange_manager.exchange.get_exchange_current_time()
        for time_frame in time_frames:
            # allowed times are [local time frame t0: local time frame t0 + allowed lag]
            time_frame_allowed_window_start = self.convert_to_historical_timestamp(
                timestamp if include_past_data else current_time,
                time_frame)
            if self._should_update_timestamp(value_by_currency, time_frame_allowed_window_start, force_update):
                # allow time window if time_frame_allowed_window_start not in self.historical_portfolio_value
                # or when value changes are significant or when force_update
                time_frame_seconds = commons_enums.TimeFramesMinutes[time_frame] * commons_constants.MINUTE_TO_SECONDS
                time_frame_allowed_window_end = time_frame_allowed_window_start + \
                    max(time_frame_seconds * self.TIME_FRAME_RELEVANCY_TIME_RATIO,
                        self.MIN_TIME_FRAME_RELEVANCY_SECONDS)
                if time_frame_allowed_window_start <= timestamp <= time_frame_allowed_window_end:
                    relevant_timestamps.add(time_frame_allowed_window_start)
        return relevant_timestamps

    def _should_update_timestamp(self, value_by_currency, time_frame_allowed_window_start, force_update):
        if force_update:
            return True
        try:
            for currency, value in value_by_currency.items():
                if self.get_historical_value(time_frame_allowed_window_start).is_significant_change(currency, value):
                    return True
        except KeyError:
            return True
        return False

    def _get_value_in_currency(self, historical_value, currency):
        try:
            return historical_value.get(currency)
        except KeyError:
            return self._convert_historical_value(historical_value, currency)

    def _convert_historical_value(self, historical_value, target_currency):
        # TODO try to get a more accurate historical value into target_currency currency using price history
        # last chance: try to get any usable value from portfolio value holder (not accurate since used the intermediary
        # asset might also have changed in price since the time it was recorded)
        for currency in historical_value.get_currencies():
            quantity = historical_value.get(currency)
            # 1. try from pairs with price
            for pair in self.portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair:
                base_and_quote = symbol_util.parse_symbol(pair).base_and_quote()
                if currency in base_and_quote and target_currency in base_and_quote:
                    return self.portfolio_manager.portfolio_value_holder.value_converter\
                        .convert_currency_value_using_last_prices(
                            historical_value.get(currency), currency, target_currency
                        )
            # 2. try from existing indirect pairs
            try:
                value = self.portfolio_manager.portfolio_value_holder.value_converter.\
                    try_convert_currency_value_using_multiple_pairs(
                        currency, target_currency, quantity, []
                    )
                if value is not None:
                    return value
            except (errors.MissingPriceDataError, errors.PendingPriceDataError):
                pass
        raise errors.MissingPriceDataError(f"no price data to evaluate {historical_value} on {target_currency}")

    def get_dict_historical_values(self):
        return [historical_asset.to_dict() for historical_asset in self.historical_portfolio_value.values()]

    def get_metadata(self):
        return {
            self.DATA_SOURCE_KEY: self.data_source,
            self.DATA_VERSION_KEY: self.version,
            self.STARTING_TIME: self.starting_time,
            self.STARTING_PORTFOLIO: self.starting_portfolio,
            self.ENDING_PORTFOLIO: self.ending_portfolio,
            self.LAST_UPDATE_TIME: self.last_update_time
        }

    async def stop(self):
        await self.save_historical_portfolio_value(update_data=False)
