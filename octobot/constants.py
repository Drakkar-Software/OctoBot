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
import os
import pathlib

PROJECT_NAME = "OctoBot"
SHORT_VERSION = "0.4.0"  # major.minor.revision
PATCH_VERSION = ""  # patch : pX
VERSION_DEV_PHASE = "a"  # alpha : a / beta : b / release candidate : rc
VERSION_PHASE = "18"  # XX
VERSION = f"{SHORT_VERSION}{VERSION_DEV_PHASE}{VERSION_PHASE}"
LONG_VERSION = f"{SHORT_VERSION}{PATCH_VERSION}{VERSION_DEV_PHASE}{VERSION_PHASE}"

# OctoBot urls
OCTOBOT_ONLINE = "https://www.tentacles.octobot.online"
REPOSITORY = "repository"
TENTACLES_REPOSITORY = "tentacles"
OFFICIALS = "officials"
TENTACLE_BASE_CATEGORY = "base"

# tentacles
ENV_TENTACLES_URL = "TENTACLES_URL"
ENV_TENTACLES_URL_TAG = "TENTACLES_URL_TAG"
ENV_TENTACLES_URL_CATEGORY = "TENTACLES_URL_CATEGORY"
ENV_TENTACLES_URL_SUBCATEGORY = "TENTACLES_URL_SUBCATEGORY"
DEFAULT_TENTACLES_URL = os.getenv(ENV_TENTACLES_URL,
                                  f"{OCTOBOT_ONLINE}/{REPOSITORY}/{TENTACLES_REPOSITORY}/{OFFICIALS}/"
                                  f"{os.getenv(ENV_TENTACLES_URL_CATEGORY, TENTACLE_BASE_CATEGORY)}/"
                                  f"{os.getenv(ENV_TENTACLES_URL_SUBCATEGORY, '')}"
                                  f"{os.getenv(ENV_TENTACLES_URL_TAG, LONG_VERSION)}.zip")
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
# Store the path of the octobot directory from this file since it can change depending on the installation path
# (local sources, python site-packages, ...)
OCTOBOT_FOLDER = pathlib.Path(__file__).parent.absolute()
CONFIG_FOLDER = f"{OCTOBOT_FOLDER}/config"
SCHEMA = "schema"
CONFIG_FILE_SCHEMA = f"{CONFIG_FOLDER}/config_{SCHEMA}.json"
DEFAULT_CONFIG_FILE = f"{CONFIG_FOLDER}/default_config.json"
LOGGING_CONFIG_FILE = f"{CONFIG_FOLDER}/logging_config.ini"
LOG_FILE = f"{LOGS_FOLDER}/{PROJECT_NAME}.log"

# Optimizer
OPTIMIZER_FORCE_ASYNCIO_DEBUG_OPTION = False
OPTIMIZER_DATA_FILES_FOLDER = f"{OCTOBOT_FOLDER}/strategy_optimizer/optimizer_data_files"

# Channel
OCTOBOT_CHANNEL = "OctoBot"

OCTOBOT_KEY = b'uVEw_JJe7uiXepaU_DR4T-ThkjZlDn8Pzl8hYPIv7w0='
