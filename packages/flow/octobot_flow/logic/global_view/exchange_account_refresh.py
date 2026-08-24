#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import asyncio
import decimal

import octobot_commons.constants as commons_constants
import octobot_commons.logging as octobot_commons_logging
import octobot_protocol.models as protocol_models
import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges.util.exchange_util as exchange_util_module
import octobot_trading.personal_data.portfolios.portfolio_util as portfolio_util_module
import octobot_trading.personal_data.portfolios.protocol as portfolios_protocol

import octobot_flow.entities
import octobot_flow.logic.exchange.orders.order_change_detection as order_change_detection_module
import octobot_flow.logic.exchange.simulator.simulated_order_fill_detector as simulated_order_fill_detector_module
import octobot_flow.repositories.exchange.tickers_repository as tickers_repository_module

def _get_logger() -> octobot_commons_logging.BotLogger:
    return octobot_commons_logging.get_logger("ExchangeAccountRefresh")


async def refresh_exchange_account(
    exchange_manager,
    trading_type: protocol_models.TradingType,
    previous_open_order_exchange_ids: set[str],
    *,
    is_simulated: bool = False,
    previous_open_orders: list[dict] | None = None,
    fetch_open_orders: bool = True,
    open_order_symbols: list[str] | None = None,
) -> octobot_flow.entities.ExchangeAccountRefreshResult:
    await tickers_repository_module.TickersRepository.ensure_temporary_ticker_channel(exchange_manager)

    # Step: fetch balance and open orders from the exchange (real accounts only).
    tickers: dict[str, dict] | None = None
    if is_simulated:
        if previous_open_orders is None:
            raise ValueError("previous_open_orders is required for simulated account refresh.")
        portfolio_content = trading_api.get_portfolio(exchange_manager, as_decimal=False)
        valuation_unit = trading_api.resolve_portfolio_valuation_unit(exchange_manager)
        order_symbols = simulated_order_fill_detector_module.symbols_from_open_orders(previous_open_orders)
        valuation_symbols = _valuation_symbols_from_portfolio(
            exchange_manager,
            portfolio_content,
            valuation_unit,
        )
        symbols_to_fetch = sorted(set(order_symbols) | set(valuation_symbols))
        tickers = await _fetch_tickers(exchange_manager, symbols_to_fetch)
        ticker_close_by_symbol = _ticker_close_by_symbol_from_tickers(tickers)
        open_orders = simulated_order_fill_detector_module.resolve_simulated_open_orders(
            previous_open_orders,
            ticker_close_by_symbol,
        )
    elif not fetch_open_orders:
        await _fetch_and_apply_exchange_balance(exchange_manager)
        open_orders = []
    else:
        await _fetch_and_apply_exchange_balance(exchange_manager)
        open_orders = await _fetch_open_orders_for_symbols(
            exchange_manager,
            open_order_symbols or [],
        )
    trades: list[dict] = []
    positions: list[dict] = []

    # Step: resolve valuation unit and portfolio total in that currency.
    if not is_simulated:
        valuation_unit = trading_api.resolve_portfolio_valuation_unit(exchange_manager)
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    if portfolio_manager is not None:
        portfolio_manager.reference_market = valuation_unit
    if is_simulated:
        portfolio_content = trading_api.get_portfolio(exchange_manager, as_decimal=False)
        simulated_valuation_symbols = _valuation_symbols_from_portfolio(
            exchange_manager,
            portfolio_content,
            valuation_unit,
        )
        await _refresh_portfolio_valuation(
            exchange_manager,
            valuation_unit,
            tickers=tickers,
            valuation_symbols=simulated_valuation_symbols,
        )
    else:
        portfolio_content = trading_api.get_portfolio(exchange_manager, as_decimal=False)
        valuation_symbols = _valuation_symbols_from_portfolio(
            exchange_manager, portfolio_content, valuation_unit,
        )
        tickers = await _fetch_tickers(exchange_manager, valuation_symbols)
        await _refresh_portfolio_valuation(
            exchange_manager, valuation_unit, tickers=tickers, valuation_symbols=valuation_symbols,
        )
    # Step: build protocol assets (holdings only, no historical snapshot).
    portfolio_content = trading_api.get_portfolio(exchange_manager, as_decimal=False)
    balance_summary = octobot_commons_logging.get_private_placeholder_if_necessary(
        portfolio_util_module.get_balance_summary(portfolio_content, use_exchange_format=False)
    )
    _get_logger().info(
        "Fetched [%s] full [%s] portfolio: %s",
        exchange_manager.exchange_name,
        "simulated" if is_simulated else "real",
        balance_summary,
    )
    detailed_assets = portfolios_protocol.to_protocol_assets(portfolio_content)
    assets_for_trading_type = [
        protocol_models.DetailedAssetsForTradingType(
            trading_type=trading_type,
            assets=detailed_assets,
        )
    ] if detailed_assets else []

    # Collect ticker close prices for the persisted latest-tickers cache.
    ticker_closes = _ticker_close_by_symbol_from_tickers(tickers) if tickers else {}

    # Step: detect orders that disappeared since the previous refresh.
    changed_order_ids = order_change_detection_module.detect_changed_order_ids(
        previous_open_order_exchange_ids,
        open_orders,
    )
    return octobot_flow.entities.ExchangeAccountRefreshResult(
        assets=assets_for_trading_type,
        ticker_closes=ticker_closes,
        valuation_unit=valuation_unit,
        open_orders=open_orders,
        trades=trades,
        positions=positions,
        changed_order_ids=changed_order_ids,
    )


