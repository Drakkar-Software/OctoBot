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
from trading_backend.exchanges import exchange
from trading_backend.exchanges.exchange import (
    Exchange
)

from trading_backend.exchanges import binance
from trading_backend.exchanges.binance import (
    Binance
)

from trading_backend.exchanges import binanceus
from trading_backend.exchanges.binanceus import (
    BinanceUS
)

from trading_backend.exchanges import coinbase
from trading_backend.exchanges.coinbase import (
    Coinbase
)

from trading_backend.exchanges import okx
from trading_backend.exchanges.okx import (
    OKX
)

from trading_backend.exchanges import bybit
from trading_backend.exchanges.bybit import (
    Bybit
)

from trading_backend.exchanges import cryptocom
from trading_backend.exchanges.cryptocom import (
    CryptoCom
)

from trading_backend.exchanges import ascendex
from trading_backend.exchanges.ascendex import (
    Ascendex
)

from trading_backend.exchanges import gateio
from trading_backend.exchanges.gateio import (
    GateIO
)

from trading_backend.exchanges import htx
from trading_backend.exchanges.htx import (
    HTX
)

from trading_backend.exchanges import huobi
from trading_backend.exchanges.huobi import (
    Huobi
)

from trading_backend.exchanges import hollaex
from trading_backend.exchanges.hollaex import (
    HollaEx
)

from trading_backend.exchanges import bitget
from trading_backend.exchanges.bitget import (
    Bitget
)

from trading_backend.exchanges import phemex
from trading_backend.exchanges.phemex import (
    Phemex
)

from trading_backend.exchanges import kucoin
from trading_backend.exchanges.kucoin import (
    Kucoin
)

from trading_backend.exchanges import kucoinfutures
from trading_backend.exchanges.kucoinfutures import (
    KucoinFutures
)

from trading_backend.exchanges import mexc
from trading_backend.exchanges.mexc import (
    MEXC
)

from trading_backend.exchanges import bingx
from trading_backend.exchanges.bingx import (
    Bingx
)

from trading_backend.exchanges import coinex
from trading_backend.exchanges.coinex import (
    Coinex
)

from trading_backend.exchanges import bitmart
from trading_backend.exchanges.bitmart import (
    Bitmart
)

from trading_backend.exchanges import lbank
from trading_backend.exchanges.lbank import (
    LBank
)

__all__ = [
    "Exchange",
    "Binance",
    "Bybit",
    "CryptoCom",
    "OKX",
    "Ascendex",
    "GateIO",
    "HTX",
    "Huobi",
    "Bitget",
    "Phemex",
    "Kucoin",
    "KucoinFutures",
    "MEXC",
    "Bingx",
    "Coinex",
    "Bitmart",
    "LBank",
]
