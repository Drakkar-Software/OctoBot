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

cdef class OctoBotAPI:

    cdef object _octobot

    cpdef bint is_initialized(self)
    cpdef list get_exchange_manager_ids(self)
    cpdef dict get_global_config(self)
    cpdef object get_startup_tentacles_config(self)
    cpdef object get_edited_tentacles_config(self)
    cpdef void set_edited_tentacles_config(self, object config)
    cpdef object get_startup_config(self)
    cpdef object get_edited_config(self, bint dict_only=*)
    cpdef void set_edited_tentacles_config(self, object config)
    cpdef object get_trading_mode(self)
    cpdef double get_start_time(self)
    cpdef str get_bot_id(self)
    cpdef str get_matrix_id(self)
    cpdef object get_aiohttp_session(self)
    cpdef object run_in_main_asyncio_loop(self, object coroutine)
    cpdef void stop_tasks(self)
    cpdef void stop_bot(self)
    cpdef void update_bot(self)
