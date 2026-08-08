#  This file is part of OctoBot Sync (https://github.com/Drakkar-Software/OctoBot)
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

"""Mirror session construction. The sync mechanics live in
`starfish_replica.space`'s `SpaceMirrorChannel`; `service.py` wires them
together."""

from __future__ import annotations

from typing import TypedDict

from starfish_spaces.client import ClientOpts, DeviceKeys
from starfish_spaces.session import BuildSessionOpts, Session, build_session

import octobot_sync.constants as sync_constants


class DerivedIdentity(TypedDict):
    """The wallet-derived identity `build_mirror_session` expects — build it
    with `derived_identity_for_mirror()`."""

    userId: str
    keys: DeviceKeys


async def build_mirror_session(
    derived: DerivedIdentity, sync_url: str, name: str = "octobot-node-mirror"
) -> Session:
    """`sync_url` is the same sync server `create_sync_client` already targets:
    `dk` is another namespace on it, not a separate host."""
    client_opts: ClientOpts = {
        "baseUrl": f"{sync_url.rstrip('/')}/{sync_constants.SYNC_MOUNT_PATH}",
        "namespace": "dk",
    }
    return await build_session(
        BuildSessionOpts(
            user_id=derived["userId"],
            keys=derived["keys"],
            client_opts=client_opts,
            name=name,
        )
    )


def derived_identity_for_mirror(private_key: str) -> DerivedIdentity:
    """Reshape octobot_sync's own wallet-derived root identity into what
    `build_mirror_session()` takes, so the node writes into the same mirror
    space the wallet's other devices use."""
    from octobot_sync.auth.provider import derive_root_identity

    root = derive_root_identity(private_key)
    return DerivedIdentity(
        userId=root.user_id,
        keys={
            "edPriv": root.keys.ed_priv,
            "edPub": root.keys.ed_pub,
            "kemPriv": root.keys.kem_priv,
            "kemPub": root.keys.kem_pub,
        },
    )
