#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_flow.entities
import octobot_flow.jobs.global_view_account_job as global_view_account_job_module
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_authentication_resolver as account_authentication_resolver
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_state_updater as account_state_updater
import octobot_node.scheduler.user_actions.user_actions_executor.util.exchange_account_resolver as exchange_account_resolver


async def refresh_account_global_view(
    user_id: str,
    account: protocol_models.Account,
) -> octobot_flow.entities.GlobalViewAccountRefreshResult:
    account_specifics = account.specifics
    if account_specifics is None or account_specifics.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "Account.specifics.actual_instance is required for global view refresh."
        )
    account_specifics_instance = account_specifics.actual_instance
    if isinstance(account_specifics_instance, protocol_models.GenericAccount):
        return octobot_flow.entities.GlobalViewAccountRefreshResult(
            updated_account=account,
            changed_order_ids=set(),
        )
    if isinstance(account_specifics_instance, protocol_models.BlockchainAccount):
        raise node_errors.InvalidUserActionPayloadError("Blockchain accounts are not supported yet.")
    if not isinstance(account_specifics_instance, protocol_models.ExchangeAccount):
        raise node_errors.InvalidUserActionPayloadError(
            f"Unsupported account specifics type: {type(account_specifics_instance).__name__}."
        )

    exchange_account = account_specifics_instance
    trading_type = account_state_updater._trading_type_for_account_state_check(account)
    exchange_config = exchange_account_resolver.get_exchange_config(user_id, exchange_account)
    authentication = None if account.is_simulated else account_authentication_resolver.get_exchange_authentication(
        user_id,
        account,
    )
    auth_details = account_state_updater._encrypted_exchange_auth_details(
        exchange_account,
        authentication,
        trading_type,
        exchange_config.sandboxed,
    )
    context = octobot_flow.entities.GlobalViewAccountContext(
        account=account,
        exchange_account=exchange_account,
        exchange_config=exchange_config,
        trading_type=trading_type,
        auth_details=auth_details,
    )
    return await global_view_account_job_module.GlobalViewAccountJob(user_id, context).run()
