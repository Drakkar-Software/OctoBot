#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import os
import pathlib
import dotenv
import decimal

import octobot_commons.os_util as os_util
import octobot_commons.enums
import octobot.enums

# make constants visible
from octobot import (
    PROJECT_NAME,
    AUTHOR,
    VERSION,
    LONG_VERSION,
)

# load environment variables from .env file if exists
DOTENV_PATH = os.getenv("DOTENV_PATH", os.path.curdir)
dotenv.load_dotenv(os.path.join(DOTENV_PATH, ".env"), verbose=False)

# OctoBot urls
OCTOBOT_WEBSITE_URL = os.getenv("OCTOBOT_ONLINE_URL", "https://www.octobot.cloud")
OCTOBOT_DOCS_URL = os.getenv("DOCS_OCTOBOT_ONLINE_URL", "https://www.octobot.cloud/guides")
EXCHANGES_DOCS_URL = os.getenv("DOCS_OCTOBOT_ONLINE_URL", "https://www.octobot.cloud/guides/exchanges/")
DEVELOPER_DOCS_URL = os.getenv("DOCS_OCTOBOT_ONLINE_URL", "https://www.octobot.cloud/guides/developers/")
STATIC_OCTOBOT_ONLINE = os.getenv("TENTACLES_OCTOBOT_ONLINE_URL", "https://static.octobot.online")
OCTOBOT_FEEDBACK = os.getenv("FEEDBACK_OCTOBOT_ONLINE_URL", "https://feedback.octobot.cloud/")
TENTACLES_REPOSITORY = "tentacles"
BETA_TENTACLES_REPOSITORY = "dev-tentacles"
OFFICIALS = "officials"
TENTACLE_CATEGORY = "full"
TENTACLE_PACKAGE_NAME = "base"
BETA_TENTACLE_PACKAGE_NAME = "beta"
TENTACLE_PACKAGES = "packages"
COMPILED_TENTACLE_CATEGORY = "extra"

OCTOBOT_DONATION_URL = "https://forms.gle/Bagagc7dyjJGDT1t9"
OCTOBOT_FEEDBACK_FORM_URL = "https://goo.gl/forms/vspraniXPY7rvtKN2"
OCTOBOT_BETA_PROGRAM_FORM_URL = "https://octobot.click/docs-join-beta"
AUTOMATION_FEEDBACK_FORM_ID = "n9NKMV"
WELCOME_FEEDBACK_FORM_ID = os.getenv("WELCOME_FEEDBACK_FORM_ID", None)

COMMUNITY_FEED_CURRENT_MINIMUM_VERSION = "1.0.0"
COMMUNITY_FEED_DEFAULT_TYPE = octobot.enums.CommunityFeedType.SupabaseFeed

# production env SHOULD ONLY BE USED THROUGH CommunityIdentifiersProvider
OCTOBOT_COMMUNITY_LANDING_URL = os.getenv("COMMUNITY_SERVER_URL", "https://octobot.cloud")
OCTOBOT_COMMUNITY_URL = os.getenv("COMMUNITY_SERVER_URL", "https://app.octobot.cloud")
OCTOBOT_COMMUNITY_RECOVER_PASSWORD_URL = OCTOBOT_COMMUNITY_URL
# default env
COMMUNITY_BACKEND_URL = os.getenv("COMMUNITY_BACKEND_URL", "https://nwhpvrguwcihhizrnyoe.supabase.co")
COMMUNITY_BACKEND_KEY = os.getenv("COMMUNITY_BACKEND_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im53aHB2cmd1d2NpaGhpenJueW9lIiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTU2NDQxMDcsImV4cCI6MjAxMTIyMDEwN30.AILcgv0l6hl_0IUEPlWh1wiu9RIpgrkGZGERM5uXftE")

# staging env SHOULD ONLY BE USED THROUGH CommunityIdentifiersProvider
STAGING_OCTOBOT_COMMUNITY_LANDING_URL = os.getenv("COMMUNITY_SERVER_URL", "https://beta.octobot.cloud")
STAGING_OCTOBOT_COMMUNITY_URL = os.getenv("COMMUNITY_SERVER_URL", "https://app-beta.octobot.cloud/")
STAGING_COMMUNITY_RECOVER_PASSWORD_URL = STAGING_OCTOBOT_COMMUNITY_URL
STAGING_COMMUNITY_BACKEND_URL = os.getenv("COMMUNITY_BACKEND_URL", "https://wmfkgvgzokyzhvxowbyg.supabase.co")
STAGING_COMMUNITY_BACKEND_KEY = os.getenv("COMMUNITY_BACKEND_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndtZmtndmd6b2t5emh2eG93YnlnIiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTE0NDA1MTEsImV4cCI6MjAwNzAxNjUxMX0.YZQl7LYgvnzO_Jizs0UKfPEaqPoV2EwhjunH8gime8o")

