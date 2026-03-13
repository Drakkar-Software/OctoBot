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

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import octobot_sync.constants as constants
import octobot_sync.sync as sync

router = APIRouter()

UNSAFE_KEYS = frozenset({"__proto__", "constructor", "prototype"})


async def _get_doc(store, prefix: str, doc_id: str) -> dict | None:
    raw = await store.get_string(f"{prefix}/{doc_id}.json")
    if not raw:
        return None
    return json.loads(raw)


async def _put_doc(store, prefix: str, doc_id: str, doc: dict) -> None:
    await store.put(f"{prefix}/{doc_id}.json", json.dumps(doc), content_type="application/json")


@router.put("/product/{product_pubkey}/{version}/meta")
async def put_product_meta(product_pubkey: str, version: str, request: Request):
    """Upload product metadata (multipart form: profile fields + logo + version_description)."""
    object_store = request.app.state.object_store
    registry = request.app.state.registry

    # Parse version
    raw_version = version.lstrip("v") or str(constants.DEFAULT_VERSION)
    try:
        ver = int(raw_version)
    except ValueError:
        return JSONResponse({"error": "Invalid version"}, status_code=400)

    form_data = await request.form()

    # Profile fields — whitelist only
    profile_fields: dict = {}
    for field in ("name", "description", "website", "twitter"):
        value = form_data.get(field)
        if value and str(value):
            profile_fields[field] = value

    tags = form_data.get("tags")
    if tags and str(tags):
        try:
            profile_fields["tags"] = json.loads(tags)
        except json.JSONDecodeError:
            return JSONResponse({"error": "Invalid tags JSON"}, status_code=400)

    # Merge with existing profile — sanitize both sides
    if profile_fields:
        raw = await _get_doc(object_store, f"products/{product_pubkey}", "profile") or {}
        existing = {k: v for k, v in raw.items() if k not in UNSAFE_KEYS}
        await _put_doc(
            object_store, f"products/{product_pubkey}", "profile", {**existing, **profile_fields}
        )

    # Logo upload
    logo = form_data.get("logo")
    if logo and hasattr(logo, "read"):
        logo_data = await logo.read()
        await object_store.put(
            f"products/{product_pubkey}/logo.png",
            logo_data.decode("utf-8") if bytes(logo_data) else logo_data,
            content_type="image/png",
        )

    # Version description
    version_desc = form_data.get("version_description")
    if version_desc and str(version_desc):
        await _put_doc(
            object_store,
            f"products/{product_pubkey}/v{ver}",
            "document",
            {"description": version_desc},
        )

    return {"ok": True}


@router.get("/product/{product_pubkey}/info")
async def get_product_info(product_pubkey: str, request: Request):
    object_store = request.app.state.object_store
    registry = request.app.state.registry

    product = await sync.find_item(registry, product_pubkey)
    profile = await _get_doc(object_store, f"products/{product_pubkey}", "profile")

    return {
        "product": {"id": product.id, "owner": product.owner} if product else None,
        "profile": profile or {},
    }
