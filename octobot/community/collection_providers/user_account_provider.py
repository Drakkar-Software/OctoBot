#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.


import octobot_commons.singleton.singleton_class as singleton_class
import octobot_node.constants as node_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums

import octobot.community.collection_backend.base_local_collection_provider as base_provider


class AccountProvider(
    base_provider.BaseLocalCollectionProvider[protocol_models.Account, protocol_models.AccountsState],
    singleton_class.Singleton
):
    """
    Singleton provider exposing CRUD operations on protocol Account models.

    Accounts are grouped per wallet address and persisted as an encrypted
    AccountsState envelope.  All CRUD logic lives in the base class.
    """
    COLLECTION = sync_enums.Collections.USER_ACCOUNTS.value
    STATE_VERSION = node_constants.EXCHANGE_ACCOUNTS_STATE_VERSION
    STATE_CLASS = protocol_models.AccountsState
    ITEMS_KEY = "accounts"

    def _get_item_id(self, item: protocol_models.Account) -> str:
        return item.id
