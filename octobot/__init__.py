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

from __future__ import print_function
from distutils.version import LooseVersion
import os
import sys

MIN_TENTACLE_MANAGER_VERSION = "1.0.10"

# check compatible tentacle manager
try:
    from octobot_tentacles_manager import VERSION
    if LooseVersion(VERSION) < MIN_TENTACLE_MANAGER_VERSION:
        print("OctoBot requires OctoBot-Tentacles-Manager in a minimum version of " + MIN_TENTACLE_MANAGER_VERSION +
              " you can install and update OctoBot-Tentacles-Manager using the following command: "
              "python3 -m pip install -U OctoBot-Tentacles-Manager", file=sys.stderr)
        sys.exit(-1)
except ImportError:
    print("OctoBot requires OctoBot-Tentacles-Manager, you can install it using "
          "python3 -m pip install -U OctoBot-Tentacles-Manager", file=sys.stderr)
    sys.exit(-1)

# binary tentacle importation
sys.path.append(os.path.dirname(sys.executable))

bot_instance = None
global_config = None


def __init__(bot, config):
    global bot_instance
    bot_instance = bot

    global global_config
    global_config = config


# TODO: find a better way to keep track of the bot instance in octobot module
def set_bot(bot):
    global bot_instance
    bot_instance = bot


def get_bot():
    return bot_instance


def get_config():
    return global_config
