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

cimport octobot.updater.updater as updater_class

cdef class BinaryUpdater(updater_class.Updater):
    cdef str _get_latest_release_url(self)
    cdef object _parse_latest_version(self, object latest_release_data)
    cdef str _create_release_asset_name(self, object platform)
    cdef void _give_execution_rights(self, str new_binary_file)
