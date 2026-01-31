# cython: language_level=3
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
#  Lesser General License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
from octobot_trading.producers.abstract_mode_producer cimport AbstractTradingModeProducer

from octobot_trading.consumers.abstract_mode_consumer cimport AbstractTradingModeConsumer

from octobot_trading.modes.abstract_trading_mode cimport AbstractTradingMode


cdef class DailyTradingMode(AbstractTradingMode):
    pass


cdef class DailyTradingModeConsumer(AbstractTradingModeConsumer):
    cdef public double MAX_SUM_RESULT

    cdef public double STOP_LOSS_ORDER_MAX_PERCENT
    cdef public double STOP_LOSS_ORDER_MIN_PERCENT
    cdef public double STOP_LOSS_ORDER_ATTENUATION

    cdef public double QUANTITY_MIN_PERCENT
    cdef public double QUANTITY_MAX_PERCENT
    cdef public double QUANTITY_ATTENUATION

    cdef public double QUANTITY_MARKET_MIN_PERCENT
    cdef public double QUANTITY_MARKET_MAX_PERCENT
    cdef public double QUANTITY_BUY_MARKET_ATTENUATION
    cdef public double QUANTITY_MARKET_ATTENUATION

    cdef public double BUY_LIMIT_ORDER_MAX_PERCENT
    cdef public double BUY_LIMIT_ORDER_MIN_PERCENT
    cdef public double SELL_LIMIT_ORDER_MIN_PERCENT
    cdef public double SELL_LIMIT_ORDER_MAX_PERCENT
    cdef public double LIMIT_ORDER_ATTENUATION

    cdef public double QUANTITY_RISK_WEIGHT
    cdef public double MAX_QUANTITY_RATIO
    cdef public double MIN_QUANTITY_RATIO
    cdef public double DELTA_RATIO

    cdef public double SELL_MULTIPLIER
    cdef public double FULL_SELL_MIN_RATIO

    cdef public bint USE_CLOSE_TO_CURRENT_PRICE
    cdef public double CLOSE_TO_CURRENT_PRICE_DEFAULT_RATIO
    cdef public bint BUY_WITH_MAXIMUM_SIZE_ORDERS
    cdef public bint SELL_WITH_MAXIMUM_SIZE_ORDERS
    cdef public bint DISABLE_BUY_ORDERS
    cdef public bint DISABLE_SELL_ORDERS
    cdef public bint USE_STOP_ORDERS

    cpdef __get_limit_price_from_risk(self, object eval_note)
    cpdef __get_stop_price_from_risk(self)
    cpdef __get_buy_limit_quantity_from_risk(self, object eval_note, double quantity, str quote)
    cpdef __get_market_quantity_from_risk(self, object eval_note, double quantity, str quote, bint selling=*)

cdef class DailyTradingModeProducer(AbstractTradingModeProducer):
    cdef public object state

    cdef public double VERY_LONG_THRESHOLD
    cdef public double LONG_THRESHOLD
    cdef public double NEUTRAL_THRESHOLD
    cdef public double SHORT_THRESHOLD
    cdef public double RISK_THRESHOLD

    cpdef double __get_delta_risk(self)
