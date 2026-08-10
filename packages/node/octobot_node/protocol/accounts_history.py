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

import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers.user_account_history_provider as history_provider

import octobot_flow.logic.accounts.portfolio_history as portfolio_history_module


def get_portfolio_history_state(
    user_id: str,
    account_id: str,
) -> protocol_models.PortfolioHistoricalValuesState:
    try:
        return history_provider.AccountHistoryProvider.instance().load_state(user_id, account_id)
    except collection_errors.CollectionNoDataError:
        return protocol_models.PortfolioHistoricalValuesState(
            version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
            history=None,
        )


def save_portfolio_evaluation(
    user_id: str,
    account_id: str,
    snapshot: protocol_models.PortfolioHistoricalValue,
    valuation_unit: str,
    evaluation_time: datetime.datetime,
) -> protocol_models.PortfolioHistoricalValuesState:
    history_state = get_portfolio_history_state(user_id, account_id)
    existing_values = (
        history_state.history.values
        if history_state.history is not None and history_state.history.values
        else []
    )
    merged_values = portfolio_history_module.merge_snapshot(
        existing_values,
        snapshot,
        evaluation_time,
    )
    updated_history = protocol_models.PortfolioHistoricalValues(
        unit=valuation_unit,
        values=merged_values,
    )
    updated_state = protocol_models.PortfolioHistoricalValuesState(
        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
        history=updated_history,
    )
    history_provider.AccountHistoryProvider.instance().save_state(
        user_id,
        account_id,
        updated_state,
    )
    return updated_state
