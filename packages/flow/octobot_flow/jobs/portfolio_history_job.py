import asyncio
import time

import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_protocol.models as protocol_models
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.api as trading_api
import octobot_trading.api.exchange as exchange_api
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data_module
import octobot_trading.util.protocol_trading_mapping as protocol_trading_mapping

import octobot_flow.entities
import octobot_flow.entities.portfolio_history as portfolio_history_entities
import octobot_flow.logic.configuration.profile_data_factory as profile_data_factory_module
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers

import octobot_flow.logic.portfolio_history.trading_history_merge as trading_history_merge_module
import octobot_flow.logic.portfolio_history.daily_price_cache_updater as daily_price_cache_updater_module
import octobot_flow.logic.portfolio_history.trade_fetch_cursors as trade_fetch_cursors_module
import octobot_flow.logic.portfolio_history.trade_symbols_discovery as trade_symbols_discovery_module
import octobot_flow.repositories.exchange.trades_repository as trades_repository_module
import octobot_flow.repositories.exchange.transactions_repository as transactions_repository_module

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
        account_trading = _load_account_trading(self.wallet_id, account.id)
        existing_config_symbols = set(exchange_config.historical_trade_symbols or [])
        seed_symbols = list(context.trade_symbols)

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

            currencies_with_balance = _currencies_with_balance_from_account(account)
            if currencies_with_balance:
                deposits = await tx_repo.fetch_deposits(currencies=currencies_with_balance)
                withdrawals = await tx_repo.fetch_withdrawals(currencies=currencies_with_balance)
            else:
                deposits = []
                withdrawals = []
            all_transactions = deposits + withdrawals

            reference_market = _reference_market_from_account_assets(
                account,
                exchange_config.exchange,
            )
            discovered_symbols = trade_symbols_discovery_module.discover_trade_symbols(
                exchange_manager,
                seed_symbols=seed_symbols,
                account=account,
                account_trading=account_trading,
                fresh_transactions=all_transactions,
                reference_market=reference_market,
            )
            symbol_since_ms = await _build_trade_fetch_symbol_since_ms(
                discovered_symbols,
                account_trading,
                exchange_config,
                exchange_type,
                account.id,
                self.data_root,
            )
            fetched_trades_count = 0
            trades = await trades_repo.fetch_trades_paginated(
                discovered_symbols,
                existing_config_symbols=existing_config_symbols,
                exchange_name=exchange_config.exchange,
                account_id=account.id,
                exchange_config_id=exchange_config.id,
                exchange_config_name=exchange_config.name,
                symbol_since_ms=symbol_since_ms or None,
            )
            fetched_trades_count = len(trades)
            trades, dropped_trade_symbols = _filter_trades_on_live_markets(
                exchange_manager,
                trades,
            )
            if dropped_trade_symbols:
                logger.info(
                    "Dropped %d trades on delisted/unknown markets for %s account %s: %s",
                    fetched_trades_count - len(trades),
                    exchange_config.exchange,
                    account.id,
                    ", ".join(sorted(dropped_trade_symbols)),
                )

            live_discovered_symbols = _filter_symbols_on_live_markets(
                exchange_manager,
                discovered_symbols,
            )
            price_symbols = _derive_price_symbols(
                live_discovered_symbols,
                all_transactions,
                reference_market,
            )
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

        trade_confirmed_symbols = trade_symbols_discovery_module.trade_confirmed_symbols_from_fetched_trades(
            trades,
        )
        new_trade_symbols = trade_symbols_discovery_module.persist_trade_confirmed_symbols_to_exchange_config(
            self.wallet_id,
            exchange_config,
            trade_confirmed_symbols,
        )
        if new_trade_symbols:
            logger.info(
                "Added trade-confirmed symbols to historical_trade_symbols on %s config %s "
                "(account %s): %s",
                exchange_config.exchange,
                exchange_config.name or exchange_config.id,
                account.id,
                ", ".join(new_trade_symbols),
            )

        return portfolio_history_entities.PortfolioHistoryRunResult(
            account_id=account.id,
            exchange_name=exchange_config.exchange,
            trades_count=len(trades),
            transactions_count=len(all_transactions),
            is_simulated=account.is_simulated,
            trading_type=context.trading_type.value,
            price_symbols_count=len(price_symbols),
            trade_symbols_count=len(discovered_symbols),
        )


def _load_account_trading(
    wallet_id: str,
    account_id: str,
) -> protocol_models.AccountTrading | None:
    try:
        trading_state = collection_providers.AccountTradingProvider.instance().load_state(
            wallet_id,
            account_id,
        )
        return trading_state.account_trading
    except collection_errors.CollectionNoDataError:
        return None


