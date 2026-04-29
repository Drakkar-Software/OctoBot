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

from .polymarket_sync import polymarket as CCXTPolymarketExchange
from .polymarket_async import polymarket as CCXTAsyncPolymarketExchange
from .polymarket_pro import polymarket as CCXTProPolymarketExchange

import ccxt
ccxt.__all__.append("polymarket")
ccxt.exchanges.append("polymarket")
ccxt.polymarket = CCXTPolymarketExchange

import ccxt.async_support
ccxt.async_support.__all__.append("polymarket")
ccxt.async_support.exchanges.append("polymarket")
ccxt.async_support.polymarket = CCXTAsyncPolymarketExchange

import ccxt.pro
ccxt.pro.exchanges.append("polymarket")
ccxt.pro.polymarket = CCXTProPolymarketExchange
