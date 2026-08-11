#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
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
import asyncio
import datetime
import typing

import dbos
import octobot_commons.logging as octobot_commons_logging
import octobot.community.wallet_backend.errors as wallet_backend_errors
import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_providers as collection_providers

import octobot_flow.entities
import octobot_node.enums
import octobot_node.errors as node_errors
import octobot_node.scheduler.global_view.global_view_executor as global_view_executor_module
import octobot_node.scheduler.global_view.automation_trigger as automation_trigger_module
import octobot_node.scheduler.user_actions.user_actions_executor.util.exchange_account_resolver as exchange_account_resolver
import octobot_node.scheduler.workflows_retention as workflows_retention

from octobot_node.scheduler import SCHEDULER  # avoid circular import

WORKFLOW_NAME = "global_view_refresh"
SCHEDULE_NAME = "global_view_refresh_every_5m"
SCHEDULE_CRON = "*/5 * * * *"


def _exchange_label_for_account(user_id: str, account: protocol_models.Account) -> str:
    specifics = account.specifics
    if specifics is None or specifics.actual_instance is None:
        return "n/a"
    exchange_account = specifics.actual_instance
    if not isinstance(exchange_account, protocol_models.ExchangeAccount):
        return "n/a"
    try:
        return exchange_account_resolver.get_exchange_config(user_id, exchange_account).exchange
    except (node_errors.InvalidUserActionPayloadError, node_errors.AmbiguousExchangeConfigError):
        return "n/a"


def _portfolio_summary_fields(
    refresh_result: octobot_flow.entities.GlobalViewAccountRefreshResult,
) -> tuple[str, str]:
    portfolio_history_state = refresh_result.portfolio_history_state
    if portfolio_history_state is None or portfolio_history_state.history is None:
        return "n/a", "n/a"
    history = portfolio_history_state.history
    valuation_unit = history.unit if history.unit else "n/a"
    history_values = history.values or []
    if not history_values:
        return valuation_unit, "n/a"
    return valuation_unit, str(history_values[-1].total)


def _log_successful_account_refresh(
    user_id: str,
    account: protocol_models.Account,
    refresh_result: octobot_flow.entities.GlobalViewAccountRefreshResult,
) -> None:
    valuation_unit, portfolio_total = _portfolio_summary_fields(refresh_result)
    open_orders_count = len(refresh_result.open_orders or [])
    changed_orders_count = len(refresh_result.changed_order_ids)
    octobot_commons_logging.get_logger(GlobalViewRefreshWorkflow.__name__).info(
        "Account global view refresh succeeded: account=%s wallet=%s name=%s exchange=%s "
        "simulated=%s open_orders=%s changed_orders=%s automations_triggered=%s "
        "valuation_unit=%s portfolio_total=%s",
        account.id,
        user_id,
        account.name,
        _exchange_label_for_account(user_id, account),
        account.is_simulated,
        open_orders_count,
        changed_orders_count,
        bool(refresh_result.changed_order_ids),
        valuation_unit,
        portfolio_total,
    )


@SCHEDULER.INSTANCE.dbos_class()
class GlobalViewRefreshWorkflow:
    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name=WORKFLOW_NAME)
    async def global_view_refresh(
        scheduled_time: datetime.datetime,
        context: typing.Any,
    ) -> dict[str, typing.Any]:
        return await GlobalViewRefreshWorkflow._run_global_view_refresh(
            scheduled_time,
        )

    @staticmethod
    @SCHEDULER.INSTANCE.step(
        name="run_global_view_refresh",
        retries_allowed=False,
    )
    async def _run_global_view_refresh(
        scheduled_time: datetime.datetime,
    ) -> dict[str, typing.Any]:
        logger = octobot_commons_logging.get_logger(GlobalViewRefreshWorkflow.__name__)
        logger.info("global_view_refresh started (scheduled_time=%s)", scheduled_time.isoformat())
        if workflows_retention.should_skip_retention_cleanup_on_this_node():
            logger.info("global_view_refresh stopped: consumer-only node (skipped)")
            return {"refreshed_accounts": 0, "skipped": True}
        wallet_ids = collection_providers.AccountProvider.instance().list_registered_wallet_ids()
        refreshed_accounts_count = 0
        for wallet_id in wallet_ids:
            refreshed_accounts_count += await GlobalViewRefreshWorkflow._refresh_wallet_accounts(
                wallet_id,
            )
        result = {
            "refreshed_accounts": refreshed_accounts_count,
            "scheduled_time": scheduled_time.isoformat(),
        }
        logger.info(
            "global_view_refresh completed (refreshed_accounts=%s, scheduled_time=%s)",
            refreshed_accounts_count,
            scheduled_time.isoformat(),
        )
        return result

    @staticmethod
    async def _refresh_wallet_accounts(
        user_id: str,
    ) -> int:
        logger = octobot_commons_logging.get_logger(GlobalViewRefreshWorkflow.__name__)
        account_provider = collection_providers.AccountProvider.instance()
        try:
            accounts = account_provider.list_items(user_id)
        except wallet_backend_errors.WalletNotFoundError as error:
            logger.warning(
                "Skipping global view refresh for wallet %s: cannot list accounts (%s)",
                user_id,
                error,
            )
            return 0
        if not accounts:
            return 0
        refresh_results = await asyncio.gather(
            *[
                GlobalViewRefreshWorkflow._refresh_single_account(user_id, account)
                for account in accounts
            ],
            return_exceptions=True,
        )
        refreshed_count = 0
        for refresh_result in refresh_results:
            if isinstance(refresh_result, Exception):
                logger.exception(
                    refresh_result,
                    True,
                    f"Account global view refresh failed: {refresh_result}",
                )
                continue
            if refresh_result:
                refreshed_count += 1
        return refreshed_count

    @staticmethod
    async def _refresh_single_account(
        user_id: str,
        account: protocol_models.Account,
    ) -> bool:
        try:
            refresh_result = await global_view_executor_module.refresh_account_global_view(
                user_id,
                account,
            )
        except Exception as error:
            octobot_commons_logging.get_logger(
                GlobalViewRefreshWorkflow.__name__
            ).exception(
                error,
                True,
                f"Failed to refresh account {account.id} for wallet {user_id}: {error}",
            )
            raise
        if refresh_result.changed_order_ids:
            await automation_trigger_module.trigger_account_automations(
                user_id,
                account.id,
                refresh_result.changed_order_ids,
            )
        _log_successful_account_refresh(user_id, account, refresh_result)
        return True

    


def get_schedule_input() -> dbos.ScheduleInput:
    return {
        "schedule_name": SCHEDULE_NAME,
        "workflow_fn": GlobalViewRefreshWorkflow.global_view_refresh,
        "schedule": SCHEDULE_CRON,
        "context": None,
        "automatic_backfill": False,
        "queue_name": octobot_node.enums.SchedulerQueues.GLOBAL_VIEW_QUEUE.value,
    }