async def _fetch_and_apply_exchange_balance(exchange_manager) -> None:
    balance = await exchange_manager.exchange.get_balance()
    non_empty_balance = portfolio_util_module.filter_empty_values(balance)
    decimal_balance = portfolio_util_module.parse_decimal_portfolio(non_empty_balance)
    await exchange_manager.exchange_personal_data.handle_portfolio_update(
        decimal_balance,
        should_notify=False,
    )


async def _fetch_tickers(exchange_manager, symbols: list[str]) -> dict[str, dict]:
    if not symbols:
        return {}
    tickers_repository = tickers_repository_module.TickersRepository(
        exchange_manager,
        known_automations=[],
        fetched_exchange_data=octobot_flow.entities.FetchedExchangeData(),
    )
    return await tickers_repository.fetch_tickers(symbols)


def _ticker_close_by_symbol_from_tickers(tickers: dict[str, dict]) -> dict[str, float]:
    close_column = trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
    ticker_close_by_symbol: dict[str, float] = {}
    for symbol, ticker in tickers.items():
        close_price = ticker.get(close_column)
        if close_price is not None:
            ticker_close_by_symbol[symbol] = float(close_price)
    return ticker_close_by_symbol


async def _refresh_portfolio_valuation(
    exchange_manager,
    valuation_unit: str,
    *,
    tickers: dict[str, dict] | None = None,
    valuation_symbols: list[str] | None = None,
) -> None:
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    if portfolio_manager is None:
        return
    if valuation_symbols is None:
        portfolio_content = trading_api.get_portfolio(exchange_manager, as_decimal=False)
        valuation_symbols = _valuation_symbols_from_portfolio(
            exchange_manager,
            portfolio_content,
            valuation_unit,
        )
    if tickers is None and valuation_symbols:
        tickers = await _fetch_tickers(exchange_manager, valuation_symbols)
    if tickers:
        close_column = trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
        symbols_to_apply = valuation_symbols if valuation_symbols is not None else list(tickers)
        for symbol in symbols_to_apply:
            ticker = tickers.get(symbol)
            if not ticker:
                continue
            close_price = ticker.get(close_column)
            if close_price is None:
                continue
            mark_price = decimal.Decimal(str(close_price))
            portfolio_manager.portfolio_value_holder.value_converter.update_last_price(symbol, mark_price)
            if exchange_manager.symbol_exists(symbol):
                exchange_manager.get_symbol_data(symbol).handle_ticker_update(ticker)
    portfolio_manager.portfolio_value_holder._sync_portfolio_current_value_using_available_currencies_values(
        init_price_fetchers=False,
    )


def _valuation_symbols_from_portfolio(
    exchange_manager,
    portfolio_content: dict,
    valuation_unit: str,
) -> list[str]:
    valuation_symbols: set[str] = set()
    bridge_quote_currencies = []
    if valuation_unit in commons_constants.USD_LIKE_COINS:
        bridge_quote_currencies = [
            quote_currency
            for quote_currency in commons_constants.USD_LIKE_COINS
            if quote_currency != valuation_unit
        ]
    for currency, symbol_balance in portfolio_content.items():
        total_holdings = float(symbol_balance.get(commons_constants.PORTFOLIO_TOTAL) or 0)
        if total_holdings == 0 or currency == valuation_unit:
            continue
        direct_symbol, _is_reversed_symbol = exchange_util_module.get_associated_symbol(
            exchange_manager,
            currency,
            valuation_unit,
        )
        if direct_symbol is not None:
            valuation_symbols.add(direct_symbol)
            continue
        for bridge_quote in bridge_quote_currencies:
            asset_symbol, _is_reversed_symbol = exchange_util_module.get_associated_symbol(
                exchange_manager,
                currency,
                bridge_quote,
            )
            if asset_symbol is None:
                continue
            valuation_symbols.add(asset_symbol)
            if bridge_quote != valuation_unit:
                bridge_symbol, _is_reversed_bridge_symbol = exchange_util_module.get_associated_symbol(
                    exchange_manager,
                    bridge_quote,
                    valuation_unit,
                )
                if bridge_symbol is not None:
                    valuation_symbols.add(bridge_symbol)
            break
    return list(valuation_symbols)


async def _get_open_orders_for_symbol(exchange_manager, symbol: str) -> list[dict]:
    try:
        return await exchange_manager.exchange.get_open_orders(symbol=symbol)
    except trading_errors.UnSupportedSymbolError:
        return []


async def _fetch_open_orders_for_symbols(exchange_manager, symbols: list[str]) -> list[dict]:
    if not symbols:
        return []
    open_orders_by_symbol = await asyncio.gather(*[
        _get_open_orders_for_symbol(exchange_manager, symbol)
        for symbol in symbols
    ])
    orders_by_exchange_id: dict[str, dict] = {}
    order_columns = trading_enums.ExchangeConstantsOrderColumns
    for open_orders in open_orders_by_symbol:
        for open_order in open_orders:
            inner_order = open_order.get(trading_constants.STORAGE_ORIGIN_VALUE, open_order)
            exchange_id = inner_order.get(order_columns.EXCHANGE_ID.value) or inner_order.get(
                order_columns.ID.value
            )
            if exchange_id is None:
                continue
            orders_by_exchange_id[str(exchange_id)] = open_order
    return list(orders_by_exchange_id.values())


