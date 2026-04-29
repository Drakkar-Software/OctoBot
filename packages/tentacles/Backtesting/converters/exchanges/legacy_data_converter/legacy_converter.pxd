# cython: language_level=3
#  Drakkar-Software OctoBot-Tentacles
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
#  Lesser General License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
from octobot_backtesting.converters.data_converter cimport DataConverter
from octobot_backtesting.data.database cimport DataBase

cdef class LegacyDataConverter(DataConverter):
    cdef str exchange_name
    cdef str symbol
    cdef str time_data
    cdef list time_frames
    cdef dict file_content
    cdef DataBase database

    cdef list _get_formatted_candles(self, object time_frame)
    cdef dict _read_data_file(self)
    cdef dict _read_data_file(self)
