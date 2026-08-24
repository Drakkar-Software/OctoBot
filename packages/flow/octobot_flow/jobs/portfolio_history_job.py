import asyncio
import time

import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_protocol.models as protocol_models
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data_module
import octobot_trading.util.protocol_trading_mapping as protocol_trading_mapping

import octobot_flow.entities
import octobot_flow.entities.portfolio_history as portfolio_history_entities
import octobot_flow.logic.configuration.profile_data_factory as profile_data_factory_module
import octobot_flow.logic.portfolio_history.trading_history_merge as trading_history_merge_module
import octobot_flow.logic.portfolio_history.daily_price_cache_updater as daily_price_cache_updater_module
import octobot_flow.repositories.exchange.trades_repository as trades_repository_module
import octobot_flow.repositories.exchange.transactions_repository as transactions_repository_module

import tentacles.Meta.Keywords.scripting_library as scripting_library


logger = commons_logging.get_logger("PortfolioHistoryJob")


class PortfolioHistoryJob:
    def __init__(
        self,
        wallet_id: str,
        contexts: list[portfolio_history_entities.PortfolioHistoryAccountContext],
        data_root: str = None,
    ):
        self.wallet_id = wallet_id
        self.contexts = contexts
        self.data_root = data_root

    async def run(self) -> list[portfolio_history_entities.PortfolioHistoryRunResult]:
        """Run data collection for all exchange accounts in parallel."""
        tasks = [
            self._run_for_account(context)
            for context in self.contexts
        ]
        return list(await asyncio.gather(*tasks))

    async def _run_for_account(
        self, context: portfolio_history_entities.PortfolioHistoryAccountContext
    ) -> portfolio_history_entities.PortfolioHistoryRunResult:
        account = context.account
        account_id = account.id
        exchange_name = context.exchange_config.exchange
        result_metadata = _result_metadata_from_context(context)

        # Skip unsupported account types.
        specifics = account.specifics
        if (
            specifics is None
            or specifics.actual_instance is None
            or not isinstance(specifics.actual_instance, protocol_models.ExchangeAccount)
            or account.is_simulated
        ):
            return _skipped_run_result(account_id, exchange_name, result_metadata)

        started_at = time.monotonic()
        try:
            result = await self._fetch_and_persist(context)
        except Exception as error:
            logger.exception(
                error,
                True,
                f"Portfolio history job failed for account {account_id}: {error}",
            )
            return portfolio_history_entities.PortfolioHistoryRunResult(
                account_id=account_id,
                exchange_name=exchange_name,
                error=str(error),
                duration_seconds=time.monotonic() - started_at,
                **result_metadata,
            )
        result.duration_seconds = time.monotonic() - started_at
        return result

    async def _fetch_and_persist(
        self, context: portfolio_history_entities.PortfolioHistoryAccountContext
    ) -> portfolio_history_entities.PortfolioHistoryRunResult:
        account = context.account
        exchange_config = context.exchange_config
        exchange_type = protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(
            context.trading_type
        ).value

        profile_data = _build_profile_data(context)
        exchange_data = exchange_data_module.exchange_data_factory(
            exchange_internal_name=exchange_config.exchange,
            exchange_type=exchange_type,
            sandboxed=exchange_config.sandboxed,
            auth_details=context.auth_details,
        )
        tentacles_setup_config = tentacles_manager_api.get_full_tentacles_setup_config()

        async with trading_exchanges.exchange_manager_from_exchange_data(
            exchange_data,
            profile_data,
            tentacles_setup_config,
            price_fallback=None,
        ) as exchange_manager:
            await trades_repository_module.TradesRepository.ensure_temporary_trades_channel(
                exchange_manager,
            )
            fetched_exchange_data = octobot_flow.entities.FetchedExchangeData()
            trades_repo = trades_repository_module.TradesRepository(
                exchange_manager, [], fetched_exchange_data
            )
            tx_repo = transactions_repository_module.TransactionsRepository(
                exchange_manager, [], fetched_exchange_data
            )

            # Fetch trades, deposits, withdrawals in parallel within this account.
            symbols = list(exchange_config.historical_trade_symbols or [])
            trades_task = trades_repo.fetch_trades(symbols)
            deposits_task = tx_repo.fetch_deposits()
            withdrawals_task = tx_repo.fetch_withdrawals()
            trades, deposits, withdrawals = await asyncio.gather(
                trades_task, deposits_task, withdrawals_task
            )

            all_transactions = deposits + withdrawals

            # Update daily price cache for relevant symbols.
            reference_market = scripting_library.get_default_exchange_reference_market(
                exchange_config.exchange,
            )
            price_symbols = _derive_price_symbols(symbols, all_transactions, reference_market)
            await daily_price_cache_updater_module.update_daily_prices(
                exchange_manager,
                exchange_config.exchange,
                exchange_type,
                exchange_config.sandboxed,
                price_symbols,
                self.data_root,
            )

        # Merge and persist trading history.
        trading_history_merge_module.merge_and_persist_trading_history(
            self.wallet_id, account.id, trades, all_transactions
        )

        return portfolio_history_entities.PortfolioHistoryRunResult(
            account_id=account.id,
            exchange_name=exchange_config.exchange,
            trades_count=len(trades),
            transactions_count=len(all_transactions),
            is_simulated=account.is_simulated,
            trading_type=context.trading_type.value,
            price_symbols_count=len(price_symbols),
        )


def _result_metadata_from_context(
    context: portfolio_history_entities.PortfolioHistoryAccountContext,
) -> dict:
    return {
        "is_simulated": context.account.is_simulated,
        "trading_type": context.trading_type.value,
    }


def _skipped_run_result(
    account_id: str,
    exchange_name: str,
    result_metadata: dict,
) -> portfolio_history_entities.PortfolioHistoryRunResult:
    return portfolio_history_entities.PortfolioHistoryRunResult(
        account_id=account_id,
        exchange_name=exchange_name,
        skipped=True,
        **result_metadata,
    )


def _build_profile_data(context: portfolio_history_entities.PortfolioHistoryAccountContext):
    return profile_data_factory_module.profile_data_for_account(
        context.account,
        context.exchange_account,
        context.exchange_config,
        context.trading_type,
        is_simulated=context.account.is_simulated,
    )


def _derive_price_symbols(
    trade_symbols: list[str],
    transactions: list[dict],
    reference_market: str,
) -> list[str]:
    """Build the set of symbols whose daily prices should be cached."""
    symbols = set(trade_symbols)
    for transaction in transactions:
        currency = transaction.get("currency")
        if currency and currency != reference_market:
            symbols.add(symbol_util.merge_currencies(currency, reference_market))
    return [
        symbol for symbol in symbols
        if _is_valid_trading_symbol(symbol)
    ]


def _is_valid_trading_symbol(symbol: str) -> bool:
    if "/" not in symbol:
        return False
    base_currency, quote_currency = symbol.split("/", 1)
    if base_currency in commons_constants.USD_LIKE_COINS:
        return False
    return bool(base_currency) and bool(quote_currency) and base_currency != quote_currency
