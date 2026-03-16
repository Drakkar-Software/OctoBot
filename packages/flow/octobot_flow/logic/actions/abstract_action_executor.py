import typing

import octobot_commons.logging
import octobot.community

import octobot_flow.entities


class AbstractActionExecutor:
    def __init__(
        self, 
    ):
        self.pending_bot_logs: list[octobot.community.BotLogData] = []

    async def execute_action(self, action: octobot_flow.entities.AbstractActionDetails) -> typing.Any:
        raise NotImplementedError("execute_action is not implemented for this action type")


    def get_logger(self) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(self.__class__.__name__)
