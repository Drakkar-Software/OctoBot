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


cdef class TaskManager:
    cdef object logger
    cdef public object octobot
    cdef public object async_loop
    cdef public object watcher
    cdef public object tools_task_group
    cdef public object current_loop_thread
    cdef public object bot_main_task
    cdef public object loop_forever_thread
    cdef public object executors

    cdef public bint ready

    cdef void _create_new_asyncio_main_loop(self)
    cdef void _loop_exception_handler(self, object loop, object context)

    cpdef void run_bot_in_thread(self, object coroutine)
    cpdef void run_forever(self, object coroutine)
    cpdef void create_pool_executor(self, int workers=*)
    cpdef void init_async_loop(self)
    cpdef object run_in_main_asyncio_loop(self, object coroutine)