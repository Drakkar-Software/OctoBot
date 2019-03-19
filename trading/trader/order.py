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

import time
import math
from abc import *
from asyncio import Lock
from dataclasses import dataclass, field
from typing import List, Any, Dict, Union

from tools.logging.logging_util import get_logger

from tools.symbol_util import split_symbol
from config import TradeOrderSide, OrderStatus, TraderOrderType, SIMULATOR_LAST_PRICES_TO_CHECK, \
    ExchangeConstantsTickersColumns as eC, FeePropertyColumns, ExchangeConstantsMarketPropertyColumns
from trading.exchanges.exchange_dispatcher import ExchangeDispatcher

""" Order class will represent an open order in the specified exchange
In simulation it will also define rules to be filled / canceled
It is also use to store creation & fill values of the order """


@dataclass
class Order:
    __metaclass__ = ABCMeta

    trader: Any = field(init=True, repr=False)
    exchange: ExchangeDispatcher = field(init=False, repr=False)
    is_simulated: bool = field(init=False, repr=False)
    side: TradeOrderSide = None
    symbol: str = None
    origin_price: float = 0
    origin_stop_price: float = 0
    origin_quantity: float = 0
    market_total_fees: float = 0
    filled_quantity: float = 0
    filled_price: float = 0
    total_cost: float = 0
    fee: Dict[str, Union[str, float]] = None
    currency: str = None
    market: str = None
    order_id: str = None
    status: OrderStatus = OrderStatus.OPEN
    order_type: TraderOrderType = None
    timestamp: int = None
    creation_time: int = time.time()
    canceled_time: int = 0
    executed_time: int = 0
    last_prices: List[Any] = None
    created_last_price: float = 0
    order_profitability: float = 0
    linked_to: Any = None
    is_from_this_octobot: bool = True
    linked_portfolio: Any = None
    order_notifier: Any = None
    linked_orders: List[Any] = None
    taker_or_maker: ExchangeConstantsMarketPropertyColumns = None
    lock: Lock = None

    def __post_init__(self):
        self.exchange = self.trader.get_exchange()
        self.is_simulated = self.trader.simulate
        self.lock = Lock()
        self.linked_orders = []

    # syntax: "async with xxx.get_lock():"
    # TODO find better way to handle async lock: reuse disposable design pattern ?
    def get_lock(self):
        return self.lock

    # create the order by setting all the required values
    def new(self, order_type, symbol, current_price, quantity,
            price=None,
            stop_price=None,
            status=None,
            order_notifier=None,
            order_id=None,
            quantity_filled=None,
            timestamp=None,
            linked_to=None,
            linked_portfolio=None):

        self.order_id = order_id
        self.origin_price = price
        self.status = status
        self.created_last_price = current_price
        self.origin_quantity = quantity
        self.origin_stop_price = stop_price
        self.symbol = symbol
        self.order_type = order_type
        self.order_notifier = order_notifier
        self.currency, self.market = split_symbol(symbol)
        self.filled_quantity = quantity_filled
        self.linked_to = linked_to
        self.linked_portfolio = linked_portfolio

        if timestamp is None:
            self.creation_time = time.time()
        else:
            # if we have a timestamp, it's a real trader => need to format timestamp if necessary
            self.creation_time = self.exchange.get_uniform_timestamp(timestamp)

        if status is None:
            self.status = OrderStatus.OPEN
        else:
            self.status = status

        if self.trader.simulate:
            self.filled_quantity = quantity

    @abstractmethod
    async def update_order_status(self, simulated_time=False):
        """
        Update_order_status will define the rules for a simulated order to be filled / canceled
        """
        raise NotImplementedError("Update_order_status not implemented")

    # check_last_prices is used to collect data to perform the order update_order_status process
    def check_last_prices(self, price, inferior, simulated_time=False):
        if self.last_prices is not None:
            prices = [p["price"]
                      for p in self.last_prices[-SIMULATOR_LAST_PRICES_TO_CHECK:]
                      if not math.isnan(p["price"]) and (p[eC.TIMESTAMP.value] >= self.creation_time or simulated_time)]

            if prices:
                if inferior:
                    if float(min(prices)) < price:
                        get_logger(self.get_name()).debug(f"{self.symbol} last prices: {prices}, "
                                                          f"ask for {'inferior' if inferior else 'superior'} "
                                                          f"to {price}")
                        return True
                else:
                    if float(max(prices)) > price:
                        get_logger(self.get_name()).debug(f"{self.symbol} last prices: {prices}, "
                                                          f"ask for {'inferior' if inferior else 'superior'} "
                                                          f"to {price}")
                        return True
        return False

    async def cancel_order(self):
        self.status = OrderStatus.CANCELED
        self.canceled_time = time.time()

        # if real order
        if not self.is_simulated and not self.trader.check_if_self_managed(self.get_order_type()):
            await self.exchange.cancel_order(self.order_id, self.symbol)

        await self.trader.notify_order_cancel(self)

    async def cancel_from_exchange(self):
        self.status = OrderStatus.CANCELED
        self.canceled_time = time.time()
        await self.trader.notify_order_cancel(self)
        await self.trader.notify_order_close(self, cancel_linked_only=True)
        self.trader.get_order_manager().remove_order_from_list(self)

    async def close_order(self):
        await self.trader.notify_order_close(self)

    def add_linked_order(self, order):
        self.linked_orders.append(order)

    def get_linked_orders(self):
        return self.linked_orders

    def get_currency_and_market(self):
        return self.currency, self.market

    def get_side(self):
        return self.side

    def get_id(self):
        return self.order_id

    def get_total_fees(self, currency):
        if self.fee and self.fee[FeePropertyColumns.CURRENCY.value] == currency:
            return self.fee[FeePropertyColumns.COST.value]
        else:
            return 0

    def get_filled_quantity(self):
        return self.filled_quantity

    def get_filled_price(self):
        return self.filled_price

    def get_total_cost(self):
        return self.total_cost

    def get_status(self):
        return self.status

    def get_order_type(self):
        return self.order_type

    def get_order_symbol(self):
        return self.symbol

    def get_exchange(self):
        return self.exchange

    def get_origin_quantity(self):
        return self.origin_quantity

    def get_origin_price(self):
        return self.origin_price

    def get_order_notifier(self):
        return self.order_notifier

    def get_creation_time(self):
        return self.creation_time

    def set_last_prices(self, last_prices):
        self.last_prices = last_prices

    def get_create_last_price(self):
        return self.created_last_price

    def is_filled(self):
        return self.status == OrderStatus.FILLED

    def is_cancelled(self):
        return self.status == OrderStatus.CANCELED

    def get_is_from_this_octobot(self):
        return self.is_from_this_octobot

    def set_is_from_this_octobot(self, is_from_this_octobot):
        self.is_from_this_octobot = is_from_this_octobot

    def get_string_info(self):
        return (f"{self.get_order_symbol()} | "
                f"{self.get_order_type().name} | "
                f"Price : {self.get_origin_price()} | "
                f"Quantity : {self.get_origin_quantity()} | "
                f"Status : {self.get_status().name}")

    def get_description(self):
        return f"{self.get_id()}{self.exchange.get_name()}{self.get_string_info()}"

    def matches_description(self, description):
        return self.get_description() == description

    def infer_taker_or_maker(self):
        if self.taker_or_maker is None:
            if self.order_type == TraderOrderType.SELL_MARKET \
                    or self.order_type == TraderOrderType.BUY_MARKET \
                    or self.order_type == TraderOrderType.STOP_LOSS:
                # always true
                return ExchangeConstantsMarketPropertyColumns.TAKER.value
            else:
                # true 90% of the time: impossible to know for sure the reality
                # (should only be used for simulation anyway)
                return ExchangeConstantsMarketPropertyColumns.MAKER.value
        return self.taker_or_maker

    def get_computed_fee(self, forced_value=None):
        computed_fee = self.exchange.get_trade_fee(self.symbol, self.order_type, self.filled_quantity,
                                                   self.filled_price, self.infer_taker_or_maker())
        return {
            FeePropertyColumns.COST.value:
                forced_value if forced_value is not None else computed_fee[FeePropertyColumns.COST.value],
            FeePropertyColumns.CURRENCY.value: computed_fee[FeePropertyColumns.CURRENCY.value],
        }

    def get_profitability(self):
        if self.get_filled_price() != 0 and self.get_create_last_price() != 0:
            if self.get_filled_price() >= self.get_create_last_price():
                self.order_profitability = 1 - self.get_filled_price() / self.get_create_last_price()
                if self.side == TradeOrderSide.SELL:
                    self.order_profitability *= -1
            else:
                self.order_profitability = 1 - self.get_create_last_price() / self.get_filled_price()
                if self.side == TradeOrderSide.BUY:
                    self.order_profitability *= -1
        return self.order_profitability

    @classmethod
    def get_name(cls):
        return cls.__name__

    async def default_exchange_update_order_status(self):
        result = await self.exchange.get_order(self.order_id, self.symbol)
        new_status = self.trader.parse_status(result)
        if new_status == OrderStatus.FILLED:
            self.trader.parse_exchange_order_to_trade_instance(result, self)
        elif new_status == OrderStatus.CANCELED:
            await self.cancel_from_exchange()

    def generate_executed_time(self, simulated_time=False):
        if not simulated_time or not self.last_prices:
            return time.time()
        else:
            return self.last_prices[-1][eC.TIMESTAMP.value]