# production env, ignored by CommunityIdentifiersProvider
COMMUNITY_PRODUCTION_BACKEND_URL = os.getenv("COMMUNITY_PRODUCTION_BACKEND_URL", COMMUNITY_BACKEND_URL)
COMMUNITY_PRODUCTION_BACKEND_KEY = os.getenv("COMMUNITY_PRODUCTION_BACKEND_KEY", COMMUNITY_BACKEND_KEY)

CONFIG_COMMUNITY = "community"
CONFIG_COMMUNITY_BOT_ID = "bot_id"
CONFIG_COMMUNITY_ENVIRONMENT = "environment"
USE_BETA_EARLY_ACCESS = os_util.parse_boolean_environment_var("USE_BETA_EARLY_ACCESS", "false")
USER_ACCOUNT_EMAIL = os.getenv("USER_ACCOUNT_EMAIL", "")
USER_PASSWORD_TOKEN = os.getenv("USER_PASSWORD_TOKEN", None)
COMMUNITY_BOT_ID = os.getenv("COMMUNITY_BOT_ID", "")
IS_DEMO = os_util.parse_boolean_environment_var("IS_DEMO", "False")
IS_CLOUD_ENV = os_util.parse_boolean_environment_var("IS_CLOUD_ENV", "false")
CAN_INSTALL_TENTACLES = os_util.parse_boolean_environment_var("CAN_INSTALL_TENTACLES", str(not IS_CLOUD_ENV))
TRACKING_ID = os.getenv("TRACKING_ID", "eoe1stwyun" if IS_DEMO else "eoe06soct7" if IS_CLOUD_ENV else "f726lk9q59")
# Profiles download urls to import at startup if missing, split by ","
TO_DOWNLOAD_PROFILES = os.getenv("TO_DOWNLOAD_PROFILES", None)
# Profiles to force select at startup, identified by profile id, download url or name
FORCED_PROFILE = os.getenv("FORCED_PROFILE", None)
RUN_IN_MAIN_THREAD = os.getenv("RUN_IN_MAIN_THREAD", False)

OCTOBOT_BINARY_PROJECT_NAME = "OctoBot-Binary"

# limits
UNLIMITED_ALLOWED = -1
MAX_ALLOWED_EXCHANGES = int(os.getenv("MAX_ALLOWED_EXCHANGES", str(UNLIMITED_ALLOWED)))
MAX_ALLOWED_SYMBOLS = int(os.getenv("MAX_ALLOWED_SYMBOLS", str(UNLIMITED_ALLOWED)))
MAX_ALLOWED_TIME_FRAMES = int(os.getenv("MAX_ALLOWED_TIME_FRAMES", str(UNLIMITED_ALLOWED)))
MAX_ALLOWED_BACKTESTING_CANDLES_HISTORY = int(os.getenv("MAX_ALLOWED_BACKTESTING_CANDLES_HISTORY",
                                                        str(UNLIMITED_ALLOWED)))
ENABLE_AUTOMATIONS = os_util.parse_boolean_environment_var("ENABLE_AUTOMATIONS", "True")
ENABLE_BACKTESTING = os_util.parse_boolean_environment_var("ENABLE_BACKTESTING", "True")
ENABLE_ADVANCED_INTERFACE = os_util.parse_boolean_environment_var("ENABLE_ADVANCED_INTERFACE", "True")
ENABLE_STRATEGY_OPTIMIZER = os_util.parse_boolean_environment_var("ENABLE_STRATEGY_OPTIMIZER", "True")

# tentacles
ENV_TENTACLES_URL = "TENTACLES_URL"
ENV_COMPILED_TENTACLES_URL = "COMPILED_TENTACLES_URL"
ENV_TENTACLES_REPOSITORY = "TENTACLES_REPOSITORY"
ENV_BETA_TENTACLES_REPOSITORY = "BETA_TENTACLES_REPOSITORY"
ENV_TENTACLES_URL_TAG = "TENTACLES_URL_TAG"
ENV_TENTACLE_PACKAGE_NAME = "TENTACLE_PACKAGE_NAME"
ENV_BETA_TENTACLES_PACKAGE_NAME = "BETA_TENTACLES_PACKAGE_NAME"
ENV_TENTACLES_PACKAGES_TYPE = "TENTACLES_PACKAGES_TYPE"
ENV_TENTACLES_PACKAGES_SOURCE = "TENTACLES_PACKAGES_SOURCE"
ENV_COMPILED_TENTACLES_CATEGORY = "COMPILED_TENTACLES_CATEGORY"
ENV_COMPILED_TENTACLES_PACKAGES_TYPE = "COMPILED_TENTACLES_PACKAGES_TYPE"
ENV_TENTACLE_CATEGORY = "TENTACLE_CATEGORY"
ENV_COMPILED_TENTACLES_SUBCATEGORY = "COMPILED_TENTACLES_SUBCATEGORY"
TENTACLES_REQUIRED_VERSION = f"{os.getenv(ENV_TENTACLES_URL_TAG, LONG_VERSION)}"
# VERSION_PLACEHOLDER will be replaced by the current OctoBot version in ADDITIONAL_TENTACLES_PACKAGE_URL
# ADDITIONAL_TENTACLES_PACKAGE_URL can contain multiple urls separated by a ","
ADDITIONAL_TENTACLES_PACKAGE_URL = os.getenv("ADDITIONAL_TENTACLES_PACKAGE_URL", None)
# url example: 	https://plop.fr/tentacles/123/latest/any_platform.zip
# url example: 	https://plop.fr/tentacles/.../VERSION_PLACEHOLDER/any_platform.zip,https://plop.fr/any_platform.zip
VERSION_PLACEHOLDER = "VERSION_PLACEHOLDER"
URL_SEPARATOR = ","

