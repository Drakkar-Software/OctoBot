import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_providers as collection_providers
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_util as exchange_util_module

logger = commons_logging.get_logger("PortfolioHistoryJob")

DEFAULT_MIN_HOLDINGS_THRESHOLD = 1e-8


def discover_trade_symbols(
    exchange_manager,
    *,
    seed_symbols: list[str],
    account: protocol_models.Account,
    account_trading: protocol_models.AccountTrading | None,
    fresh_transactions: list[dict],
    reference_market: str,
    min_holdings_threshold: float = DEFAULT_MIN_HOLDINGS_THRESHOLD,
) -> list[str]:
    discovered_symbols: set[str] = set(seed_symbols or [])

    if account_trading is not None:
        _add_symbols_from_persisted_trades(discovered_symbols, account_trading)
        _add_symbols_from_persisted_transactions(
            discovered_symbols,
            exchange_manager,
            account_trading,
            reference_market,
        )

    _add_symbols_from_fresh_transactions(
        discovered_symbols,
        exchange_manager,
        fresh_transactions,
        reference_market,
    )
    _add_symbols_from_portfolio_holdings(
        discovered_symbols,
        exchange_manager,
        account,
        reference_market,
        min_holdings_threshold,
    )
    return sorted(discovered_symbols)


def trade_confirmed_symbols_from_fetched_trades(fetched_trades: list[dict]) -> set[str]:
    order_columns = trading_enums.ExchangeConstantsOrderColumns
    trade_confirmed_symbols: set[str] = set()
    for trade in fetched_trades:
        trade_symbol = trade.get(order_columns.SYMBOL.value)
        if trade_symbol:
            trade_confirmed_symbols.add(trade_symbol)
    return trade_confirmed_symbols


def persist_trade_confirmed_symbols_to_exchange_config(
    wallet_id: str,
    exchange_config: protocol_models.ExchangeConfig,
    trade_confirmed_symbols: set[str],
) -> list[str]:
    existing_config_symbols = set(exchange_config.historical_trade_symbols or [])
    new_trade_symbols = sorted(trade_confirmed_symbols - existing_config_symbols)
    if not new_trade_symbols:
        return []

    account_provider = collection_providers.AccountProvider.instance()
    updated_config = account_provider.get_exchange_config(wallet_id, exchange_config.id)
    updated_config.historical_trade_symbols = sorted(
        existing_config_symbols | trade_confirmed_symbols
    )
    account_provider.update_exchange_config(wallet_id, updated_config)
    return new_trade_symbols


def _add_symbols_from_persisted_trades(
    discovered_symbols: set[str],
    account_trading: protocol_models.AccountTrading,
) -> None:
    for trade in account_trading.trades or []:
        if trade.symbol:
            discovered_symbols.add(trade.symbol)


def _add_symbols_from_persisted_transactions(
    discovered_symbols: set[str],
    exchange_manager,
    account_trading: protocol_models.AccountTrading,
    reference_market: str,
) -> None:
    for transaction in account_trading.transactions or []:
        _add_market_pair_for_currency(
            discovered_symbols,
            exchange_manager,
            transaction.asset,
            reference_market,
        )


def _add_symbols_from_fresh_transactions(
    discovered_symbols: set[str],
    exchange_manager,
    fresh_transactions: list[dict],
    reference_market: str,
) -> None:
    transaction_columns = trading_enums.ExchangeConstantsTransactionColumns
    for transaction in fresh_transactions:
        transaction_currency = transaction.get(transaction_columns.CURRENCY.value)
        _add_market_pair_for_currency(
            discovered_symbols,
            exchange_manager,
            transaction_currency,
            reference_market,
        )


def _add_symbols_from_portfolio_holdings(
    discovered_symbols: set[str],
    exchange_manager,
    account: protocol_models.Account,
    reference_market: str,
    min_holdings_threshold: float,
) -> None:
    portfolio_content = _portfolio_content_from_account(account, min_holdings_threshold)
    if not portfolio_content:
        return
    for base_currency in portfolio_content:
        _add_market_pair_for_currency(
            discovered_symbols,
            exchange_manager,
            base_currency,
            reference_market,
        )


def _portfolio_content_from_account(
    account: protocol_models.Account,
    min_holdings_threshold: float,
) -> dict[str, dict[str, float]]:
    portfolio_content: dict[str, dict[str, float]] = {}
    if not account.assets:
        return portfolio_content
    for assets_for_trading_type in account.assets:
        for asset in assets_for_trading_type.assets or []:
            asset_total = float(asset.total or 0)
            if abs(asset_total) <= min_holdings_threshold:
                continue
            portfolio_content[asset.symbol] = {
                commons_constants.PORTFOLIO_TOTAL: asset_total,
                commons_constants.PORTFOLIO_AVAILABLE: float(asset.available or asset.total or 0),
            }
    return portfolio_content


def _add_market_pair_for_currency(
    discovered_symbols: set[str],
    exchange_manager,
    currency: str | None,
    reference_market: str,
) -> None:
    if not currency or currency == reference_market or currency in commons_constants.USD_LIKE_COINS:
        return
    direct_symbol, _is_reversed_symbol = exchange_util_module.get_associated_symbol(
        exchange_manager,
        currency,
        reference_market,
    )
    if direct_symbol is not None:
        discovered_symbols.add(direct_symbol)
        return
    merged_symbol = symbol_util.merge_currencies(currency, reference_market)
    if exchange_manager.symbol_exists(merged_symbol):
        discovered_symbols.add(merged_symbol)
