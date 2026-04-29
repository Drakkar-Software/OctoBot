#  Drakkar-Software OctoBot-Trading
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
import ccxt
import mock
import pytest
import asyncio

import octobot_trading.exchanges as exchanges
import octobot_trading.constants as constants
import octobot_trading.errors as errors



# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_retried_failed_network_request():
  request_mock = mock.AsyncMock(return_value=1)
  @exchanges.connectors.util.retried_failed_network_request()
  async def _fetch_request(*args, **kwargs):
    return await request_mock(*args, **kwargs)

  with mock.patch.object(asyncio, "sleep") as sleep_mock:
    # no error
    assert await _fetch_request("arg1", kw1=1) == 1
    request_mock.assert_awaited_once_with("arg1", kw1=1)
    sleep_mock.assert_not_called()

    # non retriable errors
    for raised_error in [
      ccxt.ExchangeError("Exchange error"),
      KeyError("random key error"),
      ValueError("random value error"),
      ZeroDivisionError("random zero division error"),
    ]:
      request_mock = mock.AsyncMock(side_effect=raised_error)
      @exchanges.connectors.util.retried_failed_network_request()
      async def _fetch_request(*args, **kwargs):
        return await request_mock(*args, **kwargs)
      with pytest.raises(raised_error.__class__):
        await _fetch_request("arg1", kw1=1)
      assert request_mock.call_count == 1
      assert sleep_mock.call_count == 0
      sleep_mock.reset_mock()

    # retriable errors
    for raised_error in [
      ccxt.ExchangeNotAvailable("Exchange not available"), 
      ccxt.RequestTimeout("Request timeout"), 
      ccxt.InvalidNonce("Invalid nonce"),
      errors.RetriableFailedRequest("Retriable failed request"),
    ]:
      request_mock = mock.AsyncMock(side_effect=raised_error)
      @exchanges.connectors.util.retried_failed_network_request()
      async def _fetch_request(*args, **kwargs):
        return await request_mock(*args, **kwargs)
      with pytest.raises(raised_error.__class__):
        await _fetch_request("arg1", kw1=1)
      assert request_mock.call_count == constants.FAILED_NETWORK_REQUEST_RETRY_ATTEMPTS
      assert sleep_mock.call_count == constants.FAILED_NETWORK_REQUEST_RETRY_ATTEMPTS - 1
      assert sleep_mock.mock_calls[0].args == (constants.DEFAULT_FAILED_REQUEST_RETRY_TIME,)
      sleep_mock.reset_mock()

    # retriable exchange errors
    for raised_error in [
      ccxt.ExchangeError("Internal Server Error"),
      ccxt.BadRequest("Error: socket hang up"),
      ccxt.BadRequest("Error: read ECONNRESET"),
      ccxt.ExchangeError('mexc {"code":700022,"msg":"Internal Server Error"}'),
    ]:
      request_mock = mock.AsyncMock(side_effect=raised_error)
      @exchanges.connectors.util.retried_failed_network_request()
      async def _fetch_request(*args, **kwargs):
        return await request_mock(*args, **kwargs)
      with pytest.raises(raised_error.__class__):
        await _fetch_request("arg1", kw1=1)
      assert request_mock.call_count == constants.FAILED_NETWORK_REQUEST_RETRY_ATTEMPTS
      assert sleep_mock.call_count == constants.FAILED_NETWORK_REQUEST_RETRY_ATTEMPTS - 1
      assert sleep_mock.mock_calls[0].args == (constants.DEFAULT_FAILED_REQUEST_RETRY_TIME,)
      sleep_mock.reset_mock()

    # retriable proxy errors
    for raised_error in [
      errors.RetriableExchangeProxyError("Retriable exchange proxy error"),
    ]:
      request_mock = mock.AsyncMock(side_effect=raised_error)
      @exchanges.connectors.util.retried_failed_network_request()
      async def _fetch_request(*args, **kwargs):
        return await request_mock(*args, **kwargs)
      with pytest.raises(raised_error.__class__):
        await _fetch_request("arg1", kw1=1)
      assert request_mock.call_count == constants.FAILED_PROXY_NETWORK_REQUEST_RETRY_ATTEMPTS
      assert sleep_mock.call_count == constants.FAILED_PROXY_NETWORK_REQUEST_RETRY_ATTEMPTS - 1
      assert sleep_mock.mock_calls[0].args == (constants.DEFAULT_FAILED_REQUEST_RETRY_TIME,)
      sleep_mock.reset_mock()

    # custom params
    request_mock = mock.AsyncMock(side_effect=ccxt.ExchangeNotAvailable("Exchange not available"))
    @exchanges.connectors.util.retried_failed_network_request(
      attempts=3, retriable_proxy_errors_attempts=1, delay=0.1
    )
    async def _fetch_request(*args, **kwargs):
      return await request_mock(*args, **kwargs)
    with pytest.raises(ccxt.ExchangeNotAvailable):
      await _fetch_request("arg1", kw1=1)
    assert request_mock.call_count == 3
    assert sleep_mock.call_count == 2
    assert sleep_mock.mock_calls[0].args == (0.1,)
    sleep_mock.reset_mock()

    request_mock = mock.AsyncMock(side_effect=errors.RetriableExchangeProxyError("Retriable exchange proxy error"))
    @exchanges.connectors.util.retried_failed_network_request(
      attempts=4, retriable_proxy_errors_attempts=4, delay=0.2
    )
    async def _fetch_request(*args, **kwargs):
      return await request_mock(*args, **kwargs)
    with pytest.raises(errors.RetriableExchangeProxyError):
      await _fetch_request("arg1", kw1=1)
    assert request_mock.call_count == 4
    assert sleep_mock.call_count == 3
    assert sleep_mock.mock_calls[0].args == (0.2,)
    sleep_mock.reset_mock()
