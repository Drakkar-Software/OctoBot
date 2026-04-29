#  Drakkar-Software OctoBot-Tentacles-Manager
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

import octobot_commons.os_util as os_util

import octobot_tentacles_manager.constants as constants


def get_os_str() -> str:
    """
    :return: the os str
    """
    return constants.PLATFORM_TO_DOWNLOAD_PATH[os_util.get_os()]


def get_arch_str() -> str:
    """
    :param current_os: the os str
    :return: the os arch str
    """
    return "x64" if sys.maxsize > 2 ** 32 else "x86"
