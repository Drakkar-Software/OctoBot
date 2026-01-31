# pylint: disable=C0301,R0902,R0913,C0415,R0801
#  Drakkar-Software OctoBot-Commons
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
import octobot_commons.constants as constants
import octobot_commons.enums as enums
import octobot_commons.errors as errors
import octobot_commons.databases.cache_manager as cache_manager
import octobot_commons.databases.implementations as implementations
import octobot_commons.databases.document_database_adaptors as document_database_adaptors


class CacheClient:
    def __init__(
        self,
        tentacle,
        exchange_name,
        symbol,
        time_frame,
        tentacles_setup_config,
        flush_cache_when_necessary,
        config_name=None,
    ):
        self._flush_cache_when_necessary = flush_cache_when_necessary
        self.cache_manager = cache_manager.CacheManager(
            database_adaptor=document_database_adaptors.TinyDBAdaptor
        )
        self.config_name = config_name or self.cache_manager.DEFAULT_CONFIG_IDENTIFIER
        self.tentacle = tentacle
        self.exchange_name = exchange_name
        self.symbol = symbol
        self.time_frame = time_frame
        self.tentacles_setup_config = tentacles_setup_config
        try:
            import octobot_tentacles_manager.models as tentacles_manager_models

            self.tentacles_requirements = (
                tentacles_manager_models.TentacleRequirementsTree(
                    self.tentacle, self.config_name
                )
            )
        except ImportError as err:
            raise ImportError(
                "OctoBot-Tentacles-Manager is required to use cache clients"
            ) from err

    def has_cache(self, pair, time_frame, tentacle_name=None, config_name=None):
        """
        Returns True when a cache as specified in arguments is currently open
        :param pair: pair/symbol to build a cache path from
        :param pair: time_frame to build a cache path from
        :param tentacle_name: tentacle to build a cache path from
        :param config_name: name of the configuration
        """
        return self.cache_manager.has_cache(
            tentacle_name or self.tentacle.get_name(),
            self.exchange_name,
            pair,
            time_frame,
            config_name or self.config_name,
        )

    def get_cache_path(self, tentacle, config_name=None):
        """
        Returns the path to the cache associated to the given tentacle
        :param tentacle: tentacle to build a cache path from
        :param config_name: name of the configuration
        """
        config_name = config_name or self.config_name
        return self.cache_manager.get_cache_or_build_path(
            tentacle,
            self.exchange_name,
            self.symbol,
            self.time_frame,
            tentacle.get_name(),
            config_name,
            self.tentacles_setup_config,
            self.tentacles_requirements,
        )

    def get_cache(
        self,
        tentacle_name=None,
        cache_type=implementations.CacheTimestampDatabase,
        config_name=None,
    ):
        """
        Returns the cache associated to the given tentacle_name
        :param tentacle_name: name of the tentacle to get cache from
        :param cache_type: type of the cache
        :param config_name: name of the configuration
        """
        tentacle = self.tentacle if tentacle_name is None else None
        tentacle_name = tentacle_name or self.tentacle.get_name()
        config_name = config_name or self.config_name
        cache, just_created = self.cache_manager.get_cache(
            tentacle,
            tentacle_name,
            self.exchange_name,
            self.symbol,
            self.time_frame,
            config_name,
            self.tentacles_setup_config,
            self.tentacles_requirements,
            cache_type=cache_type,
        )
        if just_created and cache_type is implementations.CacheTimestampDatabase:
            if tentacle is None:
                metadata = self.cache_manager.get_cache_previous_db_metadata(
                    tentacle_name,
                    self.exchange_name,
                    self.symbol,
                    self.time_frame,
                    config_name,
                )
            else:
                metadata = {
                    enums.CacheDatabaseColumns.TRIGGERED_AFTER_CANDLES_CLOSE.value: tentacle.is_triggered_after_candle_close
                }
            if metadata is None:
                raise RuntimeError(
                    "Missing db metadata. Please provide the tentacle parameter to this method"
                )
            cache.add_metadata(metadata)
        return cache

    async def get_cached_value(
        self,
        value_key: str = enums.CacheDatabaseColumns.VALUE.value,
        cache_key=None,
        tentacle_name=None,
        config_name=None,
    ) -> tuple:
        """
        Get a value for the current cache
        :param value_key: identifier of the value
        :param cache_key: timestamp to use in order to look for a value
        :param tentacle_name: name of the tentacle to get cache from
        :param config_name: name of the tentacle configuration as used in nested tentacle calls
        :return: the cached value and a boolean (True if cached value is missing from cache)
        """
        try:
            return (
                await self.get_cache(
                    tentacle_name=tentacle_name, config_name=config_name
                ).get(cache_key, name=value_key),
                False,
            )
        except errors.NoCacheValue:
            return None, True

    async def set_cached_value(
        self,
        value,
        value_key: str = enums.CacheDatabaseColumns.VALUE.value,
        cache_key=None,
        flush_if_necessary=False,
        tentacle_name=None,
        config_name=None,
        **kwargs,
    ):
        """
        Set a value into the current cache
        :param value: value to set
        :param value_key: identifier of the value
        :param cache_key: timestamp to associate the value to
        :param flush_if_necessary: flush the cache after set (write into database)
        :param tentacle_name: name of the tentacle to get cache from
        :param config_name: name of the tentacle configuration as used in nested tentacle calls
        :param kwargs: other related value_key / value couples to set at this timestamp. Use for plotted data
        :return: None
        """
        cache = None
        try:
            cache = self.get_cache(tentacle_name=tentacle_name, config_name=config_name)
            await cache.set(cache_key, value, name=value_key)
            if kwargs:
                for key, val in kwargs.items():
                    await cache.set(
                        cache_key,
                        val,
                        name=f"{value_key}{constants.CACHE_RELATED_DATA_SEPARATOR}{key}",
                    )
        finally:
            if flush_if_necessary and self._flush_cache_when_necessary and cache:
                await cache.flush()

    async def set_cached_values(
        self,
        values,
        value_key,
        cache_keys,
        flush_if_necessary=False,
        tentacle_name=None,
        config_name=None,
        additional_values_by_key=None,
    ):
        """
        Set a value into the current cache
        :param values: values to set
        :param value_key: identifier of the value
        :param cache_keys: timestamps to associate the values to
        :param flush_if_necessary: flush the cache after set (write into database)
        :param tentacle_name: name of the tentacle to get cache from
        :param config_name: name of the tentacle configuration as used in nested tentacle calls
        :param additional_values_by_key: other values to set in a dict of cache_keys
        :return: None
        """
        cache = None
        try:
            cache = self.get_cache(tentacle_name=tentacle_name, config_name=config_name)
            await cache.set_values(
                cache_keys,
                values,
                name=value_key,
                additional_values_by_key=additional_values_by_key,
            )
        finally:
            if flush_if_necessary and self._flush_cache_when_necessary and cache:
                await cache.flush()

    def ensure_no_missing_cached_value(self, is_missing):
        """
        Raises NoCacheValue when is_missing is True
        :param is_missing: True when a value is missing
        """
        if is_missing:
            raise errors.NoCacheValue(
                f"No cache value with cache key: {enums.CacheDatabaseColumns.VALUE.value}. "
                f"Impossible process {constants.DO_NOT_OVERRIDE_CACHE} return value."
            )
