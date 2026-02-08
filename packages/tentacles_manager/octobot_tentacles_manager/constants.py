#  Drakkar-Software OctoBot-Tentacles-Manager
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
import os.path as path
import octobot_commons.constants as constants
import octobot_commons.enums as enums

CURRENT_DIR_PATH = os.getcwd()

# Default tests tentacles URL
OCTOBOT_ONLINE = os.getenv("TENTACLES_OCTOBOT_ONLINE_URL", "https://tentacles.octobot.online")
DEFAULT_TENTACLES_URL = f"{OCTOBOT_ONLINE}/officials/packages/full/base/0.4.0b16/any_platform.zip"
DEFAULT_BOT_INSTALL_DIR = CURRENT_DIR_PATH

# Tentacles files
PYTHON_INIT_FILE = "__init__.py"
CYTHON_HEADER_INIT_FILE = "__init__.pxd"
PYTHON_EXT = ".py"
CYTHON_EXT = ".pxd"
CONFIG_EXT = ".json"
DOCUMENTATION_EXT = ".md"
CONFIG_SCHEMA_EXT = "_schema.json"
TENTACLE_METADATA = "metadata.json"
TENTACLE_CONFIG_FILE_NAME = "default_tentacles_config.json"
DEFAULT_TENTACLE_CONFIG = path.join(constants.CONFIG_FOLDER, TENTACLE_CONFIG_FILE_NAME)

# tentacles setup folders back list
FOLDERS_BLACK_LIST = ["__pycache__"]

# Metadata keys
METADATA_VERSION = "version"
METADATA_TENTACLES = "tentacles"
METADATA_ORIGIN_PACKAGE = "origin_package"
METADATA_DEV_MODE = "dev_mode"
METADATA_TENTACLES_REQUIREMENTS = "tentacles-requirements"
METADATA_TENTACLES_GROUP = "tentacles_group"
METADATA_BUILD = "build"
METADATA_INCLUDE = "include"

# Files that should always be included in tentacles export
ALWAYS_INCLUDED_TENTACLE_FILES = ["metadata.json", "__init__.py"]

# Artifact metadata
ARTIFACT_METADATA_FILE = "metadata.yaml"
ARTIFACT_METADATA_VERSION = "version"
ARTIFACT_METADATA_NAME = "name"
ARTIFACT_METADATA_SHORT_NAME = "short-name"
ARTIFACT_METADATA_ARTIFACT_TYPE = "type"
ARTIFACT_METADATA_REPOSITORY = "repository"
ARTIFACT_METADATA_AUTHOR = "author"
ARTIFACT_METADATA_DESCRIPTION = "description"
ARTIFACT_METADATA_TAGS = "tags"
ARTIFACT_METADATA_TENTACLES = "tentacles"
DEFAULT_ARTIFACT_METADATA_AUTHOR = "DrakkarSoftware"

# Requirements
TENTACLE_REQUIREMENT_VERSION_EQUALS = "=="

# Tentacle user config files and folders
USER_REFERENCE_TENTACLE_CONFIG_PATH = path.join(constants.USER_FOLDER, "reference_tentacles_config")
USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH = path.join(USER_REFERENCE_TENTACLE_CONFIG_PATH,
                                                     constants.CONFIG_TENTACLES_FILE)
TENTACLES_SPECIFIC_CONFIG_FOLDER = "specific_config"
USER_REFERENCE_TENTACLE_SPECIFIC_CONFIG_PATH = path.join(USER_REFERENCE_TENTACLE_CONFIG_PATH,
                                                         TENTACLES_SPECIFIC_CONFIG_FOLDER)

# Current minimum default tentacles version
TENTACLE_CURRENT_MINIMUM_DEFAULT_TENTACLES_VERSION = "1.2.0"
DEFAULT_TENTACLES_PACKAGE = "OctoBot-Default-Tentacles"

# Tentacles repository
UNKNOWN_REPOSITORY_LOCATION = "Unknown repository location"

# Tentacles packages
UNKNOWN_TENTACLES_PACKAGE_LOCATION = "Unknown package location"
TENTACLES_PACKAGE_PROFILES_PATH = "profiles"

# exporter
DEFAULT_EXPORT_DIR = "output"
ANY_PLATFORM_FILE_NAME = "any_platform"