class BuyMarketOrder(Order):
    def __post_init__(self):
        super().__post_init__()
        self.side = TradeOrderSide.BUY

    async def update_order_status(self, simulated_time=False):
        if not self.trader.simulate:
            await self.default_exchange_update_order_status()
        else:
            # ONLY FOR SIMULATION
            self.status = OrderStatus.FILLED
            self.origin_price = self.created_last_price
            self.filled_price = self.created_last_price
            self.filled_quantity = self.origin_quantity
            self.total_cost = self.filled_price*self.filled_quantity
            self.fee = self.get_computed_fee()
            self.executed_time = self.generate_executed_time(simulated_time)


class BuyLimitOrder(Order):
    def __post_init__(self):
        super().__post_init__()
        self.side = TradeOrderSide.BUY

    async def update_order_status(self, simulated_time=False):
        if not self.trader.simulate:
            await self.default_exchange_update_order_status()
        else:
            # ONLY FOR SIMULATION
            if self.check_last_prices(self.origin_price, True, simulated_time):
                self.status = OrderStatus.FILLED
                self.filled_price = self.origin_price
                self.filled_quantity = self.origin_quantity
                self.total_cost = self.filled_price*self.filled_quantity
                self.fee = self.get_computed_fee()
                self.executed_time = self.generate_executed_time(simulated_time)


