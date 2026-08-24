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

import datetime
import decimal

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
    valued_days = portfolio_value_history_module.compute_daily_portfolio_values(
        daily_holdings, daily_prices, latest_tickers, reference_market=valuation_unit,
    )

    # Step 7: Build and return result (not saved).
    history_values = [
        protocol_models.PortfolioHistoricalValue(
            timestamp=_timestamp_to_datetime(day["timestamp"]),
            total=day["value"],
            assets=[],
        )
        for day in valued_days
    ]
    if not history_values:
        return _empty_state()
    return protocol_models.PortfolioHistoricalValuesState(
        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
        history=protocol_models.PortfolioHistoricalValues(
            unit=valuation_unit,
            values=history_values,
        ),
    )


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

def _timestamp_to_datetime(timestamp: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)