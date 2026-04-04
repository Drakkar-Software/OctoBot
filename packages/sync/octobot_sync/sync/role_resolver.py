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

import json
import re
import time
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

from fastapi import Request
from starfish_server.router.route_builder import AuthResult
from starfish_server.storage.base import AbstractObjectStore

import octobot_sync.auth as auth
import octobot_sync.constants as constants

VerifySignatureFn = Callable[[str, str, str], Awaitable[bool]]


def _make_ttl_cache(ttl_s: float, maxsize: int = 4096):
    _cache: dict[str, tuple[float, str | None]] = {}

    def _evict_expired(now: float) -> None:
        expired = [k for k, (ts, _) in _cache.items() if (now - ts) >= ttl_s]
        for k in expired:
            del _cache[k]

    async def get_or_fetch(key: str, fetch) -> str | None:
        now = time.monotonic()
        entry = _cache.get(key)
        if entry and (now - entry[0]) < ttl_s:
            return entry[1]
        value = await fetch(key)
        # Only cache non-None values to avoid delaying access for newly created docs
        if value is not None:
            if len(_cache) >= maxsize:
                _evict_expired(now)
            if len(_cache) >= maxsize:
                oldest_key = min(_cache, key=lambda k: _cache[k][0])
                del _cache[oldest_key]
            _cache[key] = (now, value)
        else:
            _cache.pop(key, None)
        return value

    return get_or_fetch


def create_role_resolver(
    verify_signature: VerifySignatureFn,
    nonce: auth.NonceStore,
    platform_pubkey: str,
    supported_chains: set[str],
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

        if chain_id not in supported_chains:
            raise ValueError("Unknown chain")

        body = await request.body()
        body_text = body.decode("utf-8") if body else ""
        body_hash = auth.hash_body(body_text)
        path = urlparse(str(request.url)).path
        canonical = auth.build_canonical(request.method, path, timestamp, nonce_header, body_hash)

        valid = await verify_signature(canonical, signature, pubkey)
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


def create_role_enricher(store: AbstractObjectStore, cache_ttl_s: float = 30.0):
    cached_read = _make_ttl_cache(cache_ttl_s)

    async def role_enricher(auth_result: AuthResult, params: dict[str, str]) -> list[str]:
        product_id = params.get("productId")
        if not product_id:
            return []

        identity = auth_result.identity

        # Check members collection
        members_key = f"products/{product_id}/members"
        members_raw = await cached_read(members_key, store.get_string)
        if members_raw:
            try:
                members_doc = json.loads(members_raw)
            except (json.JSONDecodeError, TypeError):
                members_doc = {}

            owner = members_doc.get("owner", "")
            member_list = members_doc.get("members", [])

            if _identity_matches(identity, owner):
                return ["owner", "member"]
            if any(_identity_matches(identity, m) for m in member_list):
                return ["member"]

        # Entitlements are stored with lowercased identity keys.
        # Admin tooling that writes entitlements MUST also normalize to lowercase.
        entitlements_key = f"users/{identity.lower()}/entitlements"
        entitlements_raw = await cached_read(entitlements_key, store.get_string)
        if entitlements_raw:
            try:
                entitlements_doc = json.loads(entitlements_raw)
            except (json.JSONDecodeError, TypeError):
                entitlements_doc = {}

            if product_id in entitlements_doc.get("products", []):
                return ["member"]

        return []

    return role_enricher


def _identity_matches(a: str, b: str) -> bool:
    return a.lower() == b.lower()


def create_signature_verifier(verify_signature: VerifySignatureFn):
    async def signature_verifier(data: str, signature: str, pubkey: str) -> bool:
        return await verify_signature(data, signature, pubkey)

    return signature_verifier
