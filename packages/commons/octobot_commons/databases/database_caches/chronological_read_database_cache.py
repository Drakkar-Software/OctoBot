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


class ChronologicalReadDatabaseCache:
    DATA_KEY = "data"
    DATA_SORT_KEY = "data_sort_key"
    CHRONO_INDEX_KEY = "chrono_index"

    def __init__(self):
        self.timestamped_sorted_data = {}

    def set(self, values, sort_key, identifiers):
        """
        Set whole cache to later be able to efficiently select it
        :param values: cache values to set
        :param sort_key: key in the values dict to use to chronologically order data
        :param identifiers: identifiers of the given cache. Used to store multiple cache sets
        """
        nested_cache = self.timestamped_sorted_data
        for identifier in identifiers:
            if identifier not in nested_cache:
                nested_cache[identifier] = {}
            nested_cache = nested_cache[identifier]
        data = self._get_cache_data(identifiers)
        data[self.DATA_SORT_KEY] = sort_key
        data[self.DATA_KEY] = sorted(values, key=lambda x: x[sort_key])
        data[self.CHRONO_INDEX_KEY] = 0

    def reset_cached_indexes(self, parent=None):
        """
        Set the cache index of each cached element at 0
        :param parent: current cached element
        """
        for cached_data in (parent or self.timestamped_sorted_data).values():
            if isinstance(cached_data, dict):
                if self.CHRONO_INDEX_KEY in cached_data:
                    cached_data[self.CHRONO_INDEX_KEY] = 0
                else:
                    self.reset_cached_indexes(cached_data)

    def get(self, inferior_timestamp, superior_timestamp, identifiers):
        """
        Returns a cache values
        :param inferior_timestamp: timestamp to start selecting from. Use constants.DEFAULT_IGNORED_VALUE to select all
        :param superior_timestamp: timestamp to stop selecting at. Use constants.DEFAULT_IGNORED_VALUE to select all
        :param identifiers: identifiers of the cache to look into. Used to store multiple cache sets
        """
        cache_data = self._get_cache_data(identifiers)
        # if one timestamp is constants.DEFAULT_IGNORED_VALUE, return every available data from/up to this timestamp
        if inferior_timestamp == constants.DEFAULT_IGNORED_VALUE:
            if superior_timestamp == constants.DEFAULT_IGNORED_VALUE:
                return cache_data[self.DATA_KEY]
            return [
                element
                for element in cache_data[self.DATA_KEY]
                if element[cache_data[self.DATA_SORT_KEY]] <= superior_timestamp
            ]
        if superior_timestamp == constants.DEFAULT_IGNORED_VALUE:
            return [
                element
                for element in cache_data[self.DATA_KEY]
                if element[cache_data[self.DATA_SORT_KEY]] >= inferior_timestamp
            ]
        return self._get_from_time_window(
            cache_data, inferior_timestamp, superior_timestamp
        )

    def _get_from_time_window(self, cache_data, inferior_timestamp, superior_timestamp):
        data = cache_data[self.DATA_KEY]
        data_sort_key = cache_data[self.DATA_SORT_KEY]
        # a specific time window is requested: use the local cache index to generate it faster
        min_index = max_index = None
        # identify the select window considering data are time sorted
        start_index = cache_data[self.CHRONO_INDEX_KEY]
        for index in range(start_index, len(data)):
            element = data[index]
            if element[data_sort_key] >= inferior_timestamp and min_index is None:
                min_index = index
            if element[data_sort_key] > superior_timestamp and max_index is None:
                max_index = index
                # consider that since inferior_timestamp got requested, as this is a chronological database cache,
                # is going only following requests will only be in future times. Therefore previous data can be
                # ignored to avoid iterating over them over and over
                cache_data[self.CHRONO_INDEX_KEY] = min_index
                return data[min_index:max_index]
        if min_index is None:
            return []
        return data[min_index:]

    def has(self, identifiers):
        """
        :param identifiers: identifiers of the cache to look for.
        :return: True if the current identifiers are related to a registered cache
        """
        try:
            self._get_cache_data(identifiers)
            return True
        except KeyError:
            return False

    def _get_cache_data(self, identifiers):
        found_data = self.timestamped_sorted_data
        for identifier in identifiers:
            found_data = found_data[identifier]
        return found_data

    def clear(self):
        """
        Resets the cache database
        """
        self.timestamped_sorted_data = {}
