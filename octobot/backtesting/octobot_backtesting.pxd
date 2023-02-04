# cython: language_level=3
#  Drakkar-Software OctoBot
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
cimport octobot_backtesting.backtest_data as backtest_data


cdef class OctoBotBacktesting:
    cdef public dict backtesting_config
    cdef public object tentacles_setup_config

    cdef object logger

    cdef public str matrix_id
    cdef public str bot_id
    cdef public list exchange_manager_ids
    cdef public dict symbols_to_create_exchange_classes
    cdef public list evaluators
    cdef public list service_feeds
    cdef public dict fees_config
    cdef public list backtesting_files
    cdef public backtest_data.BacktestData backtesting_data
    cdef public object backtesting
    cdef public bint run_on_common_part_only
    cdef public object start_time
    cdef public object start_timestamp
    cdef public object end_timestamp
    cdef public bint enable_logs
    cdef public dict exchange_type_by_exchange
    cdef public object futures_contract_type
    cdef public bint enable_storage
    cdef public bint run_on_all_available_time_frames
    cdef bint _has_started

    cpdef object memory_leak_checkup(self, list to_check_elements)
    cpdef object check_remaining_objects(self)

cdef str _get_remaining_object_error(object obj, int expected, tuple actual)
