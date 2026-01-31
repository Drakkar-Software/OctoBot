#  Drakkar-Software OctoBot-Commons
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
import sys

import octobot_commons.singleton as singleton


class GlobalSharedMemoryStorage(dict, singleton.Singleton):
    """
    A global singleton dict available to the whole python virtual machine.
    Warnings:
        only stored in RAM, not persisted on disc
        not thread safe
    """

    def remove_oldest_elements(self, elements_count_to_remove: int):
        """
        Remove (pop) the elements_count_to_remove oldest elements
        :param elements_count_to_remove: number of elements to remove
        """
        for key in list(self.keys())[:elements_count_to_remove]:
            self.pop(key)

    def get_bytes_size(self):
        """
        Return the size in bytes of the memory storage
        """
        return sys.getsizeof(self)
