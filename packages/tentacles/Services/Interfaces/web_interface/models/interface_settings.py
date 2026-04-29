#  Drakkar-Software OctoBot-Interfaces
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

import octobot_trading.constants as trading_constants
import octobot_services.interfaces.util as interfaces_util
import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.enums as web_enums
import tentacles.Services.Interfaces.web_interface.models.configuration as configuration_model


def get_watched_symbols():
    config = get_web_interface_config()
    try:
        return config[web_interface.WebInterface.WATCHED_SYMBOLS]
    except KeyError:
        config[web_interface.WebInterface.WATCHED_SYMBOLS] = []
    return config[web_interface.WebInterface.WATCHED_SYMBOLS]


def add_watched_symbol(symbol):
    watched_symbols = get_watched_symbols()
    if symbol not in watched_symbols:
        watched_symbols.append(symbol)
        return _save_edition()[0]
    return True


def remove_watched_symbol(symbol):
    watched_symbols = get_watched_symbols()
    try:
        watched_symbols.remove(symbol)
        return _save_edition()[0]
    except ValueError:
        return True


def set_color_mode(color_mode: str):
    try:
        get_web_interface_config()[
            web_interface.WebInterface.COLOR_MODE
        ] = web_enums.ColorModes(color_mode).value
    except ValueError:
        return False, f"invalid color mode: {color_mode}"
    return _save_edition()


def set_display_announcement(key: str, display: bool):
    try:
        get_web_interface_config()[
            web_interface.WebInterface.ANNOUNCEMENTS
        ][key] = display
    except KeyError:
        get_web_interface_config()[
            web_interface.WebInterface.ANNOUNCEMENTS
        ] = {key: display}
    return _save_edition()


def get_display_announcement(key: str) -> bool:
    try:
        return get_web_interface_config()[
            web_interface.WebInterface.ANNOUNCEMENTS
        ][key]
    except KeyError:
        return True


def get_color_mode() -> web_enums.ColorModes:
    return web_enums.ColorModes(get_web_interface_config().get(
        web_interface.WebInterface.COLOR_MODE, web_enums.ColorModes.DEFAULT.value
    ))


def get_display_timeframe():
    return get_web_interface_config().get(
        web_interface.WebInterface.DISPLAY_TIME_FRAME,
        trading_constants.DISPLAY_TIME_FRAME.value
    )


def get_display_orders():
    return get_web_interface_config().get(web_interface.WebInterface.DISPLAY_ORDERS, True)


def set_display_timeframe(time_frame):
    get_web_interface_config()[
        web_interface.WebInterface.DISPLAY_TIME_FRAME
    ] = time_frame
    return _save_edition()


def set_display_orders(display_orders):
    get_web_interface_config()[
        web_interface.WebInterface.DISPLAY_ORDERS
    ] = display_orders
    return _save_edition()


def get_web_interface_config():
    try:
        return get_web_interface().local_config
    except AttributeError:
        return {}


def _save_edition():
    success, message = configuration_model.update_tentacle_config(
        web_interface.WebInterface.get_name(),
        get_web_interface().local_config,
        tentacle_class=web_interface.WebInterface
    )
    reload_config()
    return success, message


def reload_config():
    get_web_interface().reload_config()


def get_web_interface():
    return interfaces_util.get_bot_api().get_interface(web_interface.WebInterface)