# Artifacts
UNKNOWN_ARTIFACT_VERSION = "unknown_version"
ARTIFACT_VERSION_SEPARATOR = "@"
ARTIFACT_VERSION_DOT_REPLACEMENT = "~"

# Tentacles installation folders
TENTACLES_INSTALL_TEMP_DIR = "temp_tentacles"
TENTACLES_REQUIREMENTS_INSTALL_TEMP_DIR = "requirements_temp_tentacles"
TENTACLES_ARCHIVE_ROOT = "reference_tentacles"
TO_REMOVE_FOLDER = "_to_rm"

# Tentacles folders
TENTACLES_PATH = "tentacles"
DEFAULT_BOT_PATH = CURRENT_DIR_PATH
# TENTACLES_AGENTS_PATH = "Agent"
TENTACLES_AUTOMATION_PATH = "Automation"
TENTACLES_BACKTESTING_PATH = "Backtesting"
TENTACLES_EVALUATOR_PATH = "Evaluator"
TENTACLES_META_PATH = "Meta"
TENTACLES_PROFILES_PATH = "profiles"
TENTACLES_INTERFACES_PATH = "Interfaces"
TENTACLES_NOTIFIERS_PATH = "Notifiers"
TENTACLES_SERVICES_PATH = "Services"
TENTACLES_SERVICES_BASES_PATH = "Services_bases"
TENTACLES_SERVICES_FEEDS_PATH = "Services_feeds"
TENTACLES_TRADING_PATH = "Trading"

# Tentacles sub-folders
TENTACLE_MAX_SUB_FOLDERS_LEVEL = 3
TENTACLES_AGENTS_EVALUATORS_PATH = "Evaluators"
TENTACLES_AGENTS_TRADING_PATH = "Trading"
TENTACLES_AGENTS_TEAMS_PATH = "Teams"
TENTACLES_AUTOMATION_TRIGGER_EVENTS_PATH = "trigger_events"
TENTACLES_AUTOMATION_CONDITIONS_PATH = "conditions"
TENTACLES_AUTOMATION_ACTIONS_PATH = "actions"
TENTACLES_BACKTESTING_COLLECTORS_PATH = "collectors"
TENTACLES_BACKTESTING_CONVERTERS_PATH = "converters"
TENTACLES_BACKTESTING_IMPORTERS_PATH = "importers"
TENTACLES_BACKTESTING_THIRD_LEVEL_EXCHANGES_PATH = "exchanges"
TENTACLES_BACKTESTING_THIRD_LEVEL_SOCIAL_PATH = "social"
TENTACLES_EVALUATOR_REALTIME_PATH = "RealTime"
TENTACLES_EVALUATOR_TA_PATH = "TA"
TENTACLES_EVALUATOR_SCRIPTED_PATH = "Scripted"
TENTACLES_EVALUATOR_SOCIAL_PATH = "Social"
TENTACLES_EVALUATOR_STRATEGIES_PATH = "Strategies"
TENTACLES_EVALUATOR_UTIL_PATH = "Util"
TENTACLES_TRADING_MODE_PATH = "Mode"
TENTACLES_TRADING_SUPERVISOR_PATH = "Supervisor"
TENTACLES_TRADING_EXCHANGE_PATH = "Exchange"
TENTACLES_WEBSOCKETS_FEEDS_PATH = "feeds"
TENTACLES_DSL_OPERATORS_PATH = "DSL_operators"
TENTACLES_KEYWORDS_PATH = "Keywords"

# Tentacle installation context
TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION = "octobot_version"
TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION_UNKNOWN = "unknown"

# Tentacle local module folders
TENTACLE_CONFIG = "config"
TENTACLE_RESOURCES = "resources"
TENTACLE_TESTS = "tests"

# Tentacle creator
TENTACLES_PACKAGE_CREATOR_TEMP_FOLDER = "creator_temp"
TENTACLES_PACKAGE_FORMAT = "zip"
PYTHON_GENERATED_ELEMENTS = {"__pycache__"}
TENTACLES_PACKAGE_IGNORED_ELEMENTS = [".git", ".coveragerc", ".gitignore", ".travis.yml",
                                      "azure-pipelines.yml", "octobot_config.json"]
