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
cimport octobot.configuration_manager as configuration_manager
cimport octobot.octobot_channel_consumer as octobot_channel_consumer
cimport octobot.initializer as initializer
cimport octobot.octobot_api as octobot_api
cimport octobot.producers as producers
cimport octobot.task_manager as task_manager


cdef class OctoBot:
    cdef object logger

    cdef public double start_time

    cdef public bint reset_trading_history
    cdef public bint initialized
    cdef public bint ignore_config
    cdef public list startup_messages

    cdef public dict tools
    cdef public dict config
    cdef public str bot_id

    cdef object _aiohttp_session
    cdef public object community_handler
    cdef public object community_auth
    cdef public object async_loop
    cdef public object tentacles_setup_config
    cdef public object stopped  # asyncio.Event
    cdef public object automation

    cdef public initializer.Initializer initializer
    cdef public task_manager.TaskManager task_manager
    cdef object _init_metadata_run_task
    cdef public producers.ExchangeProducer exchange_producer
    cdef public producers.EvaluatorProducer evaluator_producer
    cdef public producers.InterfaceProducer interface_producer
    cdef public producers.ServiceFeedProducer service_feed_producer
    cdef public octobot_api.OctoBotAPI octobot_api
    cdef public octobot_channel_consumer.OctoBotChannelGlobalConsumer global_consumer
    cdef public configuration_manager.ConfigurationManager configuration_manager

    cpdef object run_in_main_asyncio_loop(self, object coroutine, bint log_exceptions=*, object timeout=*)
    cpdef void set_watcher(self, object watcher)
    cpdef object get_aiohttp_session(self)
    cpdef object get_edited_config(self, str config_key, bint dict_only=*)
    cpdef void set_edited_config(self, str config_key, object config)
    cpdef object get_startup_config(self, str config_key, bint dict_only=*)
    cpdef object get_trading_mode(self)
