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

from logging.handlers import RotatingFileHandler
from os import path
from config import PROJECT_ROOT_DIR


"""
Local RotatingFileHandler extension to write logs into the OctoBot directory regardless of the current terminal 
working directory.
"""


class LocalRotatingFileHandler(RotatingFileHandler):
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=False):
        super().__init__(path.join(PROJECT_ROOT_DIR, filename),
                         mode=mode,
                         maxBytes=maxBytes,
                         backupCount=backupCount,
                         encoding=encoding,
                         delay=delay)
