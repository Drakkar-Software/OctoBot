#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import decimal
import datetime

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers
import octobot_trading.api as trading_api
import octobot_trading.util.protocol_trading_mapping as protocol_trading_mapping

import octobot_flow.logic.portfolio_history.portfolio_value_history as portfolio_value_history_module


def get_portfolio_history_state(
    user_id: str,
    account_id: str,
) -> protocol_models.PortfolioHistoricalValuesState:
    """Compute portfolio history on-the-fly from persisted data."""
    # Placeholder: the async compute must be awaited from an async context.
    # This synchronous wrapper returns an empty state; callers should use the async version.
    return protocol_models.PortfolioHistoricalValuesState(
        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
        history=None,
    )


async def compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
    user_id: str,
    account_id: str,
    *,
    data_root: str = None,
) -> protocol_models.PortfolioHistoricalValuesState:
    """
    Compute portfolio value history on-the-fly from Account.assets,
    AccountTrading trades/transactions, and persisted price caches.
    """
    # Step 1: Load account and its assets as the latest portfolio anchor.
    try:
        account = collection_providers.AccountProvider.instance().get_account(user_id, account_id)
    except (collection_errors.CollectionNoDataError, collection_errors.ItemNotFoundError):
        return _empty_state()

    portfolio = _portfolio_from_account_assets(account)
    if not portfolio:
        return _empty_state()

    # Step 2: Load AccountTrading trades and transactions.
    try:
        trading_state = collection_providers.AccountTradingProvider.instance().load_state(user_id, account_id)
    except collection_errors.CollectionNoDataError:
        return _empty_state()

    account_trading = trading_state.account_trading

    # Step 3: Resolve exchange info from the account's exchange config.
    exchange_info = _resolve_exchange_info(user_id, account)
    if exchange_info is None:
        return _empty_state()
    exchange_name, exchange_type, sandboxed = exchange_info

    # Step 4: Load persisted caches.
    daily_prices = await trading_api.load_daily_prices(exchange_name, exchange_type, sandboxed, data_root)
    latest_tickers = await trading_api.load_latest_tickers(exchange_name, exchange_type, sandboxed, data_root)

    # Step 5: Compute historical holdings via reverse replay.
    daily_holdings = trading_api.compute_portfolio_historical_holdings_from_latest_portfolio_trades_and_transations(
        portfolio,
        account_trading.trades or [],
        account_trading.transactions or [],
    )

    # Step 6: Daily valuation.
    valuation_unit = "USDT"
    history_values = portfolio_value_history_module.compute_daily_portfolio_values(
        daily_holdings, daily_prices, latest_tickers, reference_market=valuation_unit,
    )

    # Step 7: Build and return result (not saved).
    if not history_values:
        return _empty_state()
    return protocol_models.PortfolioHistoricalValuesState(
        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
        history=protocol_models.PortfolioHistoricalValues(
            unit=valuation_unit,
            values=history_values,
        ),
    )


async def compute_aggregated_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
    user_id: str,
    *,
    is_simulated: bool,
    data_root: str = None,
) -> protocol_models.PortfolioHistoricalValuesState:
    """
    Compute aggregated portfolio value history across all accounts matching is_simulated.
    Each account is valued independently, then daily totals are summed by timestamp.
    """
    accounts = [
        account
        for account in collection_providers.AccountProvider.instance().list_accounts(user_id)
        if account.is_simulated == is_simulated
    ]
    if not accounts:
        return _empty_state()

    account_histories: list[list[protocol_models.PortfolioHistoricalValue]] = []
    for account in accounts:
        account_state = await compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
            user_id,
            account.id,
            data_root=data_root,
        )
        if account_state.history is None or not account_state.history.values:
            continue
        account_histories.append(account_state.history.values)

    if not account_histories:
        return _empty_state()

    valuation_unit = "USDT"
    aggregated_values = _aggregate_portfolio_historical_values(account_histories)
    if not aggregated_values:
        return _empty_state()
    return protocol_models.PortfolioHistoricalValuesState(
        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
        history=protocol_models.PortfolioHistoricalValues(
            unit=valuation_unit,
            values=aggregated_values,
        ),
    )


