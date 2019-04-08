#  Drakkar-Software OctoBot
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

from cryptofeed.bitfinex.bitfinex import Bitfinex
from cryptofeed.bitstamp.bitstamp import Bitstamp
from cryptofeed.coinbase.coinbase import Coinbase
from cryptofeed.exx.exx import EXX
from cryptofeed.hitbtc.hitbtc import HitBTC
from cryptofeed.huobi.huobi import Huobi

# from cryptofeed.poloniex.poloniex import Poloniex
# from cryptofeed.gemini.gemini import Gemini

cryptofeed_classes = {
    "Bitfinex": Bitfinex,
    "Bitfinex2": Bitfinex,
    "Hitbtc": HitBTC,
    "Coinbase": Coinbase,
    "Coinbasepro": Coinbase,
    "Exx": EXX,
    # "Poloniex": Poloniex, TODO Poloniex does not handle unsupported pairs
    "Bitstamp": Bitstamp,
    "Huobi": Huobi,  # Not supported by ccxt
    # "Gemini": Gemini TODO Gemini requires a websocket per trading pair
}
