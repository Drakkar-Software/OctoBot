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

import octobot_protocol.models as protocol_models
import octobot_node.constants as node_constants
import octobot.community.collection_providers.user_account_provider as account_provider
import octobot.community.collection_backend.errors as collection_errors


def get_accounts_state_encrypted(address: str) -> dict[str, str] | None:
    try:
        return account_provider.AccountProvider.instance().list_items_encrypted(address)
    except collection_errors.CollectionNoDataError:
        return None

def get_accounts_state(address: str) -> protocol_models.AccountsState:
    return protocol_models.AccountsState(
        version=node_constants.EXCHANGE_ACCOUNTS_STATE_VERSION,
        accounts=account_provider.AccountProvider.instance().list_items(address)
    )