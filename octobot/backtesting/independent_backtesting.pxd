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

cimport octobot.backtesting.octobot_backtesting as octobot_backtesting


cdef class IndependentBacktesting:
    cdef list forced_time_frames
    cdef object optimizer_id
    cdef object backtesting_id

    cdef public dict octobot_origin_config
    cdef public dict backtesting_config
    cdef public object tentacles_setup_config
    cdef public list backtesting_files

    cdef object logger
    cdef object join_backtesting_timeout
    cdef bint stop_when_finished
    cdef public bint enable_logs

    cdef public str data_file_path
    cdef public dict symbols_to_create_exchange_classes
    cdef public double risk
    cdef public dict starting_portfolio
    cdef public dict fees_config
    cdef public bint stopped

    cdef public object post_backtesting_task
    cdef public object previous_log_level
    cdef public object stopped_event
    cdef public bint enforce_total_databases_max_size_after_run

    cdef public octobot_backtesting.OctoBotBacktesting octobot_backtesting

    cpdef bint is_in_progress(self)
    cpdef bint has_finished(self)
    cpdef double get_progress(self)
    cpdef void log_report(self)

    cdef void _post_backtesting_start(self)
    cdef void _init_default_config_values(self)
    cdef dict _get_exchanges_report(self, str reference_market, object trading_mode)
    cdef void _log_trades_history(self, object exchange_manager, str exchange_name)
    cdef void _log_symbol_report(self, str symbol, object exchange_manager, object min_time_frame)
    cdef void _log_global_report(self, object exchange_manager)
    cdef void _adapt_config(self)
    cdef str _find_reference_market_and_update_contract_type(self)
    cdef void _add_config_default_backtesting_values(self)
    cdef void _add_crypto_currencies_config(self)
    cdef void _init_exchange_type(self)
