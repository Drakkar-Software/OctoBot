#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import logging
import typing

import octobot_trading.errors
import octobot_commons.authentication as authentication
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.json_util as json_util
import octobot_flow.entities.community.user_authentication as community_user_authentication

import tentacles.Trading.Mode.simple_market_making_trading_mode.api.models as models
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.core as core
import tentacles.Services.Interfaces.node_api_interface.core.exchanges as exchanges_core


@json_util.sanitized
async def compute_market_making_volume(
    exchange_configs: list[exchanges_core.ExchangeConfig], market_making_config: dict,
    auth: typing.Optional[community_user_authentication.UserAuthentication]
) -> dict:
    logger = logging.getLogger("compute_market_making_volume")
    logger.info(f"Computing market making volume for {exchange_configs}")
    profile_data = await core.get_market_making_profile_data(exchange_configs, market_making_config, user_auth=auth)
    market_making_volume = await core.get_market_making_volume(profile_data, user_auth=auth)
    logger.info(f"Market making volume for {exchange_configs}: {market_making_volume}")
    return market_making_volume


@json_util.sanitized
async def get_price_and_predicted_order_book(
    exchange_configs: list[exchanges_core.ExchangeConfig], market_making_config: dict,
    auth: typing.Optional[community_user_authentication.UserAuthentication]
) -> dict:
    logger = logging.getLogger("get_price_and_predicted_order_book")
    logger.info(f"Computing predicted order book for {exchange_configs=} {market_making_config=}")
    profile_data = await core.get_market_making_profile_data(exchange_configs, market_making_config, user_auth=auth)
    price_and_predicted_order_book = await core.get_price_and_predicted_order_book(profile_data, user_auth=auth)
    logger.info(f"Predicted order book for {exchange_configs}: {price_and_predicted_order_book}")
    return price_and_predicted_order_book


async def update_liquidity_score(
    exchange_configs: list[exchanges_core.ExchangeConfig],
    policy: models.OrderBookFetchPolicy,
    symbols: typing.Optional[list[str]],
    auth: typing.Optional[community_user_authentication.UserAuthentication]
) -> str:
    logger = logging.getLogger("update_liquidity_score")
    profile_data = await core.get_market_making_profile_data(exchange_configs, None, user_auth=auth)
    # todo update if raising when not available is required
    custom_auth = None
    fingerprint = f"update_liquidity_score{exchange_configs}{policy.value}{symbols}"
    if asyncio_tools.run_background_fingerprint_async_executor(
        fingerprint,
        core.update_liquidity_scores(
            profile_data, policy, symbols=symbols, custom_auth=custom_auth, user_auth=auth
        )
    ):
        logger.info(f"Updating {symbols} liquidity score for {exchange_configs}")
        return "update scheduled"
    else:
        logger.info(f"Liquidity scores update for this input is already processing")
        return "update already processing"


async def dispatch_market_making_request(
    data: typing.Optional[dict],
) -> tuple[typing.Any, int]:
    request_type = data.get("type")
    logger = logging.getLogger("market_making_dispatch")
    logger.info(f"Starting for {request_type}...")
    json_resp: typing.Any = f"unknown request_type: {request_type}"
    status_code = 400
    parsed_auth = community_user_authentication.UserAuthentication.from_dict(
        data.get("auth") if data else None
    )
    try:
        exchanges: list[exchanges_core.ExchangeConfig] = []
        if _exchanges := data.get("exchanges"):
            exchanges = [
                exchanges_core.ExchangeConfig.model_validate(exchange)
                for exchange in _exchanges
            ]
        if request_type == "market_making_volume":
            json_resp = await compute_market_making_volume(
                exchanges, data.get("config"), parsed_auth
            )
            status_code = 200
        if request_type == "predicted_order_book":
            json_resp = await get_price_and_predicted_order_book(
                exchanges, data.get("config"), parsed_auth
            )
            status_code = 200
        if request_type == "update_liquidity_score":
            json_resp = await update_liquidity_score(
                exchanges,
                models.OrderBookFetchPolicy(data.get("policy")),
                data.get("symbols"),
                parsed_auth
            )
            status_code = 200
    except ValueError as err:
        json_resp = {"error": str(err)}
        logger.exception(err)
        status_code = 404
    except authentication.AuthenticationError as err:
        json_resp = {"error": str(err)}
        logger.exception(err)
        status_code = 401
    except octobot_trading.errors.AuthenticationError as err:
        json_resp = {"error": str(err)}
        logger.warning(f"Invalid exchange credentials: {err}")  # don't alert on this error, it can happen
        status_code = 401
    return json_resp, status_code
