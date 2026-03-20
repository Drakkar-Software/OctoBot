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

import re
import time
from contextvars import ContextVar
from urllib.parse import urlparse

from fastapi import Request
from starfish_server.router.route_builder import AuthResult

import octobot_sync.auth as auth
import octobot_sync.chain as chain
import octobot_sync.constants as constants

# Per-request chain context so the enricher can access the resolved chain
_request_chain: ContextVar[chain.AbstractChain | None] = ContextVar("_request_chain", default=None)


def create_role_resolver(
    registry: chain.ChainRegistry,
    nonce: auth.NonceStore,
    platform_pubkey: str,
):
    async def role_resolver(request: Request) -> AuthResult:
        pubkey = request.headers.get(constants.HEADER_PUBKEY)
        signature = request.headers.get(constants.HEADER_SIGNATURE)
        timestamp = request.headers.get(constants.HEADER_TIMESTAMP)
        nonce_header = request.headers.get(constants.HEADER_NONCE)
        chain_id = request.headers.get(constants.HEADER_CHAIN)

        if not all([pubkey, signature, timestamp, nonce_header, chain_id]):
            raise ValueError("Missing authentication headers")

        if len(pubkey) > constants.MAX_PUBKEY_LENGTH:
            raise ValueError("Invalid pubkey")
        if len(signature) > constants.MAX_SIGNATURE_LENGTH:
            raise ValueError("Invalid signature")
        if len(nonce_header) > constants.MAX_NONCE_LENGTH:
            raise ValueError("Invalid nonce")

        if not re.match(r"^\d+$", timestamp):
            raise ValueError("Invalid timestamp")
        ts = int(timestamp)
        if abs(ts - int(time.time() * 1000)) > constants.TIMESTAMP_WINDOW_MS:
            raise ValueError("Timestamp out of window")

        try:
            chain = registry.get(chain_id)
        except Exception:
            raise ValueError("Unknown chain")

        # Store chain for later use by enricher
        _request_chain.set(chain)

        body = await request.body()
        body_text = body.decode("utf-8") if body else ""
        body_hash = auth.hash_body(body_text)
        path = urlparse(str(request.url)).path
        canonical = auth.build_canonical(request.method, path, timestamp, nonce_header, body_hash)

        valid = await chain.verify_signature(canonical, signature, pubkey)
        if not valid:
            raise ValueError("Invalid signature")

        fresh = await nonce.nonce_insert(nonce_header, pubkey)
        if not fresh:
            raise ValueError("Replay")

        roles = ["user"]
        if pubkey == platform_pubkey:
            roles.append("admin")

        return AuthResult(identity=pubkey, roles=roles)

    return role_resolver


def create_role_enricher(registry: chain.ChainRegistry):
    async def role_enricher(auth: AuthResult, params: dict[str, str]) -> list[str]:
        product_id = params.get("productId")
        if not product_id:
            return []
        for c in registry.list():
            if await c.is_item_owner(product_id, auth.identity):
                return ["owner", "member"]
            if await c.has_access(product_id, auth.identity):
                return ["member"]
        return []

    return role_enricher


def create_signature_verifier(registry: chain.ChainRegistry):
    async def signature_verifier(data: str, signature: str, pubkey: str) -> bool:
        chain = _request_chain.get()
        if chain is not None:
            return await chain.verify_signature(data, signature, pubkey)
        for chain in registry.list():
            if await chain.verify_signature(data, signature, pubkey):
                return True
        return False

    return signature_verifier