async def _build_trade_fetch_symbol_since_ms(
    discovered_symbols: list[str],
    account_trading: protocol_models.AccountTrading | None,
    exchange_config: protocol_models.ExchangeConfig,
    exchange_type: str,
    account_id: str,
    data_root: str | None,
) -> dict[str, int]:
    # Load cached daily closes and derive per-symbol incremental trade-fetch cursors.
    daily_prices = await trading_api.load_daily_prices(
        exchange_config.exchange,
        exchange_type,
        exchange_config.sandboxed,
        data_root,
    )
    symbol_since_ms = trade_fetch_cursors_module.build_symbol_since_ms(
        discovered_symbols,
        account_trading,
        daily_prices,
    )

    # Classify symbols for logging: incremental vs full-history vs no-candle fallback.
    persisted_trade_symbols = trade_fetch_cursors_module.symbols_with_persisted_trades(
        account_trading,
    )
    incremental_symbols = set(symbol_since_ms)
    full_fetch_symbols = [
        trading_symbol
        for trading_symbol in discovered_symbols
        if trading_symbol not in incremental_symbols
    ]
    global_cursor_symbols = sorted(
        trading_symbol
        for trading_symbol in discovered_symbols
        if trading_symbol in incremental_symbols
        and trade_fetch_cursors_module.uses_global_daily_price_cursor(daily_prices, trading_symbol)
    )
    no_candle_fallback_symbols = sorted(
        trading_symbol
        for trading_symbol in persisted_trade_symbols
        if trading_symbol in discovered_symbols
        and trading_symbol not in incremental_symbols
        and not trade_fetch_cursors_module.uses_global_daily_price_cursor(daily_prices, trading_symbol)
    )

    if incremental_symbols or full_fetch_symbols:
        logger.info(
            "Trade fetch for %s account %s: %d incremental, %d full-history symbol(s)",
            exchange_config.exchange,
            account_id,
            len(incremental_symbols),
            len(full_fetch_symbols),
        )
    if global_cursor_symbols:
        logger.info(
            "Using global daily candle cursor for USD-like pair(s) on %s account %s: %s",
            exchange_config.exchange,
            account_id,
            ", ".join(global_cursor_symbols),
        )
    if no_candle_fallback_symbols:
        logger.info(
            "Falling back to full trade history for %s on %s account %s "
            "(persisted trades but no daily candle cache): %s",
            exchange_config.exchange,
            exchange_config.name or exchange_config.id,
            account_id,
            ", ".join(no_candle_fallback_symbols),
        )
    return symbol_since_ms


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


def _currencies_with_balance_from_account(
    account: protocol_models.Account,
    min_holdings_threshold: float = 1e-8,
) -> list[str]:
    currency_totals: dict[str, float] = {}
    if account.assets:
        for assets_for_trading_type in account.assets:
            for asset in assets_for_trading_type.assets or []:
                asset_total = float(asset.total or 0)
                if asset_total <= min_holdings_threshold:
                    continue
                currency_totals[asset.symbol] = max(
                    currency_totals.get(asset.symbol, 0),
                    asset_total,
                )
    return sorted(currency_totals.keys())


def _reference_market_from_account_assets(
    account: protocol_models.Account,
    exchange_name: str,
    min_holdings_threshold: float = 1e-8,
) -> str:
    usd_like_holdings: dict[str, float] = {}
    if account.assets:
        for assets_for_trading_type in account.assets:
            for asset in assets_for_trading_type.assets or []:
                if asset.symbol not in commons_constants.USD_LIKE_COINS:
                    continue
                asset_total = float(asset.total or 0)
                if asset_total <= min_holdings_threshold:
                    continue
                usd_like_holdings[asset.symbol] = max(
                    usd_like_holdings.get(asset.symbol, 0),
                    asset_total,
                )
    if usd_like_holdings:
        return max(usd_like_holdings, key=usd_like_holdings.get)
    return exchange_api.get_default_exchange_reference_market(exchange_name)


def _filter_trades_on_live_markets(
    exchange_manager,
    trades: list[dict],
) -> tuple[list[dict], set[str]]:
    order_columns = trading_enums.ExchangeConstantsOrderColumns
    live_symbols = set(exchange_manager.client_symbols or [])
    kept_trades: list[dict] = []
    dropped_symbols: set[str] = set()
    for trade in trades:
        trade_symbol = trade.get(order_columns.SYMBOL.value)
        if not trade_symbol or trade_symbol not in live_symbols:
            if trade_symbol:
                dropped_symbols.add(trade_symbol)
            continue
        kept_trades.append(trade)
    return kept_trades, dropped_symbols


def _filter_symbols_on_live_markets(
    exchange_manager,
    symbols: list[str],
) -> list[str]:
    live_symbols = set(exchange_manager.client_symbols or [])
    return sorted(symbol for symbol in symbols if symbol in live_symbols)


def _derive_price_symbols(
    trade_symbols: list[str],
    transactions: list[dict],
    reference_market: str,
) -> list[str]:
    """Build the set of symbols whose daily prices should be cached."""
    base_assets: set[str] = set()
    for trading_symbol in trade_symbols:
        if not symbol_util.is_symbol(trading_symbol):
            continue
        base_currency, _quote_currency = symbol_util.parse_symbol(trading_symbol).base_and_quote()
        if symbol_util.is_usd_like_coin(base_currency):
            continue
        if base_currency and base_currency != reference_market:
            base_assets.add(base_currency)
    for transaction in transactions:
        transaction_currency = transaction.get("currency")
        if (
            not transaction_currency
            or transaction_currency == reference_market
            or symbol_util.is_usd_like_coin(transaction_currency)
        ):
            continue
        base_assets.add(transaction_currency)
    valuation_symbols = [
        symbol_util.merge_currencies(base_asset, reference_market)
        for base_asset in base_assets
    ]
    return sorted(
        valuation_symbol
        for valuation_symbol in valuation_symbols
        if _is_valid_trading_symbol(valuation_symbol)
    )


def _is_valid_trading_symbol(symbol: str) -> bool:
    if not symbol_util.is_symbol(symbol):
        return False
    base_currency, quote_currency = symbol_util.parse_symbol(symbol).base_and_quote()
    if symbol_util.is_usd_like_coin(base_currency):
        return False
    return bool(base_currency) and bool(quote_currency) and base_currency != quote_currency
