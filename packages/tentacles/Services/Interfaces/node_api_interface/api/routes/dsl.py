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

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import octobot_node.protocol.dsl as dsl_protocol
import octobot_protocol.models as protocol_models

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser
except ImportError:
    from api.deps import CurrentUser  # type: ignore[no-redef]

router = APIRouter(tags=["dsl"])


@router.get("/keywords", response_model=protocol_models.DslKeywordsState)
def get_dsl_keywords(current_user: CurrentUser) -> JSONResponse:
    """Return the versioned DSL keywords state for this node."""
    dsl_keywords_state = dsl_protocol.get_dsl_keywords_state()
    return JSONResponse(content=json.loads(dsl_keywords_state.to_json()))