DEFAULT_TENTACLES_PACKAGE_NAME = "OctoBot-Default-Tentacles"

# logs
LOGS_FOLDER = "logs"
ENV_TRADING_ENABLE_DEBUG_LOGS = os_util.parse_boolean_environment_var("ENV_TRADING_ENABLE_DEBUG_LOGS", "False")

# system
ENABLE_CLOCK_SYNCH = os_util.parse_boolean_environment_var("ENABLE_CLOCK_SYNCH", "True")
ENABLE_SYSTEM_WATCHER = os_util.parse_boolean_environment_var("ENABLE_SYSTEM_WATCHER", "True")
DUMP_USED_RESOURCES = os_util.parse_boolean_environment_var("DUMP_USED_RESOURCES", "False")
USED_RESOURCES_OUTPUT = os.getenv("USED_RESOURCES_OUTPUT", "system_resources.csv")

# errors
ERRORS_URL = os.getenv("ERRORS_OCTOBOT_ONLINE_URL", "https://errors.octobot.online/")
ERRORS_POST_ENDPOINT = f"{ERRORS_URL}errors"
UPLOAD_ERRORS = os_util.parse_boolean_environment_var("UPLOAD_ERRORS", "False")
DEFAULT_METRICS_ID = "UNSET"

# config types keys
CONFIG_KEY = "config"
TENTACLES_SETUP_CONFIG_KEY = "tentacles_setup"

# terms of service
CONFIG_ACCEPTED_TERMS = "accepted_terms"

# DEBUG
CONFIG_DEBUG_OPTION = "DEV-MODE"
FORCE_ASYNCIO_DEBUG_OPTION = False
EXIT_BEFORE_TENTACLES_AUTO_REINSTALL = os_util.parse_boolean_environment_var("EXIT_BEFORE_TENTACLES_AUTO_REINSTALL", "False")

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
OPTIMIZATION_CAMPAIGN_KEY = "optimization_campaign"

OPTIMIZER_RUNS_FOLDER = "optimizer"
OPTIMIZER_DEFAULT_RANDOMLY_CHOSE_RUNS = True
OPTIMIZER_DEFAULT_REQUIRED_IDLE_CORES = 0
OPTIMIZER_DEFAULT_NOTIFY_WHEN_COMPLETE = False
OPTIMIZER_DEFAULT_QUEUE_SIZE = 10000
OPTIMIZER_DEFAULT_MAX_OPTIMIZER_RUNS = 100000
OPTIMIZER_DEFAULT_GENERATIONS_COUNT = 10
OPTIMIZER_DEFAULT_INITIAL_GENERATION_COUNT = OPTIMIZER_DEFAULT_GENERATIONS_COUNT
OPTIMIZER_DEFAULT_RUN_PER_GENERATION = 80
OPTIMIZER_DEFAULT_MUTATION_PERCENT = 20
OPTIMIZER_DEFAULT_MAX_MUTATION_PROBABILITY_PERCENT = decimal.Decimal(95)
OPTIMIZER_DEFAULT_MIN_MUTATION_PROBABILITY_PERCENT = decimal.Decimal(10)
OPTIMIZER_DEFAULT_MAX_MUTATION_NUMBER_MULTIPLIER = 3
OPTIMIZER_DEFAULT_DB_UPDATE_PERIOD = 15

# Databases
DEFAULT_MAX_TOTAL_RUN_DATABASES_SIZE = 1000000000   # 1GB
ENABLE_RUN_DATABASE_LIMIT = os_util.parse_boolean_environment_var("ENABLE_RUN_DATABASE_LIMIT", "True")
MAX_TOTAL_RUN_DATABASES_SIZE = int(os.getenv("MAX_TOTAL_RUN_DATABASES_SIZE", DEFAULT_MAX_TOTAL_RUN_DATABASES_SIZE))

# Channel
OCTOBOT_CHANNEL = "OctoBot"

# Initialization
REQUIRED_TOPIC_FOR_DATA_INIT = [
    octobot_commons.enums.InitializationEventExchangeTopics.CANDLES,
    octobot_commons.enums.InitializationEventExchangeTopics.CONTRACTS,
    octobot_commons.enums.InitializationEventExchangeTopics.PRICE,
    octobot_commons.enums.InitializationEventExchangeTopics.BALANCE,
]

OCTOBOT_KEY = b'uVEw_JJe7uiXepaU_DR4T-ThkjZlDn8Pzl8hYPIv7w0='
