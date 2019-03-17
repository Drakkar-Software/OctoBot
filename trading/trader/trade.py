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

from dataclasses import dataclass, field
from typing import Dict, Union, Any

from config import OrderStatus, TradeOrderSide
from trading.exchanges.exchange_dispatcher import ExchangeDispatcher
from trading.trader.order import TraderOrderType


@dataclass
class Trade:
    """
    Dataclass to store trade informations
    """

    canceled_time: int = field(init=False, repr=False)
    currency: str = field(init=False, repr=False)
    creation_time: int = field(init=False, repr=False)
    exchange: ExchangeDispatcher
    fee: Dict[str, Union[str, float]] = field(init=False, repr=False)
    filled_time: int = field(init=False, repr=False)
    final_status: OrderStatus = field(init=False, repr=False)
    market: str = field(init=False, repr=False)
    order: Any
    order_id: str = field(init=False, repr=False)
    order_type: TraderOrderType = field(init=False, repr=False)
    price: float = field(init=False, repr=False)
    cost: float = field(init=False, repr=False)
    quantity: float = field(init=False, repr=False)
    side: TradeOrderSide = field(init=False, repr=False)
    simulated: bool = field(init=False, repr=False)
    symbol: str = field(init=False, repr=False)

    def __post_init__(self):
        self.currency, self.market = self.order.get_currency_and_market()
        self.quantity = self.order.get_filled_quantity()
        self.price = self.order.get_filled_price()
        self.cost = self.order.get_total_cost()
        self.order_type = self.order.get_order_type()
        self.final_status = self.order.get_status()
        self.fee = self.order.fee
        self.order_id = self.order.get_id()
        self.side = self.order.get_side()
        self.creation_time = self.order.get_creation_time()
        self.canceled_time = self.order.canceled_time
        self.filled_time = self.order.executed_time
        self.symbol = self.order.get_order_symbol()
        self.simulated = self.order.trader.simulate
