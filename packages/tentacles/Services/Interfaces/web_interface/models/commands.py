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
import threading
import time

import octobot_services.interfaces.util as interfaces_util

_PENDING_COMMANDS = set()
_REBOOT = "reboot"


def schedule_delayed_command(command, *args, delay=0.5):
    def _delayed_command():
        time.sleep(delay)
        command(*args)
    threading.Thread(target=_delayed_command).start()


def restart_bot(delay=None):
    _PENDING_COMMANDS.add(_REBOOT)
    if delay:
        # recall self with delay
        schedule_delayed_command(restart_bot, delay=delay)
        return
    _PENDING_COMMANDS.remove(_REBOOT)
    interfaces_util.get_bot_api().restart_bot()


def is_rebooting():
    return _REBOOT in _PENDING_COMMANDS


def stop_bot():
    interfaces_util.get_bot_api().stop_bot()


def update_bot():
    interfaces_util.get_bot_api().update_bot()
