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

from flask import render_template

from interfaces.web import server_instance
from interfaces.web.models.configuration import get_in_backtesting_mode
from interfaces.web.models.interface_settings import get_watched_symbols


@server_instance.route("/")
@server_instance.route("/home")
def home():
    in_backtesting = get_in_backtesting_mode()
    return render_template('index.html',
                           watched_symbols=get_watched_symbols(),
                           backtesting_mode=in_backtesting)
