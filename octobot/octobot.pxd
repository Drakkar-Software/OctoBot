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
from octobot.initializer cimport Initializer
from octobot.task_manager cimport TaskManager
from octobot.exchange_factory cimport ExchangeFactory

from octobot.evaluator_factory cimport EvaluatorFactory

cdef class OctoBot:
    cdef object logger

    cdef public double start_time

    cdef public bint reset_trading_history

    cdef public dict config
    cdef public dict startup_config
    cdef public dict edited_config
    cdef public dict tools

    cdef object _aiohttp_session
    cdef public object metrics_handler
    cdef public object async_loop

    cdef public Initializer initializer
    cdef public TaskManager task_manager
    cdef public ExchangeFactory exchange_factory
    cdef public EvaluatorFactory evaluator_factory

    cpdef object run_in_main_asyncio_loop(self, object coroutine)
    cpdef void set_watcher(self, object watcher)
    cpdef object get_aiohttp_session(self)