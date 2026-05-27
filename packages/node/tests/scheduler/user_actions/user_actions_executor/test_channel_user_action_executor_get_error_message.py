#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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

import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.automation.create_automation as create_automation_executor_module
import octobot_node.scheduler.user_actions.user_actions_executor.account.create_account as create_account_executor
import octobot_node.scheduler.user_actions.user_actions_executor.exchange_config.create_exchange_config as create_exchange_config_executor
import octobot_node.scheduler.user_actions.user_actions_executor.automation.stop_automation as stop_automation_executor

_WALLET = "0xwallet"


class TestAutomationUserActionExecutorGetErrorMessage:
    def test_active_automation_workflow_not_found(self):
        executor = stop_automation_executor.StopAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(node_errors.ActiveAutomationWorkflowNotFoundError("none"))
        assert resolved == protocol_models.AutomationActionResultErrorMessage.AUTOMATION_NOT_FOUND

    def test_invalid_user_action_payload(self):
        executor = stop_automation_executor.StopAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(node_errors.InvalidUserActionPayloadError("bad"))
        assert resolved == protocol_models.AutomationActionResultErrorMessage.INVALID_CONFIGURATION

    def test_ambiguous_active_automation_workflow(self):
        executor = stop_automation_executor.StopAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(node_errors.AmbiguousActiveAutomationWorkflowError("ambiguous"))
        assert resolved == protocol_models.AutomationActionResultErrorMessage.AUTOMATION_NOT_FOUND

    def test_account_not_found(self):
        executor = stop_automation_executor.StopAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(node_errors.AccountNotFoundError("missing"))
        assert resolved == protocol_models.AutomationActionResultErrorMessage.ACCOUNT_NOT_FOUND

    def test_account_authentication_details_not_found(self):
        executor = create_automation_executor_module.CreateAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(
            node_errors.AccountAuthenticationNotFoundError("missing auth")
        )
        assert resolved == protocol_models.AutomationActionResultErrorMessage.ACCOUNT_AUTHENTICATION_DETAILS_NOT_FOUND

    def test_unsupported_automation_configuration_type(self):
        executor = stop_automation_executor.StopAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(
            node_errors.UnsupportedAutomationConfigurationTypeError("dca")
        )
        assert resolved == protocol_models.AutomationActionResultErrorMessage.INVALID_CONFIGURATION

    def test_automation_strategy_not_found(self):
        executor = create_automation_executor_module.CreateAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(node_errors.AutomationStrategyNotFoundError("missing"))
        assert resolved == protocol_models.AutomationActionResultErrorMessage.STRATEGY_NOT_FOUND

    def test_automation_strategy_version_mismatch(self):
        executor = create_automation_executor_module.CreateAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(
            node_errors.AutomationStrategyVersionMismatchError("mismatch"),
        )
        assert resolved == protocol_models.AutomationActionResultErrorMessage.STRATEGY_VERSION_NOT_FOUND

    def test_unknown_trading_type(self):
        executor = create_automation_executor_module.CreateAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(node_errors.UnknownTradingTypeError("unknown"))
        assert resolved == protocol_models.AutomationActionResultErrorMessage.UNKNOWN_TRADING_TYPE

    def test_ambiguous_trading_type(self):
        executor = create_automation_executor_module.CreateAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(node_errors.AmbiguousTradingTypeError("ambiguous"))
        assert resolved == protocol_models.AutomationActionResultErrorMessage.AMBIGUOUS_TRADING_TYPE

    def test_ambiguous_exchange_config(self):
        executor = create_automation_executor_module.CreateAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(node_errors.AmbiguousExchangeConfigError("ambiguous"))
        assert resolved == protocol_models.AutomationActionResultErrorMessage.AMBIGUOUS_EXCHANGE_CONFIG

    def test_unknown_exception_falls_back_to_internal_error(self):
        executor = stop_automation_executor.StopAutomationActionExecutor(_WALLET)
        resolved = executor._get_error_message(RuntimeError("boom"))
        assert resolved == protocol_models.AutomationActionResultErrorMessage.INTERNAL_ERROR


class TestAccountUserActionExecutorGetErrorMessage:
    def test_account_not_found_from_backend(self):
        executor = create_account_executor.CreateAccountActionExecutor(_WALLET)
        resolved = executor._get_error_message(collection_errors.ItemNotFoundError("missing"))
        assert resolved == protocol_models.AccountActionResultErrorMessage.ACCOUNT_NOT_FOUND

    def test_account_not_found(self):
        executor = create_account_executor.CreateAccountActionExecutor(_WALLET)
        resolved = executor._get_error_message(node_errors.AccountNotFoundError("lookup failed"))
        assert resolved == protocol_models.AccountActionResultErrorMessage.ACCOUNT_NOT_FOUND

    def test_account_authentication_details_not_found(self):
        executor = create_account_executor.CreateAccountActionExecutor(_WALLET)
        resolved = executor._get_error_message(
            node_errors.AccountAuthenticationNotFoundError("missing auth")
        )
        assert (
            resolved
            == protocol_models.AccountActionResultErrorMessage.ACCOUNT_AUTHENTICATION_DETAILS_NOT_FOUND
        )

    def test_invalid_user_action_payload(self):
        executor = create_account_executor.CreateAccountActionExecutor(_WALLET)
        resolved = executor._get_error_message(node_errors.InvalidUserActionPayloadError("bad"))
        assert resolved == protocol_models.AccountActionResultErrorMessage.INVALID_CONFIGURATION

    def test_duplicate_account(self):
        executor = create_account_executor.CreateAccountActionExecutor(_WALLET)
        resolved = executor._get_error_message(collection_errors.DuplicateItemError("dup"))
        assert resolved == protocol_models.AccountActionResultErrorMessage.DUPLICATE_ITEM

    def test_unknown_exception_falls_back_to_internal_error(self):
        executor = create_account_executor.CreateAccountActionExecutor(_WALLET)
        resolved = executor._get_error_message(ValueError("unexpected"))
        assert resolved == protocol_models.AccountActionResultErrorMessage.INTERNAL_ERROR


class TestExchangeConfigUserActionExecutorGetErrorMessage:
    def test_exchange_config_not_found_from_backend(self):
        executor = create_exchange_config_executor.CreateExchangeConfigActionExecutor(_WALLET)
        resolved = executor._get_error_message(collection_errors.ItemNotFoundError("missing"))
        assert resolved == protocol_models.ExchangeConfigActionResultErrorMessage.EXCHANGE_CONFIG_NOT_FOUND

    def test_invalid_user_action_payload(self):
        executor = create_exchange_config_executor.CreateExchangeConfigActionExecutor(_WALLET)
        resolved = executor._get_error_message(node_errors.InvalidUserActionPayloadError("bad"))
        assert resolved == protocol_models.ExchangeConfigActionResultErrorMessage.INVALID_CONFIGURATION

    def test_duplicate_exchange_config(self):
        executor = create_exchange_config_executor.CreateExchangeConfigActionExecutor(_WALLET)
        resolved = executor._get_error_message(collection_errors.DuplicateItemError("dup"))
        assert resolved == protocol_models.ExchangeConfigActionResultErrorMessage.DUPLICATE_ITEM

    def test_unknown_exception_falls_back_to_internal_error(self):
        executor = create_exchange_config_executor.CreateExchangeConfigActionExecutor(_WALLET)
        resolved = executor._get_error_message(ValueError("unexpected"))
        assert resolved == protocol_models.ExchangeConfigActionResultErrorMessage.INTERNAL_ERROR
