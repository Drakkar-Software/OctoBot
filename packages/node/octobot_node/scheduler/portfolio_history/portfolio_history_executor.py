import octobot_commons.logging as commons_logging
import octobot.community.wallet_backend.errors as wallet_backend_errors
import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_providers as collection_providers

import octobot_flow.entities.portfolio_history as portfolio_history_entities
import octobot_flow.jobs.portfolio_history_job as portfolio_history_job_module

import octobot_node.scheduler.user_actions.user_actions_executor.util.account_authentication_resolver as account_authentication_resolver
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_state_updater as account_state_updater
import octobot_node.scheduler.user_actions.user_actions_executor.util.exchange_account_resolver as exchange_account_resolver

logger = commons_logging.get_logger("PortfolioHistoryExecutor")


async def run_portfolio_history_collection(
    wallet_id: str,
    account_ids: list[str] | None = None,
) -> list[portfolio_history_entities.PortfolioHistoryRunResult]:
    """
    Build contexts for all exchange accounts of the given wallet and run
    the PortfolioHistoryJob with parallel per-exchange fetching.
    """
    account_provider = collection_providers.AccountProvider.instance()
    try:
        accounts = account_provider.list_items(wallet_id)
    except wallet_backend_errors.WalletNotFoundError as error:
        logger.warning(
            "Skipping portfolio history collection for wallet %s: cannot list accounts (%s)",
            wallet_id,
            error,
        )
        return []

    if account_ids is not None:
        account_ids_set = set(account_ids)
        accounts = [account for account in accounts if account.id in account_ids_set]

    contexts = [
        context
        for account in accounts
        if (context := _build_context_for_account(wallet_id, account))
    ]

    if not contexts:
        logger.info("No exchange accounts found for wallet %s", wallet_id)
        return []

    job = portfolio_history_job_module.PortfolioHistoryJob(wallet_id, contexts)
    results = await job.run()
    for result in results:
        if result.error:
            logger.error(
                "Portfolio history collection failed for account %s: %s",
                result.account_id, result.error,
            )
        elif result.skipped:
            logger.debug("Skipped account %s", result.account_id)
        else:
            logger.info(
                "Collected %d trades + %d transactions for [%s %s %s] account %s "
                "in %.2fs, %d fetched candles symbols",
                result.trades_count,
                result.transactions_count,
                result.exchange_name,
                "simulated" if result.is_simulated else "real",
                result.trading_type or commons_constants.CONFIG_EXCHANGE_SPOT,
                result.account_id,
                result.duration_seconds or 0.0,
                result.price_symbols_count,
            )
    return results


def _build_context_for_account(
    wallet_id: str,
    account: protocol_models.Account,
) -> portfolio_history_entities.PortfolioHistoryAccountContext | None:
    specifics = account.specifics
    if specifics is None or specifics.actual_instance is None:
        return None
    if not isinstance(specifics.actual_instance, protocol_models.ExchangeAccount):
        return None
    if account.is_simulated:
        return None

    exchange_account = specifics.actual_instance
    trading_type = account_state_updater._trading_type_for_account_state_check(account)
    try:
        exchange_config = exchange_account_resolver.get_exchange_config(wallet_id, exchange_account)
    except Exception as error:
        logger.exception(
            error,
            True,
            f"Could not resolve exchange config for account {account.id}: {error}",
        )
        return None
    try:
        authentication = account_authentication_resolver.get_exchange_authentication(wallet_id, account)
    except Exception as error:
        logger.exception(
            error,
            True,
            f"Could not resolve authentication for account {account.id}: {error}",
        )
        return None
    auth_details = account_state_updater._encrypted_exchange_auth_details(
        exchange_account,
        authentication,
        trading_type,
        exchange_config.sandboxed,
    )
    return portfolio_history_entities.PortfolioHistoryAccountContext(
        account=account,
        exchange_account=exchange_account,
        exchange_config=exchange_config,
        trading_type=trading_type,
        auth_details=auth_details,
    )
