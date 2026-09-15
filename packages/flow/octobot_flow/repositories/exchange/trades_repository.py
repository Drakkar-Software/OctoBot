import dataclasses
import typing

import octobot_commons.logging as commons_logging
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.personal_data.trades.trades_util as trades_util_module

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


def _split_symbols_by_fetch_mode(
    symbols: list[str],
    symbol_since_ms: dict[str, int] | None,
) -> tuple[list[str], dict[str, int]]:
    if not symbol_since_ms:
        return list(symbols), {}
    full_symbols: list[str] = []
    incremental_symbols: dict[str, int] = {}
    for trading_symbol in symbols:
        if trading_symbol in symbol_since_ms:
            incremental_symbols[trading_symbol] = symbol_since_ms[trading_symbol]
        else:
            full_symbols.append(trading_symbol)
    return full_symbols, incremental_symbols


def _merge_parsed_trades(parsed_trade_batches: list[list[dict]]) -> list[dict]:
    merged_trades: list[dict] = []
    for parsed_trade_batch in parsed_trade_batches:
        if not parsed_trade_batch:
            continue
        merged_trades = trades_util_module.merge_trades_deduped(merged_trades, parsed_trade_batch)
    return merged_trades


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
        symbol_since_ms: dict[str, int] | None = None,
    ) -> list[dict]:
        if not symbols:
            return []

        context = _TradeFetchContext(
            exchange_name=exchange_name,
            account_id=account_id,
            exchange_config_id=exchange_config_id,
            exchange_config_name=exchange_config_name,
        )
        full_symbols, incremental_symbols = _split_symbols_by_fetch_mode(symbols, symbol_since_ms)

        if self.exchange_manager.exchange.get_option_value(
            trading_enums.ExchangeClientOptions.MY_TRADES_SYMBOL_FILTER_IS_CLIENT_SIDE
        ):
            return await self._fetch_all_trades_account_wide(
                symbols,
                full_symbols=full_symbols,
                incremental_symbols=incremental_symbols,
                existing_config_symbols=existing_config_symbols,
                context=context,
            )

        _log_new_symbol_fetches(symbols, existing_config_symbols, context)
        parsed_trades = await self._fetch_paginated_per_symbol(
            full_symbols,
            incremental_symbols,
            context,
        )
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
        since: int | None = None,
        exhaust_history: bool = False,
    ) -> list[dict]:
        fetch_kwargs: dict = {}
        if since is not None:
            fetch_kwargs["since"] = since
        if exhaust_history:
            fetch_kwargs["exhaust_history"] = True
        return await self._get_trades_updater().fetch_trades(symbols, **fetch_kwargs)

    async def _fetch_and_parse_raw_trades(
        self,
        symbols: list[str],
        context: _TradeFetchContext,
        *,
        since: int | None = None,
        exhaust_history: bool = True,
    ) -> list[dict]:
        raw_trades = await self._fetch_raw_trades(
            symbols,
            since=since,
            exhaust_history=exhaust_history,
        )
        parsed_trades, skipped_symbols, skipped_trade_count = _parse_raw_trades(
            self.exchange_manager,
            raw_trades,
        )
        _log_skipped_delisted_trades(skipped_trade_count, skipped_symbols, context)
        return parsed_trades

    async def _fetch_paginated_per_symbol(
        self,
        full_symbols: list[str],
        incremental_symbols: dict[str, int],
        context: _TradeFetchContext,
    ) -> list[dict]:
        parsed_trade_batches: list[list[dict]] = []
        if full_symbols:
            parsed_trade_batches.append(
                await self._fetch_and_parse_raw_trades(full_symbols, context)
            )
        for trading_symbol, since_ms in incremental_symbols.items():
            parsed_trade_batches.append(
                await self._fetch_and_parse_raw_trades(
                    [trading_symbol],
                    context,
                    since=since_ms,
                    exhaust_history=True,
                )
            )
        return _merge_parsed_trades(parsed_trade_batches)

    async def _fetch_all_trades_account_wide(
        self,
        symbols: list[str],
        *,
        full_symbols: list[str],
        incremental_symbols: dict[str, int],
        existing_config_symbols: set[str],
        context: _TradeFetchContext,
    ) -> list[dict]:
        _log_new_symbol_fetches(symbols, existing_config_symbols, context)
        parsed_trade_batches: list[list[dict]] = []
        requested_symbols = set(symbols)
        if incremental_symbols:
            account_wide_since_ms = min(incremental_symbols.values())
            account_wide_trades = await self._fetch_and_parse_raw_trades(
                [],
                context,
                since=account_wide_since_ms,
                exhaust_history=True,
            )
            parsed_trade_batches.append([
                trade
                for trade in account_wide_trades
                if trade.get(_order_columns.SYMBOL.value) in requested_symbols
            ])
        if full_symbols:
            if incremental_symbols:
                for trading_symbol in full_symbols:
                    parsed_trade_batches.append(
                        await self._fetch_and_parse_raw_trades([trading_symbol], context)
                    )
            else:
                parsed_trade_batches.append(
                    await self._fetch_and_parse_raw_trades([], context)
                )
        parsed_trades = _merge_parsed_trades(parsed_trade_batches)
        self._log_fetched_trade_counts_per_symbol(parsed_trades, symbols, context)
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
