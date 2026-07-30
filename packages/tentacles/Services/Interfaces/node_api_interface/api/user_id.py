#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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

import octobot_sync.server as sync_server
import octobot.community.authentication as community_auth


def evm_to_user_id(evm_address: str) -> str:
    """Translate an EVM wallet address (HTTP Basic login username) to the Starfish
    user_id used throughout the sync-core and scheduler.

    The HTTP API front uses EVM addresses for login; every internal scheduler API
    uses the Starfish user_id.  This helper bridges the boundary.
    """
    wallet = community_auth.CommunityAuthentication.instance().get_wallet(evm_address)
    return sync_server.derive_user_id(wallet.private_key)
