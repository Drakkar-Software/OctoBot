import typing
import contextlib

import octobot_commons.dsl_interpreter
import octobot_commons.signals
import octobot_commons.errors
import octobot_trading.exchanges
import octobot_trading.dsl
import octobot.community

import tentacles.Meta.DSL_operators as dsl_operators

import octobot_flow.entities
import octobot_flow.errors
import octobot_flow.enums

# avoid circular import
import octobot_flow.logic.actions.abstract_action_executor as abstract_action_executor



class ConfiguredActionsExecutor(abstract_action_executor.AbstractActionExecutor):
    def __init__(
        self, 
        exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
        automation: octobot_flow.entities.AutomationDetails,
    ):
        super().__init__()

        self._exchange_manager = exchange_manager
        self._automation = automation

    async def execute_action(self, action: octobot_flow.entities.ConfiguredActionDetails) -> typing.Any:
        return_value = None
        error_status = octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
        match action.action:
            case octobot_flow.enums.ActionType.STOP_AUTOMATION.value:
                return_value = await self._execute_stop_automation_action(action)
            case _:
                self.get_logger().error(f"Configured action type {action.action} is not supported")
                error_status = octobot_flow.enums.ActionErrorStatus.UNSUPPORTED_ACTION_TYPE.value
        action.complete(result=return_value, error_status=error_status)
        return return_value

    async def _execute_stop_automation_action(self, action: octobot_flow.entities.ConfiguredActionDetails) -> typing.Any:
        self.get_logger().info(f"Stopping automation: {self._automation.metadata.automation_id}")
        self._automation.post_actions.stop_automation = True
        # todo cancel open orders and sell assets if required in action config
        return None
    