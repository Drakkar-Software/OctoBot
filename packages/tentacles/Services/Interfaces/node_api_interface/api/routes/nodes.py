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

from fastapi import APIRouter

import octobot_node.models
import octobot_node.scheduler.api

router = APIRouter(tags=["nodes"])

@router.get("/me", response_model=octobot_node.models.Node)
def get_current_node() -> typing.Any:
    status = octobot_node.scheduler.api.get_node_status()
    return octobot_node.models.Node(**status)
