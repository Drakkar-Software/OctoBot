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

import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers.user_account_trading_provider as trading_provider
import octobot_protocol.models as protocol_models
import octobot_trading.personal_data.orders.protocol as orders_protocol
import octobot_trading.personal_data.positions.protocol as positions_protocol
import octobot_trading.personal_data.trades.protocol as trades_protocol
import octobot_trading.personal_data.trades.trades_util as trades_util


def get_account_trading_state_encrypted(
    address: str,
    account_id: str,
) -> dict[str, str] | None:
    try:
        return trading_provider.AccountTradingProvider.instance().load_state_encrypted(
            address,
            account_id,
        )
    except collection_errors.CollectionNoDataError:
        return None

def get_account_trading_state(address: str, account_id: str) -> protocol_models.AccountTradingState:
    return trading_provider.AccountTradingProvider.instance().load_state(address, account_id)


def _account_trading_state_to_summary(
    account_id: str,
    trading_state: protocol_models.AccountTradingState,
) -> protocol_models.AccountTradingWithAccountId:
    return protocol_models.AccountTradingWithAccountId(
        account_id=account_id,
        account_trading=trading_state.account_trading,
    )


def get_account_trading_summaries(
    address: str,
    account_ids: list[str],
) -> list[protocol_models.AccountTradingWithAccountId]:
    summaries: list[protocol_models.AccountTradingWithAccountId] = []
    for account_id in account_ids:
        try:
            trading_state = get_account_trading_state(address, account_id)
        except collection_errors.CollectionNoDataError:
            continue
        summaries.append(_account_trading_state_to_summary(account_id, trading_state))
    return summaries


def update_account_trading(
    address: str,
    account_id: str,
    orders: list[dict],
    trades: list[dict],
    positions: list[dict],
) -> None:
    # Step: load persisted state or start from an empty account trading snapshot.
    try:
        trading_state = get_account_trading_state(address, account_id)
    except collection_errors.CollectionNoDataError:
        trading_state = protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=datetime.datetime.now(datetime.UTC),
            ),
        )
    account_trading = trading_state.account_trading
    # Step: replace orders and positions from the latest automation exchange snapshot.
    account_trading.orders = [orders_protocol.to_protocol_order(order) for order in orders] or None
    account_trading.positions = [
        positions_protocol.to_protocol_position(position) for position in positions
    ] or None
    # Step: upsert trades with exchange identity deduplication.
    existing_trade_dicts = [
        trades_protocol.exchange_columns_dict_from_protocol_trade(protocol_trade)
        for protocol_trade in (account_trading.trades or [])
    ]
    merged_trade_dicts = trades_util.merge_trades_deduped(existing_trade_dicts, trades)
    account_trading.trades = [
        trades_protocol.to_protocol_trade(trade_dict) for trade_dict in merged_trade_dicts
    ] or None
    account_trading.updated_at = datetime.datetime.now(datetime.UTC)
    # Step: persist the updated trading state for this account.
    trading_provider.AccountTradingProvider.instance().save_state(address, account_id, trading_state)
