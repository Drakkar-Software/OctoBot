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

from fastapi import APIRouter

from tentacles.Services.Interfaces.node_api_interface.api.routes import login, nodes, users, tasks


def build_api_router() -> APIRouter:
    api_router = APIRouter()
    api_router.include_router(login.router)
    api_router.include_router(users.router, prefix="/users")
    api_router.include_router(tasks.router, prefix="/tasks")
    api_router.include_router(nodes.router, prefix="/nodes")
    return api_router
