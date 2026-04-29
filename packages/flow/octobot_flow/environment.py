import octobot.constants  # will load .env file and init constants

import octobot_flow.repositories.community
import octobot_trading.constants


def initialize_environment(allow_funds_transfer: bool = False) -> None:
    octobot_flow.repositories.community.initialize_community_authentication()
    if allow_funds_transfer:
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = True
