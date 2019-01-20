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

import logging
import os
import sys

from config import PlatformsName, get_os

MIN_PYTHON_VERSION = (3, 7)

# check python version
current_version = sys.version_info
if not current_version >= MIN_PYTHON_VERSION:
    logging.error(" OctoBot requires Python version to be higher or equal to Python " + str(MIN_PYTHON_VERSION[0])
                  + "." + str(MIN_PYTHON_VERSION[1]) + " current Python version is " + str(current_version[0])
                  + "." + str(current_version[1]) + "\n"
                  + "You can download Python last versions on: https://www.python.org/downloads/")
    sys.exit(-1)

# binary tentacle importation
sys.path.append(os.path.dirname(sys.executable))

# if compatible version, can proceed with imports

# check sudo rights
if get_os() is not PlatformsName.WINDOWS and os.getuid() == 0:
    logging.warning("OctoBot is started with admin / sudo rights that are not required, "
                    "please check you starting command ")
