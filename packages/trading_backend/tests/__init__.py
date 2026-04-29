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
import mock
import os
import pytest
import pytest_asyncio
import ccxt.async_support


@pytest.fixture
def binance_exchange():
    return ExchangeWrapper(ccxt.async_support.binanceus())  # binanceus not to fail on CI


@pytest.fixture
def binanceus_exchange():
    return ExchangeWrapper(ccxt.async_support.binanceus())  # binanceus not to fail on CI


@pytest.fixture
def coinbase_exchange():
    return ExchangeWrapper(ccxt.async_support.coinbase())


@pytest.fixture
def okx_exchange():
    return ExchangeWrapper(ccxt.async_support.okx())


@pytest.fixture
def huobi_exchange():
    return ExchangeWrapper(ccxt.async_support.huobi())


@pytest.fixture
def htx_exchange():
    return ExchangeWrapper(ccxt.async_support.htx())


@pytest.fixture
def ascendex_exchange():
    return ExchangeWrapper(ccxt.async_support.ascendex())


@pytest.fixture
def bybit_exchange():
    return ExchangeWrapper(ccxt.async_support.bybit())


@pytest.fixture
def cryptocom_exchange():
    return ExchangeWrapper(ccxt.async_support.cryptocom())


@pytest.fixture
def gateio_exchange():
    return ExchangeWrapper(ccxt.async_support.gateio())


@pytest.fixture
def hollaex_exchange():
    return ExchangeWrapper(ccxt.async_support.hollaex())


@pytest.fixture
def bitget_exchange():
    return ExchangeWrapper(ccxt.async_support.bitget())


@pytest.fixture
def phemex_exchange():
    return ExchangeWrapper(ccxt.async_support.phemex())


@pytest.fixture
def kucoin_exchange():
    return ExchangeWrapper(ccxt.async_support.kucoin())


@pytest.fixture
def kucoinfutures_exchange():
    return ExchangeWrapper(ccxt.async_support.kucoinfutures())


@pytest.fixture
def mexc_exchange():
    return ExchangeWrapper(ccxt.async_support.mexc())


@pytest.fixture
def bingx_exchange():
    return ExchangeWrapper(ccxt.async_support.bingx())


@pytest.fixture
def coinex_exchange():
    return ExchangeWrapper(ccxt.async_support.coinex())


@pytest.fixture
def bitmart_exchange():
    return ExchangeWrapper(ccxt.async_support.bitmart())


@pytest.fixture
def default_exchange():
    """
    :return: An exchange for which there is no exchange implementation in trading_backend.exchanges
    """
    return ExchangeWrapper(ccxt.async_support.okx())


class ExchangeConnector:
    def __init__(self, ccxt_exchange):
        self.client = ccxt_exchange

    def add_headers(self, headers_dict):
        for header_key, header_value in headers_dict.items():
            self.client.headers[header_key] = header_value

    def raise_or_prefix_proxy_error_if_relevant(self, cause_error, raised_error):
        raise cause_error from (raised_error or cause_error)


class ExchangeManager:
    def __init__(self, is_margin=False, is_future=False, is_sandboxed=False):
        self.is_future = is_future
        self.is_margin = is_margin
        self.is_sandboxed = is_sandboxed


class ExchangeWrapper:
    def __init__(self, ccxt_exchange, is_margin=False, is_future=False):
        self.connector = ExchangeConnector(ccxt_exchange)
        self.exchange_manager = ExchangeManager(is_margin=is_margin, is_future=is_future)
        self.is_api_permission_error = mock.Mock(return_value=False)
        self.is_authentication_error = mock.Mock(return_value=False)
        self.is_ip_whitelist_error = mock.Mock(return_value=False)


def _is_on_github_ci():
    # Always set to true when GitHub Actions is running the workflow.
    # You can use this variable to differentiate when tests are being run locally or by GitHub Actions.
    # from https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables
    return bool(os.getenv("GITHUB_ACTIONS"))


@pytest_asyncio.fixture
async def skipped_on_github_CI():
    if _is_on_github_ci():
        pytest.skip(reason="test skipped on github CI")
