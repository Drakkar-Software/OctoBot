#  Drakkar-Software trading-backend
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
import json

import mock

import trading_backend.exchanges as exchanges


async def create_order_mocked_test_args(
    exchange: exchanges.Exchange,
    exchange_private_post_order_method_name: str,
    exchange_request_referral_key: str,
    should_contains: bool = True,
    result_is_list: bool = False,
    symbol: str = "BTC/USDT",
    amount: int = 1,
    price: int = 1,
    post_order_mock_return_value: dict = None
):
    with mock.patch.object(exchange._exchange.connector.client,
                           "check_required_credentials",
                           mock.Mock(return_value=False)), \
            mock.patch.object(exchange._exchange.connector.client,
                              exchange_private_post_order_method_name,
                              mock.AsyncMock(return_value=post_order_mock_return_value or {})) as post_order_mock:
        # without referral patch
        await exchange._exchange.connector.client.create_limit_buy_order(symbol, amount, price)
        result = post_order_mock.call_args[0][0].get(exchange_request_referral_key, "") \
            if not result_is_list else post_order_mock.call_args[0][0][0].get(exchange_request_referral_key, "")
        if should_contains:
            assert exchange._get_id() not in result
        else:
            assert exchange._get_id() != result

        # with referral patch
        await exchange._exchange.connector.client.create_limit_buy_order(symbol, amount, price,
                                                                         params=exchange.get_orders_parameters())
        result = post_order_mock.call_args[0][0].get(exchange_request_referral_key, "") \
            if not result_is_list else post_order_mock.call_args[0][0][0].get(exchange_request_referral_key, "")
        if should_contains:
            assert exchange._get_id() in result
        else:
            assert exchange._get_id() == result


def get_content(signed_result, in_body):
    if in_body:
        return json.loads(signed_result["body" if in_body else "headers"])
    return signed_result["headers"]


async def sign_test(
    exchange: exchanges.Exchange,
    api,
    broker_id_key: str,
    broker_sign_header_key: str = None,
    section: str = None,
    should_contains: bool = False,
    in_body: bool = False,
    url_path: str = "url/path"
):
    method = "POST"
    params = {}
    headers = None
    body = None
    api_key = "123"
    api_secret = "456"
    password = "789"
    ccxt_client = exchange._exchange.connector.client
    ccxt_client.apiKey = api_key
    ccxt_client.secret = api_secret
    ccxt_client.password = password

    # without referral patch
    if section:
        signed_result = ccxt_client.sign(
            url_path, section=section, method=method, params=params, headers=headers, body=body
        )
    else:
        signed_result = ccxt_client.sign(
            url_path, api=api, method=method, params=params, headers=headers, body=body
        )
    assert signed_result
    content = get_content(signed_result, in_body)
    if should_contains:
        assert exchange._get_id() not in content[broker_id_key]
    else:
        assert content[broker_id_key] != exchange._get_id()
    if broker_sign_header_key:
        assert content[broker_sign_header_key]

    # with referral patch
    exchange.get_orders_parameters()
    if section:
        signed_result = ccxt_client.sign(
            url_path, section=section, method=method, params=params, headers=headers, body=body
        )
    else:
        signed_result = ccxt_client.sign(
            url_path, api=api, method=method, params=params, headers=headers, body=body
        )
    assert signed_result
    content = get_content(signed_result, in_body)
    if should_contains:
        assert exchange._get_id() in content[broker_id_key]
    else:
        assert content[broker_id_key] == exchange._get_id()
    if broker_sign_header_key:
        assert content[broker_sign_header_key]


async def exchange_requests_contains_headers_test(exchange: exchanges.Exchange,
                                                  exchange_header_referral_key: str,
                                                  exchange_header_referral_value: str):
    request_headers = exchange._exchange.connector.client.prepare_request_headers()
    assert request_headers[exchange_header_referral_key] == exchange_header_referral_value
