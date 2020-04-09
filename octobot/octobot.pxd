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
from octobot.configuration_manager cimport ConfigurationManager
from octobot.initializer cimport Initializer
from octobot.factories.interface_factory cimport InterfaceFactory
from octobot.octobot_api cimport OctoBotAPI
from octobot.factories.service_feed_factory cimport ServiceFeedFactory
from octobot.task_manager cimport TaskManager
from octobot.factories.exchange_factory cimport ExchangeFactory

from octobot.factories.evaluator_factory cimport EvaluatorFactory

cdef class OctoBot:
    cdef object logger

    cdef public double start_time

    cdef public bint reset_trading_history
    cdef public bint initialized

    cdef public dict tools
    cdef public dict config
    cdef public str bot_id

    cdef object _aiohttp_session
    cdef public object community_handler
    cdef public object async_loop
    cdef public object tentacles_setup_config

    cdef public Initializer initializer
    cdef public TaskManager task_manager
    cdef public ExchangeFactory exchange_factory
    cdef public EvaluatorFactory evaluator_factory
    cdef public InterfaceFactory interface_factory
    cdef public ServiceFeedFactory service_feed_factory
    cdef public OctoBotAPI octobot_api
    cdef public ConfigurationManager configuration_manager

    cpdef object run_in_main_asyncio_loop(self, object coroutine)
    cpdef void set_watcher(self, object watcher)
    cpdef object get_aiohttp_session(self)
