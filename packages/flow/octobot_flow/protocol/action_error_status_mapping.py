#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import typing

import octobot_flow.enums
import octobot_protocol.models as protocol_models


_ACTION_ERROR_STATUS_TO_PROTOCOL_ERROR_MESSAGE: dict[
    typing.Optional[str], protocol_models.AutomationActionResultErrorMessage
] = {
    octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value: (
        protocol_models.AutomationActionResultErrorMessage.NOT_ENOUGH_FUNDS
    ),
    octobot_flow.enums.ActionErrorStatus.ORDER_NOT_FOUND.value: (
        protocol_models.AutomationActionResultErrorMessage.ORDER_NOT_FOUND
    ),
    octobot_flow.enums.ActionErrorStatus.INVALID_ORDER.value: (
        protocol_models.AutomationActionResultErrorMessage.INVALID_ORDER
    ),
    octobot_flow.enums.ActionErrorStatus.AUTHENTICATION_ERROR.value: (
        protocol_models.AutomationActionResultErrorMessage.AUTHENTICATION_ERROR
    ),
    octobot_flow.enums.ActionErrorStatus.MISSING_SYMBOL.value: (
        protocol_models.AutomationActionResultErrorMessage.MISSING_SYMBOL
    ),
    octobot_flow.enums.ActionErrorStatus.SYMBOL_INCOMPATIBLE_WITH_ACCOUNT.value: (
        protocol_models.AutomationActionResultErrorMessage.SYMBOL_INCOMPATIBLE_WITH_ACCOUNT
    ),
}


def map_action_error_status_to_protocol_error_message(
    error_status: typing.Optional[str],
) -> protocol_models.AutomationActionResultErrorMessage:
    mapped_error_message = _ACTION_ERROR_STATUS_TO_PROTOCOL_ERROR_MESSAGE.get(error_status)
    if mapped_error_message is not None:
        return mapped_error_message
    return protocol_models.AutomationActionResultErrorMessage.EXECUTION_FAILED
