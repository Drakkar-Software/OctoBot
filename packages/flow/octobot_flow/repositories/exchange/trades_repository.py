import dataclasses
import typing

import octobot_commons.logging as commons_logging
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.personal_data as trading_personal_data

import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import

logger = commons_logging.get_logger("PortfolioHistoryJob")

_order_columns = trading_enums.ExchangeConstantsOrderColumns


@dataclasses.dataclass(frozen=True, slots=True)
class _TradeFetchContext:
    exchange_name: str
    account_id: str
    exchange_config_id: str
    exchange_config_name: str

    @property
    def config_label(self) -> str:
        return self.exchange_config_name or self.exchange_config_id


def _raw_trade_symbol(raw_trade: dict) -> str | None:
    trade_symbol = raw_trade.get(_order_columns.SYMBOL.value)
    if trade_symbol is None:
        return None
    return str(trade_symbol)


def _is_live_market_trade(exchange_manager, raw_trade: dict) -> bool:
    trade_symbol = _raw_trade_symbol(raw_trade)
    if not trade_symbol:
        return False
    return exchange_manager.symbol_exists(trade_symbol)


def _parse_raw_trades(
    exchange_manager,
    raw_trades: list[dict],
) -> tuple[list[dict], set[str], int]:
    parsed_trades: list[dict] = []
    skipped_symbols: set[str] = set()
    skipped_trade_count = 0
    for raw_trade in raw_trades:
        if not _is_live_market_trade(exchange_manager, raw_trade):
            skipped_trade_count += 1
            trade_symbol = _raw_trade_symbol(raw_trade)
            if trade_symbol:
                skipped_symbols.add(trade_symbol)
            continue
        if parsed_trade := trading_personal_data.TradesUpdater.ensure_parsing(
            exchange_manager,
            raw_trade,
        ):
            parsed_trades.append(parsed_trade)
    return parsed_trades, skipped_symbols, skipped_trade_count


def _log_skipped_delisted_trades(
    skipped_trade_count: int,
    skipped_symbols: set[str],
    context: _TradeFetchContext,
) -> None:
    if not skipped_trade_count:
        return
    logger.info(
        "Skipped %d trades on delisted/unknown markets before parsing for %s account %s: %s",
        skipped_trade_count,
        context.exchange_name,
        context.account_id,
        ", ".join(sorted(skipped_symbols)),
    )


def _log_new_symbol_fetches(
    symbols: list[str],
    existing_config_symbols: set[str],
    context: _TradeFetchContext,
) -> None:
    for trading_symbol in symbols:
        if trading_symbol not in existing_config_symbols:
            logger.info(
                "Fetching trade history for new symbol %s on %s "
                "(account %s, config %s)",
                trading_symbol,
                context.exchange_name,
                context.account_id,
                context.config_label,
            )


def _log_fetched_trade_count(
    trading_symbol: str,
    count: int,
    context: _TradeFetchContext,
) -> None:
    logger.info(
        "Fetched %d trades for %s on %s (account %s, config %s)",
        count,
        trading_symbol,
        context.exchange_name,
        context.account_id,
        context.config_label,
    )


class TradesRepository(base_exchange_repository_import.BaseExchangeRepository):

    @classmethod
    async def ensure_temporary_trades_channel(cls, exchange_manager) -> None:
        await trading_exchanges.create_exchange_channels(exchange_manager)
        await trading_exchanges.create_producers(
            exchange_manager,
            [trading_personal_data.TradesUpdater],
            start_producers=False,
        )

    async def fetch_trades(self, symbols: list[str]) -> list[dict]:
        if not symbols:
            return []
        raw_trades = await self._fetch_raw_trades(symbols)
        parsed_trades, _, _ = _parse_raw_trades(self.exchange_manager, raw_trades)
        return parsed_trades

    async def fetch_trades_paginated(
        self,
        symbols: list[str],
        *,
        existing_config_symbols: set[str],
        exchange_name: str,
        account_id: str,
        exchange_config_id: str,
        exchange_config_name: str,
    ) -> list[dict]:
        if not symbols:
            return []

        context = _TradeFetchContext(
            exchange_name=exchange_name,
            account_id=account_id,
            exchange_config_id=exchange_config_id,
            exchange_config_name=exchange_config_name,
        )

        if self.exchange_manager.exchange.get_option_value(
            trading_enums.ExchangeClientOptions.MY_TRADES_SYMBOL_FILTER_IS_CLIENT_SIDE
        ):
            return await self._fetch_all_trades_account_wide(
                symbols,
                existing_config_symbols=existing_config_symbols,
                context=context,
            )

        _log_new_symbol_fetches(symbols, existing_config_symbols, context)
        parsed_trades = await self._fetch_and_parse_raw_trades(symbols, context)
        self._log_fetched_trade_counts_per_symbol(parsed_trades, symbols, context)
        return parsed_trades

    def _get_trades_updater(self) -> trading_personal_data.TradesUpdater:
        return typing.cast(
            trading_personal_data.TradesUpdater,
            self.get_channel_updater(trading_constants.TRADES_CHANNEL),
        )

    async def _fetch_raw_trades(
        self,
        symbols: list[str],
        *,
        exhaust_history: bool = False,
    ) -> list[dict]:
        return await self._get_trades_updater().fetch_trades(
            symbols,
            exhaust_history=exhaust_history,
        )

    async def _fetch_all_trades_account_wide(
        self,
        symbols: list[str],
        *,
        existing_config_symbols: set[str],
        context: _TradeFetchContext,
    ) -> list[dict]:
        _log_new_symbol_fetches(symbols, existing_config_symbols, context)
        parsed_trades = await self._fetch_and_parse_raw_trades([], context)
        self._log_fetched_trade_counts_per_symbol(parsed_trades, symbols, context)
        return parsed_trades

    async def _fetch_and_parse_raw_trades(
        self,
        symbols: list[str],
        context: _TradeFetchContext,
    ) -> list[dict]:
        raw_trades = await self._fetch_raw_trades(symbols, exhaust_history=True)
        parsed_trades, skipped_symbols, skipped_trade_count = _parse_raw_trades(
            self.exchange_manager,
            raw_trades,
        )
        _log_skipped_delisted_trades(skipped_trade_count, skipped_symbols, context)
        return parsed_trades

    def _log_fetched_trade_counts_per_symbol(
        self,
        parsed_trades: list[dict],
        symbols: list[str],
        context: _TradeFetchContext,
    ) -> None:
        trades_by_symbol: dict[str, int] = {}
        for trade in parsed_trades:
            trade_symbol = trade.get(_order_columns.SYMBOL.value)
            if trade_symbol:
                trades_by_symbol[trade_symbol] = trades_by_symbol.get(trade_symbol, 0) + 1
        for trading_symbol in symbols:
            _log_fetched_trade_count(
                trading_symbol,
                trades_by_symbol.get(trading_symbol, 0),
                context,
            )
