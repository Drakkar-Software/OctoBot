import octobot_flow.enums
import octobot_flow.protocol.action_error_status_mapping as action_error_status_mapping
import octobot_protocol.models as protocol_models


class TestMapActionErrorStatusToProtocolErrorMessage:
    def test_maps_known_action_error_statuses(self):
        assert action_error_status_mapping.map_action_error_status_to_protocol_error_message(
            octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value,
        ) == protocol_models.AutomationActionResultErrorMessage.NOT_ENOUGH_FUNDS
        assert action_error_status_mapping.map_action_error_status_to_protocol_error_message(
            octobot_flow.enums.ActionErrorStatus.ORDER_NOT_FOUND.value,
        ) == protocol_models.AutomationActionResultErrorMessage.ORDER_NOT_FOUND
        assert action_error_status_mapping.map_action_error_status_to_protocol_error_message(
            octobot_flow.enums.ActionErrorStatus.INVALID_ORDER.value,
        ) == protocol_models.AutomationActionResultErrorMessage.INVALID_ORDER
        assert action_error_status_mapping.map_action_error_status_to_protocol_error_message(
            octobot_flow.enums.ActionErrorStatus.AUTHENTICATION_ERROR.value,
        ) == protocol_models.AutomationActionResultErrorMessage.AUTHENTICATION_ERROR
        assert action_error_status_mapping.map_action_error_status_to_protocol_error_message(
            octobot_flow.enums.ActionErrorStatus.MISSING_SYMBOL.value,
        ) == protocol_models.AutomationActionResultErrorMessage.MISSING_SYMBOL
        assert action_error_status_mapping.map_action_error_status_to_protocol_error_message(
            octobot_flow.enums.ActionErrorStatus.SYMBOL_INCOMPATIBLE_WITH_ACCOUNT.value,
        ) == protocol_models.AutomationActionResultErrorMessage.SYMBOL_INCOMPATIBLE_WITH_ACCOUNT

    def test_unknown_status_maps_to_execution_failed(self):
        assert action_error_status_mapping.map_action_error_status_to_protocol_error_message(
            "unexpected_status",
        ) == protocol_models.AutomationActionResultErrorMessage.EXECUTION_FAILED
