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

import tempfile
import typing

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasicCredentials

try:
    import octobot.community.errors_upload.error_sharing as error_sharing
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser, security_basic
except ImportError:
    from api.deps import CurrentUser, security_basic

router = APIRouter(tags=["logs"])


@router.post("/share")
async def share_logs(
    current_user: CurrentUser,
    credentials: typing.Annotated[typing.Optional[HTTPBasicCredentials], Depends(security_basic)],
) -> typing.Any:
    try:
        with tempfile.NamedTemporaryFile(suffix="", delete=False) as tmp:
            export_path = tmp.name
        passphrase = credentials.password if credentials else None
        result = await error_sharing.share_logs(export_path, passphrase)
        if result is None:
            return {"success": False, "error": "Not connected to octobot.cloud"}
        return {
            "success": True,
            "errorId": result.get("errorId"),
            "errorSecret": result.get("errorSecret"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