class SellMarketOrder(Order):
    def __post_init__(self):
        super().__post_init__()
        self.side = TradeOrderSide.SELL

    async def update_order_status(self, simulated_time=False):
        if not self.trader.simulate:
            await self.default_exchange_update_order_status()
        else:
            # ONLY FOR SIMULATION
            self.status = OrderStatus.FILLED
            self.origin_price = self.created_last_price
            self.filled_price = self.created_last_price
            self.filled_quantity = self.origin_quantity
            self.total_cost = self.filled_price*self.filled_quantity
            self.fee = self.get_computed_fee()
            self.executed_time = self.generate_executed_time(simulated_time)


class SellLimitOrder(Order):
    def __post_init__(self):
        super().__post_init__()
        self.side = TradeOrderSide.SELL

    async def update_order_status(self, simulated_time=False):
        if not self.trader.simulate:
            await self.default_exchange_update_order_status()
        else:
            # ONLY FOR SIMULATION
            if self.check_last_prices(self.origin_price, False, simulated_time):
                self.status = OrderStatus.FILLED
                self.filled_price = self.origin_price
                self.filled_quantity = self.origin_quantity
                self.total_cost = self.filled_price*self.filled_quantity
                self.fee = self.get_computed_fee()
                self.executed_time = self.generate_executed_time(simulated_time)


class StopLossOrder(Order):
    def __post_init__(self):
        super().__post_init__()
        self.side = TradeOrderSide.SELL

    async def update_order_status(self, simulated_time=False):
        if self.check_last_prices(self.origin_price, True, simulated_time):
            self.status = OrderStatus.FILLED
            self.filled_price = self.origin_price
            self.filled_quantity = self.origin_quantity
            self.total_cost = self.filled_price*self.filled_quantity
            self.executed_time = self.generate_executed_time(simulated_time)
            if self.trader.simulate:
                # compute normal fees
                self.fee = self.get_computed_fee()
            else:
                # force 0 fee: not a real order: only used as a trigger
                self.fee = self.get_computed_fee(forced_value=0)
                for order in self.linked_orders:
                    await self.trader.cancel_order(order)
                await self.trader.create_artificial_order(TraderOrderType.SELL_MARKET, self.symbol, self.origin_price,
                                                          self.origin_quantity, self.origin_price,
                                                          self.linked_portfolio)


# TODO
class StopLossLimitOrder(Order):
    def __post_init__(self):
        super().__post_init__()
        self.side = TradeOrderSide.SELL

    async def update_order_status(self, simulated_time=False):
        pass


# TODO
class TakeProfitOrder(Order):
    def __post_init__(self):
        super().__post_init__()
        self.side = TradeOrderSide.SELL

    async def update_order_status(self, simulated_time=False):
        pass


# TODO
class TakeProfitLimitOrder(Order):
    def __post_init__(self):
        super().__post_init__()
        self.side = TradeOrderSide.SELL

    async def update_order_status(self, simulated_time=False):
        pass


class OrderConstants:
    TraderOrderTypeClasses = {
        TraderOrderType.BUY_MARKET: BuyMarketOrder,
        TraderOrderType.BUY_LIMIT: BuyLimitOrder,
        TraderOrderType.TAKE_PROFIT: TakeProfitOrder,
        TraderOrderType.TAKE_PROFIT_LIMIT: TakeProfitLimitOrder,
        TraderOrderType.STOP_LOSS: StopLossOrder,
        TraderOrderType.STOP_LOSS_LIMIT: StopLossLimitOrder,
        TraderOrderType.SELL_MARKET: SellMarketOrder,
        TraderOrderType.SELL_LIMIT: SellLimitOrder,
    }
