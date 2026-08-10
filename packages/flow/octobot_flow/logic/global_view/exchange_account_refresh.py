#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_commons.constants as commons_constants
import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models
import octobot_trading.api as trading_api
import octobot_trading.errors as trading_errors
import octobot_trading.personal_data.portfolios.protocol as portfolios_protocol

import octobot_flow.entities
import octobot_flow.logic.exchange.orders.order_change_detection as order_change_detection_module
import octobot_flow.logic.exchange.portfolio.valuation_unit as valuation_unit_module


async def refresh_exchange_account(
    exchange_manager,
    trading_type: protocol_models.TradingType,
    previous_open_order_exchange_ids: set[str],
) -> octobot_flow.entities.ExchangeAccountRefreshResult:
    # Step: fetch balance and open orders from the exchange manager.
    await exchange_manager.exchange.get_balance()
    open_orders = await exchange_manager.exchange.get_open_orders()
    trades: list[dict] = []
    positions: list[dict] = []

    # Step: resolve valuation unit and portfolio total in that currency.
    valuation_unit = valuation_unit_module.resolve_portfolio_valuation_unit(exchange_manager)
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    if portfolio_manager is not None:
        portfolio_manager.reference_market = valuation_unit
        handle_mark_price_update = getattr(portfolio_manager, "handle_mark_price_update", None)
        if handle_mark_price_update is not None:
            await handle_mark_price_update()
    portfolio_total = trading_api.get_current_portfolio_value(exchange_manager)

    # Step: build protocol assets and historical snapshot payload.
    portfolio_content = trading_api.get_portfolio(exchange_manager, as_decimal=False)
    detailed_assets = portfolios_protocol.to_protocol_assets(portfolio_content)
    historical_assets = _historical_assets_from_portfolio(
        exchange_manager,
        portfolio_content,
        trading_type,
        valuation_unit,
    )
    evaluation_time = timestamp_util.utc_now_datetime()
    portfolio_snapshot = protocol_models.PortfolioHistoricalValue(
        timestamp=evaluation_time,
        total=portfolio_total,
        assets=historical_assets,
    )
    assets_for_trading_type = [
        protocol_models.DetailedAssetsForTradingType(
            trading_type=trading_type,
            assets=detailed_assets,
        )
    ] if detailed_assets else []

    # Step: detect orders that disappeared since the previous refresh.
    changed_order_ids = order_change_detection_module.detect_changed_order_ids(
        previous_open_order_exchange_ids,
        open_orders,
    )
    open_order_dicts = [
        order_change_detection_module.open_order_to_storage_dict(open_order)
        for open_order in open_orders
    ]
    return octobot_flow.entities.ExchangeAccountRefreshResult(
        assets=assets_for_trading_type,
        portfolio_snapshot=portfolio_snapshot,
        valuation_unit=valuation_unit,
        open_orders=open_order_dicts,
        trades=trades,
        positions=positions,
        changed_order_ids=changed_order_ids,
    )


def _historical_assets_from_portfolio(
    exchange_manager,
    portfolio_content: dict,
    trading_type: protocol_models.TradingType,
    valuation_unit: str,
) -> list[protocol_models.HistoricalAssetsForTradingType]:
    historical_asset_values: list[protocol_models.HistoricalAssetValue] = []
    for symbol, symbol_balance in portfolio_content.items():
        total_holdings = float(symbol_balance.get(commons_constants.PORTFOLIO_TOTAL) or 0)
        if total_holdings == 0:
            continue
        try:
            unit_price = float(
                trading_api.get_current_crypto_currency_value(exchange_manager, symbol)
            )
        except (KeyError, trading_errors.MissingPriceDataError):
            unit_price = 0.0
        asset_value = unit_price * total_holdings
        historical_asset_values.append(
            protocol_models.HistoricalAssetValue(
                symbol=str(symbol),
                holdings=total_holdings,
                value=asset_value,
            )
        )
    if not historical_asset_values:
        return []
    return [
        protocol_models.HistoricalAssetsForTradingType(
            trading_type=trading_type,
            assets=historical_asset_values,
        )
    ]
