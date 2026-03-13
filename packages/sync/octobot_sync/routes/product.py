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

import octobot_sync.sync as sync

router = APIRouter()


async def _get_doc(store, prefix: str, doc_id: str) -> dict | None:
    raw = await store.get_string(f"{prefix}/{doc_id}.json")
    if not raw:
        return None
    return json.loads(raw)


@router.get("/product/{product_pubkey}")
async def get_product(product_pubkey: str, request: Request):
    registry = request.app.state.registry
    object_store = request.app.state.object_store

    product = await sync.find_item(registry, product_pubkey)
    if product is None:
        return JSONResponse({"error": "Product not found"}, status_code=404)

    profile = await _get_doc(object_store, f"products/{product_pubkey}", "profile")

    return {
        "product": {"id": product.id, "owner": product.owner},
        "profile": profile or {},
    }
