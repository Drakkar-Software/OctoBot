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
cimport octobot.channels as octobot_channels


cdef class InterfaceProducer(octobot_channels.OctoBotChannelProducer):
    cdef public object octobot

    cdef public list interfaces
    cdef public list notifiers

    cdef int to_create_notifiers_count

    # Cython bug with all()
    # cdef bint _is_interface_relevant(self, object interface_class, bint backtesting_enabled)
    # cdef bint _is_notifier_relevant(self, object notifier_class, bint backtesting_enabled)
