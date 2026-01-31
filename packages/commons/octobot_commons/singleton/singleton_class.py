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


class Singleton:
    """
    From https://stackoverflow.com/questions/51245056/singleton-is-not-working-in-cython
    """

    _instances = {}

    @classmethod
    def instance(cls, *args, **kwargs):
        """
        Create the instance if not already created
        Return the class instance
        :param args: the constructor arguments
        :param kwargs: the constructor optional arguments
        :return: the class only instance
        """
        if cls not in cls._instances:
            cls._instances[cls] = cls(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def get_instance_if_exists(cls):
        """
        Return the instance if it exist
        Return the class instance if it exist
        :return: the class only instance if it exist otherwise None
        """
        try:
            return cls._instances[cls]
        except KeyError:
            return None
