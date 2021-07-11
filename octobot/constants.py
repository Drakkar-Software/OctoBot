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
AUTHOR = "DrakkarSoftware"
SHORT_VERSION = "0.4.0"  # major.minor.revision
PATCH_VERSION = ""  # patch : pX
VERSION_DEV_PHASE = "b"  # alpha : a / beta : b / release candidate : rc
VERSION_PHASE = "11"  # XX
VERSION = f"{SHORT_VERSION}{VERSION_DEV_PHASE}{VERSION_PHASE}"
LONG_VERSION = f"{SHORT_VERSION}{PATCH_VERSION}{VERSION_DEV_PHASE}{VERSION_PHASE}"

# OctoBot urls
OCTOBOT_WEBSITE_URL = os.getenv("OCTOBOT_ONLINE_URL", "https://www.octobot.online")
OCTOBOT_DOCS_URL = os.getenv("DOCS_OCTOBOT_ONLINE_URL", "https://docs.octobot.online")
OCTOBOT_ONLINE = os.getenv("TENTACLES_OCTOBOT_ONLINE_URL", "https://tentacles.octobot.online")
OCTOBOT_FEEDBACK = os.getenv("FEEDBACK_OCTOBOT_ONLINE_URL", "https://feedback.octobot.online/")
REPOSITORY = "repository"
TENTACLES_REPOSITORY = "tentacles"
OFFICIALS = "officials"
TENTACLE_CATEGORY = "full"
TENTACLE_PACKAGE_NAME = "base"
TENTACLE_PACKAGES = "packages"
COMPILED_TENTACLE_CATEGORY = "extra"

DEFAULT_COMMUNITY_URL = "TODO"
OCTOBOT_COMMUNITY_URL = os.getenv("COMMUNITY_SERVER_URL", DEFAULT_COMMUNITY_URL)
OCTOBOT_COMMUNITY_AUTH_URL = f"{OCTOBOT_COMMUNITY_URL}spree_oauth/token"
OCTOBOT_COMMUNITY_ACCOUNT_URL = f"{OCTOBOT_COMMUNITY_URL}api/v2/storefront/account"
OCTOBOT_COMMUNITY_PACKAGES_URL = f"{OCTOBOT_COMMUNITY_URL}api/v2/storefront/tentacle/packages"

OCTOBOT_BINARY_PROJECT_NAME = "OctoBot-Binary"

# tentacles
ENV_TENTACLES_URL = "TENTACLES_URL"
ENV_COMPILED_TENTACLES_URL = "COMPILED_TENTACLES_URL"
ENV_TENTACLES_REPOSITORY = "TENTACLES_REPOSITORY"
ENV_TENTACLES_URL_TAG = "TENTACLES_URL_TAG"
ENV_TENTACLE_PACKAGE_NAME = "TENTACLE_PACKAGE_NAME"
ENV_TENTACLES_PACKAGES_TYPE = "TENTACLES_PACKAGES_TYPE"
ENV_TENTACLES_PACKAGES_SOURCE = "TENTACLES_PACKAGES_SOURCE"
ENV_COMPILED_TENTACLES_CATEGORY = "COMPILED_TENTACLES_CATEGORY"
ENV_COMPILED_TENTACLES_PACKAGES_TYPE = "COMPILED_TENTACLES_PACKAGES_TYPE"
ENV_TENTACLE_CATEGORY = "TENTACLE_CATEGORY"
ENV_COMPILED_TENTACLES_SUBCATEGORY = "COMPILED_TENTACLES_SUBCATEGORY"
TENTACLES_REQUIRED_VERSION = f"{os.getenv(ENV_TENTACLES_URL_TAG, LONG_VERSION)}"
# url ending example: 	tentacles/officials/packages/full/base/latest/any_platform.zip

DEFAULT_TENTACLES_PACKAGE_NAME = "OctoBot-Default-Tentacles"

# logs
LOGS_FOLDER = "logs"
ENV_ENABLE_DEBUG_LOGS = "ENABLE_DEBUG_LOGS"

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
PROFILE_FILE_SCHEMA = f"{CONFIG_FOLDER}/profile_{SCHEMA}.json"
DEFAULT_CONFIG_FILE = f"{CONFIG_FOLDER}/default_config.json"
DEFAULT_PROFILE_FILE = f"{CONFIG_FOLDER}/default_profile.json"
DEFAULT_PROFILE_AVATAR_FILE_NAME = "default_profile.png"
DEFAULT_PROFILE_AVATAR = f"{CONFIG_FOLDER}/{DEFAULT_PROFILE_AVATAR_FILE_NAME}"
LOGGING_CONFIG_FILE = f"{CONFIG_FOLDER}/logging_config.ini"
LOG_FILE = f"{LOGS_FOLDER}/{PROJECT_NAME}.log"

# Optimizer
OPTIMIZER_FORCE_ASYNCIO_DEBUG_OPTION = False
OPTIMIZER_DATA_FILES_FOLDER = f"{OCTOBOT_FOLDER}/strategy_optimizer/optimizer_data_files"

# Channel
OCTOBOT_CHANNEL = "OctoBot"

OCTOBOT_KEY = b'uVEw_JJe7uiXepaU_DR4T-ThkjZlDn8Pzl8hYPIv7w0='
