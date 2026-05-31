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

"""Starfish v3 cap-cert identity, derived from an EVM wallet.

The wallet signs a fixed challenge (deterministic EIP-191 ``personal_sign``);
that signature is HKDF-expanded by ``starfish-identities`` into a stable
Ed25519 + X25519 root identity (the EVM key never reaches the wire). The
``WalletCapProvider`` then self-signs a device cap-cert per request, which the
``StarfishClient`` uses to sign every request. ``user_id`` is the Starfish
storage identity (``sha256(rootEdPub)[:32]``), replacing the EVM address.
"""

from typing import Any

import web3
from eth_account.messages import encode_defunct

import starfish_identities

import octobot_sync.constants as constants


def _sign_bootstrap(private_key: str, challenge: str) -> bytes:
    # Deterministic ECDSA (RFC 6979) — reproducible across devices/sessions.
    signed = web3.Account.sign_message(  # pylint: disable=no-value-for-parameter
        encode_defunct(text=challenge), private_key=private_key
    )
    return bytes(signed.signature)


def derive_root_identity(
    private_key: str, challenge: str = constants.SYNC_BOOTSTRAP_CHALLENGE
) -> starfish_identities.RootIdentity:
    """Derive the Starfish root identity for an EVM wallet private key.

    Deterministic for a given (private_key, challenge): same wallet → same
    identity → same ``user_id`` on every device. The client cap provider, the
    server allowlist, and the server bridge wallet resolver MUST all call this
    with the SAME challenge so their ``user_id`` values agree.
    """
    address = web3.Account.from_key(private_key).address  # pylint: disable=no-value-for-parameter
    signature = _sign_bootstrap(private_key, challenge)
    return starfish_identities.derive_root_identity_from_evm_signature(
        address, signature, challenge=challenge
    )


def derive_user_id(
    private_key: str, challenge: str = constants.SYNC_BOOTSTRAP_CHALLENGE
) -> str:
    """Return the Starfish ``user_id`` an EVM wallet key derives to."""
    return derive_root_identity(private_key, challenge).user_id


class WalletCapProvider:
    """``CapProvider`` for ``StarfishClient``: signs requests with a device cap
    self-minted from the wallet-derived root identity.

    The raw bootstrap signature is private-key-equivalent — it is consumed once
    in :func:`derive_root_identity` and never stored here; only the derived
    identity material is kept in memory.
    """

    def __init__(
        self, private_key: str, challenge: str = constants.SYNC_BOOTSTRAP_CHALLENGE
    ) -> None:
        self._root = derive_root_identity(private_key, challenge)

    @property
    def user_id(self) -> str:
        return self._root.user_id

    async def get_cap(self) -> dict[str, Any]:
        # Mint a fresh, full-scope device cap on each call so a long-running bot
        # never presents an expired cap (mint_device_cap sets a TTL); minting is
        # a single Ed25519 signature.
        cap = starfish_identities.mint_device_cap(
            self._root.keys.ed_priv,
            self._root.keys.ed_pub,
            {"edPubHex": self._root.keys.ed_pub, "kemPubHex": self._root.keys.kem_pub},
            starfish_identities.scopes.root_all(),
        )
        return {"cap": cap, "dev_ed_priv_hex": self._root.keys.ed_priv}
