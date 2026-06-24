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

import typing

import eth_account
from eth_account.messages import encode_defunct
from fastapi import APIRouter

import octobot.community.authentication as _community_auth
import octobot.constants

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser
except ImportError:
    from api.deps import CurrentUser

router = APIRouter(tags=["config"])

# App-specific EIP-191 challenge the OctoBot wallet signs to derive its OctoChat identity. MUST
# stay byte-identical to the frontend (src/lib/octochat-identity.ts) — changing it changes every
# derived identity and orphans existing tickets.
OCTOCHAT_IDENTITY_CHALLENGE = "octochat:support-identity"


@router.get("/octochat")
def get_octochat_config(current_user: CurrentUser) -> typing.Any:
    # Non-secret OctoChat support-desk config for the web UI. supportDeskRequestLink is null
    # when unconfigured → the frontend hides ticket creation.
    return {
        "syncBase": octobot.constants.SYNC_SERVER_URL,
        "syncNamespace": octobot.constants.SYNC_NAMESPACE,
        "supportDeskRequestLink": octobot.constants.OCTOCHAT_SUPPORT_DESK_REQUEST_LINK,
        "webBase": octobot.constants.OCTOCHAT_WEB_BASE,
    }


@router.get("/octochat-identity")
def get_octochat_identity(current_user: CurrentUser) -> typing.Any:
    # Bind the OctoChat support identity to the OctoBot wallet: sign a fixed challenge with the
    # caller's wallet using a deterministic (RFC 6979) EIP-191 personal_sign. The browser feeds
    # this signature to deriveRootIdentityFromEvmSignature, so the same OctoBot account resolves
    # to the same OctoChat identity — and thus the same support ticket — on every device.
    #
    # The signature is private-key-equivalent for the DERIVED identity (it cannot recover the
    # wallet key). It is auth-gated to the wallet owner, served over the authenticated channel,
    # and never logged.
    wallet = _community_auth.CommunityAuthentication.instance().get_wallet(current_user.email)
    account = eth_account.Account.from_key(wallet.private_key)
    signed = eth_account.Account.sign_message(
        encode_defunct(text=OCTOCHAT_IDENTITY_CHALLENGE),
        private_key=wallet.private_key,
    )
    return {
        "address": account.address,
        "signature": signed.signature.hex(),
    }
