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
import trading_backend.exchanges as exchanges


def create_exchange_backend(exchange) -> exchanges.Exchange:
    # use ccxt exchange id to find exchanges (ex kucoinfutures: id: kucoinfutures, name: "Kucoin Futures")
    return _get_exchanges().get(exchange.connector.client.id.lower(), exchanges.Exchange)(exchange)


def is_sponsoring(exchange_name) -> bool:
    return _get_exchanges().get(exchange_name.lower(), exchanges.Exchange).is_sponsoring()


def _get_exchanges() -> dict:
    return {
        exchange.get_name(): exchange
        for exchange in _get_subclasses(exchanges.Exchange)
    }


def _get_subclasses(parent) -> list:
    children = [parent]
    for child in parent.__subclasses__():
        children += _get_subclasses(child)
    return children
