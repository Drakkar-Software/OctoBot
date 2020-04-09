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

PROJECT_NAME = "OctoBot"
SHORT_VERSION = "0.4.0"  # major.minor.revision
PATCH_VERSION = ""  # patch : pX
VERSION_DEV_PHASE = "a"  # alpha : a / beta : b / release candidate : rc
VERSION_PHASE = "8"  # XX
VERSION = f"{SHORT_VERSION}{VERSION_DEV_PHASE}{VERSION_PHASE}"
LONG_VERSION = f"{SHORT_VERSION}{PATCH_VERSION}{VERSION_DEV_PHASE}{VERSION_PHASE}"

# OctoBot urls
OCTOBOT_ONLINE = "https://www.tentacles.octobot.online"
REPOSITORY = "repository"
TENTACLES_REPOSITORY = "tentacles"
RELEASES = "releases"

# tentacles
DEFAULT_TENTACLES_URL = f"{OCTOBOT_ONLINE}/{REPOSITORY}/{TENTACLES_REPOSITORY}/{RELEASES}/{LONG_VERSION}.zip"
DEFAULT_TENTACLES_PACKAGE_NAME = "OctoBot-Default-Tentacles"

# logs
LOGS_FOLDER = "logs"

# config types keys
CONFIG_KEY = "config"
TENTACLES_SETUP_CONFIG_KEY = "tentacles_setup"

# terms of service
CONFIG_ACCEPTED_TERMS = "accepted_terms"

# DEBUG
CONFIG_DEBUG_OPTION = "DEV-MODE"
FORCE_ASYNCIO_DEBUG_OPTION = False

# Files
CONFIG_FILE = "config.json"
TEMP_RESTORE_CONFIG_FILE = "temp_config.json"
CONFIG_FOLDER = "config"
SCHEMA = "schema"
CONFIG_FILE_SCHEMA = f"{CONFIG_FOLDER}/config_{SCHEMA}.json"
DEFAULT_CONFIG_FILE = f"{CONFIG_FOLDER}/default_config.json"
LOGGING_CONFIG_FILE = f"{CONFIG_FOLDER}/logging_config.ini"
LOG_FILE = f"{LOGS_FOLDER}/{PROJECT_NAME}.log"

OCTOBOT_KEY = b'uVEw_JJe7uiXepaU_DR4T-ThkjZlDn8Pzl8hYPIv7w0='
