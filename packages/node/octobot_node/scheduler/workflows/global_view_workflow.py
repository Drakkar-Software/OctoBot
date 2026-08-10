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
import logging
import typing

import dbos
import octobot_commons.logging as octobot_commons_logging
import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_providers as collection_providers

import octobot_node.enums
import octobot_node.scheduler.global_view.global_view_executor as global_view_executor_module
import octobot_node.scheduler.global_view.automation_trigger as automation_trigger_module
import octobot_node.scheduler.workflows_retention as workflows_retention

from octobot_node.scheduler import SCHEDULER  # avoid circular import

WORKFLOW_NAME = "global_view_refresh"
SCHEDULE_NAME = "global_view_refresh_every_5m"
SCHEDULE_CRON = "*/5 * * * *"


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
            context,
        )

    @staticmethod
    @SCHEDULER.INSTANCE.step(name="run_global_view_refresh")
    async def _run_global_view_refresh(
        scheduled_time: datetime.datetime,
        context: typing.Any,
    ) -> dict[str, typing.Any]:
        logger = octobot_commons_logging.get_logger(GlobalViewRefreshWorkflow.__name__)
        if workflows_retention.should_skip_retention_cleanup_on_this_node():
            logger.info("global_view_refresh skipped: consumer-only node")
            return {"refreshed_accounts": 0, "skipped": True}
        wallet_ids = collection_providers.AccountProvider.instance().list_registered_wallet_ids()
        refreshed_accounts_count = 0
        for wallet_id in wallet_ids:
            refreshed_accounts_count += await GlobalViewRefreshWorkflow._refresh_wallet_accounts(
                wallet_id,
                logger,
            )
        return {
            "refreshed_accounts": refreshed_accounts_count,
            "scheduled_time": scheduled_time.isoformat(),
        }

    @staticmethod
    async def _refresh_wallet_accounts(
        user_id: str,
        logger: logging.Logger,
    ) -> int:
        account_provider = collection_providers.AccountProvider.instance()
        try:
            accounts = account_provider.list_items(user_id)
        except Exception as error:
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
                GlobalViewRefreshWorkflow._refresh_single_account(user_id, account, logger)
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
        logger: logging.Logger,
    ) -> bool:
        try:
            refresh_result = await global_view_executor_module.refresh_account_global_view(
                user_id,
                account,
            )
        except Exception as error:
            logger.exception(
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
        return True


def get_schedule_input() -> dbos.ScheduleInput:
    return {
        "schedule_name": SCHEDULE_NAME,
        "workflow_fn": GlobalViewRefreshWorkflow.global_view_refresh,
        "schedule": SCHEDULE_CRON,
        "context": None,
        "automatic_backfill": True,
        "queue_name": octobot_node.enums.SchedulerQueues.GLOBAL_VIEW_QUEUE.value,
    }
