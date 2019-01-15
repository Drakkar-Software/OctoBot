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

try:
    from interfaces.gui.app.main_app import MainApp
except ModuleNotFoundError as e:
    logging.error(f"Can't find {e}, impossible to load GUI")
except ImportError as e:
    logging.error(f"Can't find {e}, impossible to load GUI")

main_app = None


def __init__(config):
    global main_app
    main_app = MainApp(config)
