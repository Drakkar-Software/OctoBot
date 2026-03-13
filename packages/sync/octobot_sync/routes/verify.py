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

from fastapi import APIRouter, Request, Response

import octobot_sync.auth as auth
import octobot_sync.chain as chain
import octobot_sync.constants as constants

router = APIRouter()


def _strip_bucket_prefix(uri: str) -> str:
    without_leading_slash = uri.lstrip("/")
    slash_idx = without_leading_slash.find("/")
    return "" if slash_idx == -1 else without_leading_slash[slash_idx + 1 :]


def _is_path_authorized(
    s3_path: str, method: str, pubkey: str, platform_pubkey: str
) -> bool:
    is_read = method in ("GET", "HEAD")

    if s3_path.startswith("products/"):
        return is_read or pubkey == platform_pubkey

    if s3_path.startswith("public/"):
        return is_read or pubkey == platform_pubkey

    if s3_path.startswith("users/"):
        parts = s3_path.split("/")
        path_pubkey = parts[1] if len(parts) > 1 else ""
        return pubkey == path_pubkey or pubkey == platform_pubkey

    if s3_path.startswith("platform/"):
        return pubkey == platform_pubkey

    return False


@router.get("/verify")
async def verify(request: Request) -> Response:
    registry: chain.ChainRegistry = request.app.state.registry
    nonce_store: auth.NonceStore = request.app.state.nonce
    platform_pubkey: str = request.app.state.platform_pubkey

    pubkey = request.headers.get(constants.HEADER_PUBKEY)
    signature = request.headers.get(constants.HEADER_SIGNATURE)
    timestamp = request.headers.get(constants.HEADER_TIMESTAMP)
    nonce_header = request.headers.get(constants.HEADER_NONCE)
    chain_id = request.headers.get(constants.HEADER_CHAIN)

    original_method = request.headers.get(constants.HEADER_ORIGINAL_METHOD)
    original_uri = request.headers.get(constants.HEADER_ORIGINAL_URI)

    # Public reads on products/ and public/ don't require auth
    if original_uri and original_method == "GET":
        path = _strip_bucket_prefix(original_uri)
        if path.startswith("products/") or path.startswith("public/"):
            return Response(status_code=200)

    if not all([pubkey, signature, timestamp, nonce_header, chain_id]):
        return Response(status_code=401)

    if len(pubkey) > constants.MAX_PUBKEY_LENGTH:
        return Response(status_code=401)
    if len(signature) > constants.MAX_SIGNATURE_LENGTH:
        return Response(status_code=401)
    if len(nonce_header) > constants.MAX_NONCE_LENGTH:
        return Response(status_code=401)

    if not re.match(r"^\d+$", timestamp):
        return Response(status_code=401)
    ts = int(timestamp)
    if abs(ts - int(time.time() * 1000)) > constants.TIMESTAMP_WINDOW_MS:
        return Response(status_code=401)

    try:
        chain = registry.get(chain_id)
    except Exception:
        return Response(status_code=401)

    body_hash = auth.hash_body("")
    method = original_method or "GET"
    path = original_uri or "/"
    canonical = auth.build_canonical(method, path, timestamp, nonce_header, body_hash)

    valid = await chain.verify_signature(canonical, signature, pubkey)
    if not valid:
        return Response(status_code=401)

    fresh = await nonce_store.nonce_insert(nonce_header, pubkey)
    if not fresh:
        return Response(status_code=401)

    # Path-based authorization
    if original_uri:
        s3_path = _strip_bucket_prefix(original_uri)
        if not _is_path_authorized(s3_path, method, pubkey, platform_pubkey):
            return Response(status_code=401)

    return Response(status_code=200)