def _iter_historical_assets(
    history_value: protocol_models.PortfolioHistoricalValue,
):
    if not history_value.assets:
        return
    for assets_for_type in history_value.assets:
        for asset in assets_for_type.assets or []:
            yield assets_for_type.trading_type, asset


def _aggregate_portfolio_historical_values(
    account_histories: list[list[protocol_models.PortfolioHistoricalValue]],
) -> list[protocol_models.PortfolioHistoricalValue]:
    totals_by_day: dict[float, float] = {}
    assets_by_day: dict[float, dict[protocol_models.TradingType, dict[str, list[float]]]] = {}
    for history_values in account_histories:
        for history_value in history_values:
            day_key = portfolio_value_history_module._utc_day_start(
                history_value.timestamp.timestamp(),
            )
            totals_by_day[day_key] = totals_by_day.get(day_key, 0.0) + float(history_value.total)
            day_assets = assets_by_day.setdefault(day_key, {})
            for trading_type, asset in _iter_historical_assets(history_value):
                symbol_totals = day_assets.setdefault(trading_type, {})
                holdings_sum, value_sum = symbol_totals.get(asset.symbol, [0.0, 0.0])
                symbol_totals[asset.symbol] = [
                    holdings_sum + float(asset.holdings),
                    value_sum + float(asset.value),
                ]

    aggregated_values: list[protocol_models.PortfolioHistoricalValue] = []
    for day_key in sorted(totals_by_day):
        assets_for_day = assets_by_day.get(day_key, {})
        assets_by_trading_type: list[protocol_models.HistoricalAssetsForTradingType] = []
        for trading_type in sorted(assets_for_day, key=lambda trading_type_value: trading_type_value.value):
            symbol_totals = assets_for_day[trading_type]
            day_asset_values: list[protocol_models.HistoricalAssetValue] = []
            for symbol, holdings_and_value in sorted(symbol_totals.items()):
                holdings_sum, value_sum = holdings_and_value
                if holdings_sum == 0:
                    continue
                day_asset_values.append(
                    protocol_models.HistoricalAssetValue(
                        symbol=symbol,
                        holdings=holdings_sum,
                        value=value_sum,
                    )
                )
            if day_asset_values:
                assets_by_trading_type.append(
                    protocol_models.HistoricalAssetsForTradingType(
                        trading_type=trading_type,
                        assets=day_asset_values,
                    )
                )
        aggregated_values.append(
            protocol_models.PortfolioHistoricalValue(
                timestamp=datetime.datetime.fromtimestamp(day_key, tz=datetime.timezone.utc),
                total=totals_by_day[day_key],
                assets=assets_by_trading_type or None,
            )
        )
    return aggregated_values


def _empty_state() -> protocol_models.PortfolioHistoricalValuesState:
    return protocol_models.PortfolioHistoricalValuesState(
        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
        history=None,
    )


def _portfolio_from_account_assets(account: protocol_models.Account) -> dict[str, dict[str, decimal.Decimal]]:
    """Convert Account.assets to the portfolio dict format used by the builder."""
    portfolio: dict[str, dict[str, decimal.Decimal]] = {}
    if not account.assets:
        return portfolio
    for assets_for_type in account.assets:
        for asset in (assets_for_type.assets or []):
            portfolio[asset.symbol] = {
                commons_constants.PORTFOLIO_TOTAL: decimal.Decimal(str(asset.total)),
                commons_constants.PORTFOLIO_AVAILABLE: decimal.Decimal(str(asset.available or asset.total)),
            }
    return portfolio


def _resolve_exchange_info(
    user_id: str, account: protocol_models.Account
) -> tuple[str, str, bool] | None:
    """Derive exchange identity from the account's first exchange config."""
    specifics = account.specifics
    if specifics is None or specifics.actual_instance is None:
        return None
    exchange_account = specifics.actual_instance
    if not isinstance(exchange_account, protocol_models.ExchangeAccount):
        return None
    config_ids = exchange_account.exchange_config_ids or []
    if not config_ids:
        return None
    try:
        exchange_config = collection_providers.AccountProvider.instance().get_exchange_config(
            user_id, config_ids[0]
        )
    except collection_errors.CollectionNoDataError:
        return None
    exchange_type = protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(
        protocol_models.TradingType.SPOT
    )
    return (
        exchange_config.exchange,
        exchange_type.value if exchange_type else "spot",
        exchange_config.sandboxed,
    )