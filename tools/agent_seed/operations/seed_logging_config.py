#  Demo agent-seed logging_config.ini (DEBUG handlers from bundled OctoBot default).

import configparser
import pathlib

import tools.agent_seed.paths as agent_seed_paths

_HANDLER_SECTION_PREFIX = "handler_"
_DEBUG_LOG_LEVEL = "DEBUG"


class AgentSeedBundledLoggingConfigMissingError(RuntimeError):
    """Raised when the shipped octobot/config/logging_config.ini template is absent."""


def _apply_debug_handler_levels(parser: configparser.ConfigParser) -> None:
    for section_name in parser.sections():
        if section_name.startswith(_HANDLER_SECTION_PREFIX):
            parser[section_name]["level"] = _DEBUG_LOG_LEVEL


def write_demo_logging_config(user_folder: pathlib.Path) -> None:
    bundled_path = agent_seed_paths.bundled_octobot_logging_config_file()
    if not bundled_path.is_file():
        raise AgentSeedBundledLoggingConfigMissingError(
            "Bundled OctoBot logging config is missing "
            f"({bundled_path}). "
            "Run agent-seed from a full OctoBot source tree."
        )
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(bundled_path, encoding="utf-8")
    _apply_debug_handler_levels(parser)
    user_folder.mkdir(parents=True, exist_ok=True)
    output_path = agent_seed_paths.logging_config_file(user_folder)
    with output_path.open("w", encoding="utf-8") as output_file:
        parser.write(output_file, space_around_delimiters=False)
