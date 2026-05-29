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

import octobot_commons.json_util as json_util
import octobot_protocol.models as protocol_models
import octobot_trading.errors as trading_errors
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

try:
    import tentacles.Services.Interfaces.node_api_interface.core.exchanges as exchange_core
except ImportError:
    import core.exchanges as exchange_core


router = APIRouter(prefix="/exchanges", tags=["exchanges"])


def _exchange_config_from_query(
    exchange_config_id: typing.Annotated[str, Query(alias="id")],
    name: typing.Annotated[str, Query()],
    exchange: typing.Annotated[str, Query()],
    sandboxed: typing.Annotated[bool, Query()] = False,
    url: typing.Annotated[str | None, Query()] = None,
) -> protocol_models.ExchangeConfig:
    return protocol_models.ExchangeConfig(
        id=exchange_config_id,
        name=name,
        exchange=exchange,
        sandboxed=sandboxed,
        url=url,
    )


@router.get("/traded-pairs")
async def get_traded_pairs(
    exchange_config: typing.Annotated[protocol_models.ExchangeConfig, Depends(_exchange_config_from_query)],
    trading_type: typing.Annotated[protocol_models.TradingType, Query()] = protocol_models.TradingType.SPOT,
) -> JSONResponse:
    pairs_and_tf_by_exchange = await exchange_core.get_traded_pairs_and_timeframes_by_exchange(
        exchange_config,
        trading_type=trading_type,
    )
    return JSONResponse(content={
        exchange: pairs_and_tf[exchange_core.ExchangeInfo.PAIRS.value]
        for exchange, pairs_and_tf in pairs_and_tf_by_exchange.items()
    })


@router.get("/traded-pairs-and-timeframes")
async def get_traded_pairs_and_timeframes(
    exchange_config: typing.Annotated[protocol_models.ExchangeConfig, Depends(_exchange_config_from_query)],
    trading_type: typing.Annotated[protocol_models.TradingType, Query()] = protocol_models.TradingType.SPOT,
) -> JSONResponse:
    return JSONResponse(
        content=await exchange_core.get_traded_pairs_and_timeframes_by_exchange(
            exchange_config,
            trading_type=trading_type,
        )
    )


@router.get("/dex_pairs")
async def get_dex_pairs(
    exchange_config: typing.Annotated[protocol_models.ExchangeConfig, Depends(_exchange_config_from_query)],
    symbols: typing.Annotated[list[str] | None, Query()] = None,
    trading_type: typing.Annotated[protocol_models.TradingType, Query()] = protocol_models.TradingType.SPOT,
) -> JSONResponse:
    if not symbols:
        return JSONResponse(
            status_code=400,
            content={"error": "symbols query parameter is required"},
        )
    try:
        content = await exchange_core.get_dex_pairs_for_symbols(
            exchange_config,
            symbols,
            trading_type=trading_type,
        )
    except trading_errors.NotSupported as err:
        return JSONResponse(status_code=501, content={"error": str(err)})
    return JSONResponse(content=json_util.sanitize(content))
