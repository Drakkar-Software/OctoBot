#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  Demo-only agent seed wallet sandbox rules for the debug user-action API.
#  Not for production; pairs with tools/agent_seed insecure dev credentials.

import typing

import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_providers as collection_providers

import octobot.community.authentication as community_authentication

import octobot_node.agent_seed.constants as agent_seed_constants


class DemoAgentSeedUserActionForbiddenError(Exception):
    """Raised when a demo agent-seed wallet attempts a disallowed user action."""


def _normalize_user_id(user_id: str) -> str:
    return user_id.strip().lower()


def _wallet_display_name_for_user_id(user_id: str) -> typing.Optional[str]:
    try:
        wallet = community_authentication.CommunityAuthentication.instance().get_wallet_by_user_id(
            user_id,
        )
    except Exception:
        return None
    address = wallet.address.lower()
    return community_authentication.CommunityAuthentication.instance().get_wallet_name(address)


def is_demo_agent_seed_user(user_id: str) -> bool:
    if _normalize_user_id(user_id) != _normalize_user_id(
        agent_seed_constants.DEMO_AGENT_SEED_USER_ID,
    ):
        return False
    display_name = _wallet_display_name_for_user_id(user_id)
    if display_name is None:
        return False
    return display_name.strip().lower() == (
        agent_seed_constants.DEMO_AGENT_SEED_WALLET_DISPLAY_NAME.strip().lower()
    )


def _forbidden() -> None:
    raise DemoAgentSeedUserActionForbiddenError(
        agent_seed_constants.DEMO_AGENT_SEED_FORBIDDEN_ACTION_DETAIL,
    )


def _account_is_simulated(user_id: str, account_id: str) -> bool:
    account = collection_providers.AccountProvider.instance().get_item(user_id, account_id)
    return bool(account.is_simulated)


def _automation_account_ids(
    automation_configuration: protocol_models.AutomationConfiguration,
) -> list[str]:
    account_ids: list[str] = []
    for account_reference in automation_configuration.accounts or []:
        if account_reference.id:
            account_ids.append(account_reference.id)
    return account_ids


def _validate_automation_accounts_simulated(user_id: str, account_ids: list[str]) -> None:
    for account_id in account_ids:
        if not _account_is_simulated(user_id, account_id):
            _forbidden()


def validate_demo_agent_seed_user_action(
    user_id: str,
    user_action: protocol_models.UserAction,
) -> None:
    if not is_demo_agent_seed_user(user_id):
        return
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        return
    payload = wrapper.actual_instance
    action_type = getattr(payload, "action_type", None)

    if action_type in (
        protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
        protocol_models.UserActionType.ACCOUNT_AUTH_EDIT,
        protocol_models.UserActionType.EXCHANGE_CONFIG_CREATE,
        protocol_models.UserActionType.EXCHANGE_CONFIG_EDIT,
    ):
        _forbidden()

    if isinstance(payload, protocol_models.CreateAccountConfiguration):
        if not payload.configuration.is_simulated:
            _forbidden()
        return

    if isinstance(payload, protocol_models.EditAccountConfiguration):
        if payload.configuration.is_simulated is False:
            _forbidden()
        return

    if isinstance(payload, protocol_models.CreateAutomationConfiguration):
        _validate_automation_accounts_simulated(
            user_id,
            _automation_account_ids(payload.configuration),
        )
        return

    if isinstance(payload, protocol_models.EditAutomationConfiguration):
        _validate_automation_accounts_simulated(
            user_id,
            _automation_account_ids(payload.configuration),
        )
