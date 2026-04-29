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

import trading_backend.exchange_factory
import trading_backend.exchanges
from tests import binance_exchange, bybit_exchange, default_exchange, kucoin_exchange, kucoinfutures_exchange


def test_create_exchange_backend(
    binance_exchange, bybit_exchange, kucoin_exchange, kucoinfutures_exchange, default_exchange
):
    class ExchangeMock:
        def __init__(self, *args):
            pass

    class BinanceMock(ExchangeMock):
        pass

    class BybitMock(ExchangeMock):
        pass

    class KucoinMock(ExchangeMock):
        pass

    class KucoinFuturesMock(ExchangeMock):
        pass

    class OtherMock(ExchangeMock):
        pass

    exchanges_dict = {
        "binanceus": BinanceMock,
        "bybit": BybitMock,
        "kucoin": KucoinMock,
        "kucoinfutures": KucoinFuturesMock,
        "other": OtherMock,
    }
    with mock.patch.object(trading_backend.exchange_factory, "_get_exchanges",
                              mock.Mock(return_value=exchanges_dict)) as _get_exchanges_mock:
        assert isinstance(trading_backend.create_exchange_backend(binance_exchange), BinanceMock)
        _get_exchanges_mock.assert_called_once()
        _get_exchanges_mock.reset_mock()
        assert isinstance(trading_backend.create_exchange_backend(bybit_exchange), BybitMock)
        _get_exchanges_mock.assert_called_once()
        _get_exchanges_mock.reset_mock()
        assert isinstance(trading_backend.create_exchange_backend(kucoin_exchange), KucoinMock)
        _get_exchanges_mock.assert_called_once()
        _get_exchanges_mock.reset_mock()
        assert isinstance(trading_backend.create_exchange_backend(kucoinfutures_exchange), KucoinFuturesMock)
        _get_exchanges_mock.assert_called_once()
        _get_exchanges_mock.reset_mock()
        assert isinstance(trading_backend.create_exchange_backend(default_exchange), trading_backend.exchanges.Exchange)
        _get_exchanges_mock.assert_called_once()


def test_get_exchanges():
    exchanges_by_name = {
        trading_backend.exchanges.Exchange.get_name(): trading_backend.exchanges.Exchange
    }
    exchanges_by_name.update({
        exchange.get_name(): exchange
        for exchange in trading_backend.exchanges.Exchange.__subclasses__()
    })
    # add exchanges subclasses
    exchanges_by_name.update({
        exchange.get_name(): exchange
        for exchange_class in exchanges_by_name.values()
        for exchange in exchange_class.__subclasses__()
    })
    assert len(exchanges_by_name) == 21
    assert trading_backend.exchange_factory._get_exchanges() == exchanges_by_name
