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

from dataclasses import dataclass, field, fields
from typing import Dict, Union, Any

from config import OrderStatus, TradeOrderSide, TraderOrderType
from trading.exchanges.exchange_dispatcher import ExchangeDispatcher


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
    from_previous_execution: bool = field(init=True, repr=False, default=False)
    order_id: str = field(init=False, repr=False)
    order_type: TraderOrderType = field(init=False, repr=False)
    price: float = field(init=False, repr=False)
    cost: float = field(init=False, repr=False)
    quantity: float = field(init=False, repr=False)
    side: TradeOrderSide = field(init=False, repr=False)
    simulated: bool = field(init=False, repr=False)
    symbol: str = field(init=False, repr=False)

    def __post_init__(self):
        if not self.from_previous_execution:
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

    def as_dict(self):
        trade_dict = {}
        for attribute, value in self.__dict__.items():
            saved_value = value
            if attribute == "exchange":
                saved_value = value.get_name()
            elif attribute in ["final_status", "side", "order_type"]:
                saved_value = value.name
            elif attribute == "order":
                saved_value = None

            trade_dict[attribute] = saved_value
        return trade_dict

    @staticmethod
    def from_dict(exchange, trade_dict):
        if not all(field in trade_dict for field in [n.name for n in fields(Trade)]):
            raise RuntimeError(f"Incomplete trade data, impossible to parse trade: {trade_dict}")
        new_trade = Trade(exchange, None, from_previous_execution=True)
        for attribute, value in trade_dict.items():
            saved_value = value
            if attribute == "exchange":
                saved_value = exchange
            elif attribute == "final_status":
                saved_value = OrderStatus[value]
            elif attribute == "side":
                saved_value = TradeOrderSide[value]
            elif attribute == "order_type":
                saved_value = TraderOrderType[value]
            elif attribute == "order":
                saved_value = None
            setattr(new_trade, attribute, saved_value)
        new_trade.from_previous_execution = True
        return new_trade
