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

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

try:
    import tentacles.Services.Interfaces.node_api_interface.core.exchanges as exchange_core
except ImportError:
    import core.exchanges as exchange_core


router = APIRouter(prefix="/exchanges", tags=["exchanges"])


@router.get("/traded-pairs")
async def get_traded_pairs(
    exchange_config: typing.Annotated[exchange_core.ExchangeConfig, Query()],
) -> JSONResponse:
    pairs_and_tf_by_exchange = await exchange_core.get_traded_pairs_and_timeframes_by_exchange(exchange_config)
    return JSONResponse(content={
        exchange: pairs_and_tf[exchange_core.ExchangeInfo.PAIRS.value]
        for exchange, pairs_and_tf in pairs_and_tf_by_exchange.items()
    })


@router.get("/traded-pairs-and-timeframes")
async def get_traded_pairs_and_timeframes(
    exchange_config: typing.Annotated[exchange_core.ExchangeConfig, Query()],
) -> JSONResponse:
    return JSONResponse(
        content=await exchange_core.get_traded_pairs_and_timeframes_by_exchange(exchange_config)
    )
