import datetime
import typing

import dbos
import octobot_commons.logging as commons_logging
import octobot_sync.sync.collection_providers as collection_providers

import octobot_node.scheduler.portfolio_history.portfolio_history_executor as portfolio_history_executor_module
import octobot_node.scheduler.workflows.params as workflow_params_module

import octobot_node.enums
from octobot_node.scheduler import SCHEDULER

WORKFLOW_NAME = "portfolio_history_collection"
SCHEDULE_NAME = "portfolio_history_daily_3am"
SCHEDULE_CRON = "0 3 * * *" # 3:00 AM every day

logger = commons_logging.get_logger("PortfolioHistoryWorkflow")

_EMPTY_COLLECTION_SUMMARY = {
    "succeeded": 0,
    "failed": 0,
    "skipped": 0,
}


def _parse_collection_params(
    context: typing.Any,
) -> workflow_params_module.PortfolioHistoryCollectionParams | None:
    if context is None:
        return None
    if isinstance(context, workflow_params_module.PortfolioHistoryCollectionParams):
        return context
    if isinstance(context, dict):
        return workflow_params_module.PortfolioHistoryCollectionParams.from_dict(context)
    return None


@SCHEDULER.INSTANCE.dbos_class()
class PortfolioHistoryWorkflow:
    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name=WORKFLOW_NAME)
    async def portfolio_history_collection(
        scheduled_time: datetime.datetime,
        context: typing.Any,
    ) -> dict[str, typing.Any]:
        collection_params = _parse_collection_params(context)
        return await PortfolioHistoryWorkflow._run_collection(scheduled_time, collection_params)

    @staticmethod
    @SCHEDULER.INSTANCE.step(name="run_portfolio_history_collection")
    async def _run_collection(
        scheduled_time: datetime.datetime,
        collection_params: workflow_params_module.PortfolioHistoryCollectionParams | None = None,
    ) -> dict[str, typing.Any]:
        """
        This is a step to avoid storing results of internal dbos select statements,
        which are otherwise counted as steps and have their result stored
        """
        try:
            logger.info("Starting portfolio history collection at %s", scheduled_time)
            if collection_params and collection_params.wallet_ids:
                wallet_ids = collection_params.wallet_ids
                logger.info(
                    "Portfolio history collection scoped to %d wallet(s), account_ids=%s",
                    len(wallet_ids),
                    collection_params.account_ids,
                )
            else:
                wallet_ids = collection_providers.AccountProvider.instance().list_collectable_wallet_ids()
            account_ids = collection_params.account_ids if collection_params else None
            total_results = []

            for wallet_id in wallet_ids:
                try:
                    results = await portfolio_history_executor_module.run_portfolio_history_collection(
                        wallet_id,
                        account_ids=account_ids,
                    )
                    total_results.extend(results)
                except Exception as error:
                    logger.exception(
                        error,
                        True,
                        f"Portfolio history collection failed for wallet {wallet_id}: {error}",
                    )

            succeeded = sum(1 for result in total_results if not result.skipped and not result.error)
            failed = sum(1 for result in total_results if result.error)
            skipped = sum(1 for result in total_results if result.skipped)
            logger.info(
                "Portfolio history collection complete: %d succeeded, %d failed, %d skipped",
                succeeded, failed, skipped,
            )
            return {
                "succeeded": succeeded,
                "failed": failed,
                "skipped": skipped,
            }
        except Exception as error:
            logger.exception(
                error,
                True,
                f"Portfolio history collection failed: {error}",
            )
            return dict(_EMPTY_COLLECTION_SUMMARY)


def get_schedule_input() -> dbos.ScheduleInput:
    return {
        "schedule_name": SCHEDULE_NAME,
        "workflow_fn": PortfolioHistoryWorkflow.portfolio_history_collection,
        "schedule": SCHEDULE_CRON,
        "context": None,
        "automatic_backfill": False,
        "catch_up_once_on_startup": True,
        "queue_name": octobot_node.enums.SchedulerQueues.PORTFOLIO_HISTORY_QUEUE.value,
    }
