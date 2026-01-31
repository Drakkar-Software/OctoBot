#  Drakkar-Software Async-Channel
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
"""
Define async_channel logger implementation
"""
import logging


# pylint: disable=no-member, import-outside-toplevel
def get_logger(name: str = "") -> logging.Logger:
    """
    :param name: the logger name
    :return: the logger implementation, can be octobot_commons one or default python logging
    """
    try:
        import octobot_commons.logging as common_logging

        return common_logging.get_logger(logger_name=name)
    except ImportError:
        return logging.getLogger(name)