COMPILED_TENTACLES_TO_REMOVE_FOLDERS = {"build", "temp", "tests"}
PYTHON_GENERATED_ELEMENTS_EXTENSION = {"pyc"}
COMPILED_TENTACLES_TO_KEEP_ELEMENTS = {PYTHON_INIT_FILE}
COMPILED_TENTACLES_TO_REMOVE_ELEMENTS = {".c", ".py", ".pxd", ".pyc", "tests"}
TENTACLE_TEMPLATE_PATH = "templates"
TENTACLE_TEMPLATE_DESCRIPTION = "description"
TENTACLE_CONFIG_TEMPLATE_PRE_EXT = "_config"
TENTACLE_TEMPLATE_EXT = ".template"
TENTACLE_TEMPLATE_PRE_EXT = "_tentacle"
CYTHON_PXD_HEADER = "# cython: language_level=3"
SETUP_FILE = "setup.py"

# Tentacles architecture
TENTACLES_FOLDERS_ARCH = {
    # TENTACLES_AGENTS_PATH: [
    #     TENTACLES_AGENTS_EVALUATORS_PATH,
    #     TENTACLES_AGENTS_TRADING_PATH,
    #     TENTACLES_AGENTS_TEAMS_PATH,
    # ],
    TENTACLES_AUTOMATION_PATH: [
        TENTACLES_AUTOMATION_TRIGGER_EVENTS_PATH,
        TENTACLES_AUTOMATION_CONDITIONS_PATH,
        TENTACLES_AUTOMATION_ACTIONS_PATH,
    ],
    TENTACLES_BACKTESTING_PATH: {
        TENTACLES_BACKTESTING_COLLECTORS_PATH: [
            TENTACLES_BACKTESTING_THIRD_LEVEL_EXCHANGES_PATH,
            TENTACLES_BACKTESTING_THIRD_LEVEL_SOCIAL_PATH
        ],
        TENTACLES_BACKTESTING_CONVERTERS_PATH: [
            TENTACLES_BACKTESTING_THIRD_LEVEL_EXCHANGES_PATH
        ],
        TENTACLES_BACKTESTING_IMPORTERS_PATH: [
            TENTACLES_BACKTESTING_THIRD_LEVEL_EXCHANGES_PATH,
            TENTACLES_BACKTESTING_THIRD_LEVEL_SOCIAL_PATH
        ]
    },
    TENTACLES_PROFILES_PATH: [],
    TENTACLES_EVALUATOR_PATH: [
        TENTACLES_EVALUATOR_REALTIME_PATH,
        TENTACLES_EVALUATOR_SOCIAL_PATH,
        TENTACLES_EVALUATOR_TA_PATH,
        TENTACLES_EVALUATOR_SCRIPTED_PATH,
        TENTACLES_EVALUATOR_STRATEGIES_PATH,
        TENTACLES_EVALUATOR_UTIL_PATH
    ],
    TENTACLES_META_PATH: [
        TENTACLES_DSL_OPERATORS_PATH,
        TENTACLES_KEYWORDS_PATH
    ],
    TENTACLES_SERVICES_PATH: [
        TENTACLES_INTERFACES_PATH,
        TENTACLES_NOTIFIERS_PATH,
        TENTACLES_SERVICES_BASES_PATH,
        TENTACLES_SERVICES_FEEDS_PATH
    ],
    TENTACLES_TRADING_PATH: [
        TENTACLES_TRADING_MODE_PATH,
        TENTACLES_TRADING_SUPERVISOR_PATH,
        TENTACLES_TRADING_EXCHANGE_PATH
    ]
}

TENTACLE_MODULE_FOLDERS = {
    TENTACLE_CONFIG,
    TENTACLE_RESOURCES,
    TENTACLE_TESTS
}

# tentacles files management
TENTACLE_TYPES = [
    TENTACLES_AUTOMATION_PATH,
    TENTACLES_BACKTESTING_PATH,
    TENTACLES_EVALUATOR_PATH,
    TENTACLES_META_PATH,
    TENTACLES_SERVICES_PATH,
    TENTACLES_TRADING_PATH
]


IGNORED_TENTACLES_NAMES_IN_TENTACLES_SETUP_CONFIG = [
    "Automation", # special case for the automation tentacle config: it's storing all automations config under the same name: Automation (it's not a normal tentacle class name)
]

# compiled tentacles paths
PLATFORM_TO_DOWNLOAD_PATH = {
    enums.PlatformsName.WINDOWS: "windows",
    enums.PlatformsName.LINUX: "linux",
    enums.PlatformsName.MAC: "macos",
}
