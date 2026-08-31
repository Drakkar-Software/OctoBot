#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_commons.logging as octobot_commons_logging
import octobot_protocol.models as protocol_models
import octobot_trading.api as trading_api
import octobot_trading.errors as trading_errors
import octobot_trading.personal_data as personal_data
import octobot_trading.personal_data.portfolios.portfolio_util as portfolio_util_module
import octobot_trading.personal_data.portfolios.protocol as portfolios_protocol

import octobot_flow.entities
import octobot_flow.logic.exchange.simulator.simulated_order_fill_detector as simulated_order_fill_detector_module
import octobot_flow.repositories.exchange.exchange_repository_factory as exchange_repository_factory_module
import octobot_flow.repositories.exchange.tickers_repository as tickers_repository_module


def _get_logger() -> octobot_commons_logging.BotLogger:
    return octobot_commons_logging.get_logger("ExchangeAccountRefresh")


def _create_exchange_repository_factory(exchange_manager, *, is_simulated: bool = False):
    return exchange_repository_factory_module.ExchangeRepositoryFactory(
        exchange_manager,
        known_automations=[],
        fetched_exchange_data=octobot_flow.entities.FetchedExchangeData(),
        is_simulated=is_simulated,
    )


def _detect_changed_order_ids(
    previous_open_order_exchange_ids: set[str],
    current_open_orders: list[dict],
) -> set[str]:
    if not previous_open_order_exchange_ids:
        return set()
    current_open_order_exchange_ids = personal_data.open_order_exchange_ids_from_open_orders(
        current_open_orders
    )
    return previous_open_order_exchange_ids - current_open_order_exchange_ids


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
    repository_factory = None
    if is_simulated:
        if previous_open_orders is None:
            raise ValueError("previous_open_orders is required for simulated account refresh.")
        portfolio_content = trading_api.get_portfolio(exchange_manager, as_decimal=False)
        valuation_unit = trading_api.resolve_portfolio_valuation_unit(exchange_manager)
        order_symbols = simulated_order_fill_detector_module.symbols_from_open_orders(previous_open_orders)
        valuation_symbols = personal_data.valuation_symbols_from_portfolio(
            exchange_manager,
            portfolio_content,
            valuation_unit,
        )
        symbols_to_fetch = sorted(set(order_symbols) | set(valuation_symbols))
        tickers = await _fetch_tickers(exchange_manager, symbols_to_fetch)
        ticker_close_by_symbol = personal_data.ticker_close_by_symbol_from_tickers(tickers)
        open_orders = simulated_order_fill_detector_module.resolve_simulated_open_orders(
            previous_open_orders,
            ticker_close_by_symbol,
        )
    else:
        repository_factory = _create_exchange_repository_factory(exchange_manager)
        portfolio_repository = repository_factory.get_portfolio_repository()
        await portfolio_repository.fetch_and_apply_portfolio()
        if not fetch_open_orders:
            open_orders = []
        else:
            try:
                open_orders = await repository_factory.get_orders_repository().fetch_open_orders(
                    open_order_symbols or [],
                )
            except trading_errors.NotSupported:
                open_orders = []
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
        simulated_valuation_symbols = personal_data.valuation_symbols_from_portfolio(
            exchange_manager,
            portfolio_content,
            valuation_unit,
        )
        personal_data.refresh_portfolio_valuation(
            exchange_manager,
            valuation_unit,
            tickers=tickers,
            valuation_symbols=simulated_valuation_symbols,
        )
    else:
        portfolio_content = trading_api.get_portfolio(exchange_manager, as_decimal=False)
        valuation_symbols = personal_data.valuation_symbols_from_portfolio(
            exchange_manager, portfolio_content, valuation_unit,
        )
        tickers = await repository_factory.get_tickers_repository().fetch_tickers(valuation_symbols)
        personal_data.refresh_portfolio_valuation(
            exchange_manager,
            valuation_unit,
            tickers=tickers,
            valuation_symbols=valuation_symbols,
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
    ticker_closes = personal_data.ticker_close_by_symbol_from_tickers(tickers) if tickers else {}

    # Step: detect orders that disappeared since the previous refresh.
    changed_order_ids = _detect_changed_order_ids(
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


async def _fetch_tickers(exchange_manager, symbols: list[str]) -> dict[str, dict]:
    if not symbols:
        return {}
    repository_factory = _create_exchange_repository_factory(exchange_manager)
    return await repository_factory.get_tickers_repository().fetch_tickers(symbols)
