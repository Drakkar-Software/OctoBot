import typing

import octobot.constants  # will load .env file and init constants

import octobot_flow.repositories.community
import octobot_trading.constants

_EXECUTOR_ID: typing.Optional[str] = None


def register_executor_id(executor_id: str) -> None:
    global _EXECUTOR_ID
    _EXECUTOR_ID = executor_id


def get_executor_id() -> typing.Optional[str]:
    return _EXECUTOR_ID


def initialize_environment(allow_funds_transfer: bool = False) -> None:
    octobot_flow.repositories.community.initialize_community_authentication()
    if allow_funds_transfer:
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = True
