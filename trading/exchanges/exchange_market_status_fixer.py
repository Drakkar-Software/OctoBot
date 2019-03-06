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
import math
from decimal import Decimal
from math import nan

from config import ExchangeConstantsMarketStatusColumns as Ecmsc
from config import ExchangeConstantsMarketStatusInfoColumns as Ecmsic


class ExchangeMarketStatusFixer:
    LIMIT_PRICE_MULTIPLIER = 1000
    LIMIT_COST_MULTIPLIER = 1

    # calculated from popular exchanges
    LIMIT_AMOUNT_MAX_SUP_ATTENUATION = 6        # when log(price, 10) >= 0
    LIMIT_AMOUNT_MAX_MINUS_3_ATTENUATION = 1    # when log(price, 10) > -3
    LIMIT_AMOUNT_MIN_ATTENUATION = 3            # when log(price, 10) < 0
    LIMIT_AMOUNT_MIN_SUP_ATTENUATION = 1        # when log(price, 10) >= 0

    """
    Utility class that performs exchange_self.market_status fixes
    """

    def __init__(self, market_status, price_example=None):
        self.market_status = market_status
        self.price_example = price_example

        if Ecmsc.INFO.value in self.market_status:
            self.market_status_specific = self.market_status[Ecmsc.INFO.value]
        else:
            self.market_status_specific = None

        self._fix_market_status_precision()
        self._fix_market_status_limits()

    def get_market_status(self):
        return self.market_status

    def _fix_market_status_precision(self):
        if Ecmsc.PRECISION.value not in self.market_status:
            self.market_status[Ecmsc.PRECISION.value] = {
                Ecmsc.PRECISION_AMOUNT.value: None,
                Ecmsc.PRECISION_COST.value: None,
                Ecmsc.PRECISION_PRICE.value: None,
            }

        market_precision = self.market_status[Ecmsc.PRECISION.value]

        if not self._check_market_status_values(market_precision.values(), zero_valid=True):
            if self.price_example is not None:
                self._fix_market_status_precision_with_price()

            elif self.market_status_specific:
                self._fix_market_status_precision_with_specific()

    def _fix_market_status_limits(self):
        if Ecmsc.LIMITS.value not in self.market_status:
            self.market_status[Ecmsc.LIMITS.value] = {}

        market_limit = self.market_status[Ecmsc.LIMITS.value]

        if Ecmsc.LIMITS_COST.value not in market_limit:
            market_limit[Ecmsc.LIMITS_COST.value] = {
                Ecmsc.LIMITS_COST_MAX.value: None,
                Ecmsc.LIMITS_COST_MIN.value: None
            }

        if Ecmsc.LIMITS_AMOUNT.value not in market_limit:
            market_limit[Ecmsc.LIMITS_AMOUNT.value] = {
                Ecmsc.LIMITS_AMOUNT_MAX.value: None,
                Ecmsc.LIMITS_AMOUNT_MIN.value: None
            }

        if Ecmsc.LIMITS_PRICE.value not in market_limit:
            market_limit[Ecmsc.LIMITS_PRICE.value] = {
                Ecmsc.LIMITS_PRICE_MAX.value: None,
                Ecmsc.LIMITS_PRICE_MIN.value: None
            }

        # if some data is missing
        if not self._check_market_status_limits(market_limit):
            self._fix_market_status_limits_from_current_data(market_limit)

            if self.market_status_specific and not self._check_market_status_limits(market_limit):
                self._fix_market_status_limits_with_specific()

            if self.price_example is not None and not self._check_market_status_limits(market_limit):
                self._fix_market_status_limits_with_price()

    @staticmethod
    def _check_market_status_limits(market_limit):
        return all([ExchangeMarketStatusFixer._check_market_status_values(market_limit[key].values())
                    for key in market_limit])

    @staticmethod
    def _check_market_status_values(values, zero_valid=False):
        return all([ExchangeMarketStatusFixer.is_ms_valid(value, zero_valid=zero_valid) for value in values])

    @staticmethod
    def is_ms_valid(value, zero_valid=False):
        return value is not None and value is not nan and (value >= 0 if zero_valid else value > 0)

    def _fix_market_status_limits_from_current_data(self, market_limit):
        # calculate cost
        if not (self._check_market_status_values(market_limit[Ecmsc.LIMITS_COST.value].values())):
            self._calculate_costs(market_limit)

        # calculate amounts
        if not (self._check_market_status_values(market_limit[Ecmsc.LIMITS_AMOUNT.value].values())):
            self._calculate_amounts(market_limit)

        # calculate prices
        if not (self._check_market_status_values(market_limit[Ecmsc.LIMITS_PRICE.value].values())):
            self._calculate_prices(market_limit)

        if not self.is_ms_valid(market_limit[Ecmsc.LIMITS_COST.value][Ecmsc.LIMITS_COST_MIN.value]):
            market_limit[Ecmsc.LIMITS_COST.value][Ecmsc.LIMITS_COST_MIN.value] = 0

    @staticmethod
    def _get_markets_limit(market_limit):
        return market_limit[Ecmsc.LIMITS_COST.value] if Ecmsc.LIMITS_COST.value in market_limit else None, \
               market_limit[Ecmsc.LIMITS_PRICE.value] if Ecmsc.LIMITS_PRICE.value in market_limit else None, \
               market_limit[Ecmsc.LIMITS_AMOUNT.value] if Ecmsc.LIMITS_AMOUNT.value in market_limit else None

    @staticmethod
    def _calculate_costs(market_limit):
        limit_cost, limit_price, limit_amount = ExchangeMarketStatusFixer._get_markets_limit(market_limit)

        if Ecmsc.LIMITS_AMOUNT_MAX.value in limit_amount and Ecmsc.LIMITS_PRICE_MAX.value in limit_price:
            if ExchangeMarketStatusFixer.is_ms_valid(limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value]) \
                    and ExchangeMarketStatusFixer.is_ms_valid(limit_price[Ecmsc.LIMITS_PRICE_MAX.value]) \
                    and not ExchangeMarketStatusFixer.is_ms_valid(limit_cost[Ecmsc.LIMITS_COST_MAX.value]):
                limit_cost[Ecmsc.LIMITS_COST_MAX.value] = limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value] * \
                                                          limit_price[Ecmsc.LIMITS_PRICE_MAX.value]

        if Ecmsc.LIMITS_AMOUNT_MIN.value in limit_amount and Ecmsc.LIMITS_PRICE_MIN.value in limit_price:
            if ExchangeMarketStatusFixer.is_ms_valid(limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value]) \
                    and ExchangeMarketStatusFixer.is_ms_valid(limit_price[Ecmsc.LIMITS_PRICE_MIN.value]) \
                    and not ExchangeMarketStatusFixer.is_ms_valid(limit_cost[Ecmsc.LIMITS_COST_MIN.value]):
                limit_cost[Ecmsc.LIMITS_COST_MIN.value] = limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value] * \
                                                          limit_price[Ecmsc.LIMITS_PRICE_MIN.value]

    @staticmethod
    def _calculate_prices(market_limit):
        limit_cost, limit_price, limit_amount = ExchangeMarketStatusFixer._get_markets_limit(market_limit)

        if Ecmsc.LIMITS_COST_MAX.value in limit_cost and Ecmsc.LIMITS_AMOUNT_MAX.value in limit_amount:
            if ExchangeMarketStatusFixer.is_ms_valid(limit_cost[Ecmsc.LIMITS_COST_MAX.value]) \
                    and ExchangeMarketStatusFixer.is_ms_valid(limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value]) \
                    and limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value] > 0:
                limit_price[Ecmsc.LIMITS_PRICE_MAX.value] = limit_cost[Ecmsc.LIMITS_COST_MAX.value] / \
                                                            limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value]

        if Ecmsc.LIMITS_COST_MIN.value in limit_cost and Ecmsc.LIMITS_AMOUNT_MIN.value in limit_amount:
            if ExchangeMarketStatusFixer.is_ms_valid(limit_cost[Ecmsc.LIMITS_COST_MIN.value]) \
                    and ExchangeMarketStatusFixer.is_ms_valid(limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value]) \
                    and limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value] > 0:
                limit_price[Ecmsc.LIMITS_PRICE_MIN.value] = limit_cost[Ecmsc.LIMITS_COST_MIN.value] / \
                                                            limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value]

    @staticmethod
    def _calculate_amounts(market_limit):
        limit_cost, limit_price, limit_amount = ExchangeMarketStatusFixer._get_markets_limit(market_limit)

        if Ecmsc.LIMITS_COST_MAX.value in limit_cost and Ecmsc.LIMITS_PRICE_MAX.value in limit_price:
            if ExchangeMarketStatusFixer.is_ms_valid(limit_cost[Ecmsc.LIMITS_COST_MAX.value]) \
                    and ExchangeMarketStatusFixer.is_ms_valid(limit_price[Ecmsc.LIMITS_PRICE_MAX.value]) \
                    and limit_price[Ecmsc.LIMITS_PRICE_MAX.value] > 0:
                limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value] = limit_cost[Ecmsc.LIMITS_COST_MAX.value] / \
                                                              limit_price[Ecmsc.LIMITS_PRICE_MAX.value]

        if Ecmsc.LIMITS_COST_MIN.value in limit_cost and Ecmsc.LIMITS_PRICE_MIN.value in limit_price:
            if ExchangeMarketStatusFixer.is_ms_valid(limit_cost[Ecmsc.LIMITS_COST_MIN.value]) \
                    and ExchangeMarketStatusFixer.is_ms_valid(limit_price[Ecmsc.LIMITS_PRICE_MIN.value]) \
                    and limit_price[Ecmsc.LIMITS_PRICE_MIN.value] > 0:
                limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value] = limit_cost[Ecmsc.LIMITS_COST_MIN.value] / \
                                                              limit_price[Ecmsc.LIMITS_PRICE_MIN.value]

    def _calculate_amount(self):
        amount_log_price = math.log(self.price_example, 10)

        if amount_log_price >= 0:
            amount_min = 10 ** (self.LIMIT_AMOUNT_MIN_SUP_ATTENUATION - amount_log_price)
            amount_max = 10 ** (self.LIMIT_AMOUNT_MAX_SUP_ATTENUATION - amount_log_price)
        else:
            amount_min = 10 ** -(amount_log_price + self.LIMIT_AMOUNT_MIN_ATTENUATION)
            amount_max = 10 ** (-amount_log_price + self.LIMIT_AMOUNT_MAX_MINUS_3_ATTENUATION)

        return amount_min, amount_max

    def _fix_market_status_limits_with_price(self):
        # self.LIMIT_AMOUNT_MULTIPLIER
        amount_min, amount_max = self._calculate_amount()
        price_max = self.price_example * self.LIMIT_PRICE_MULTIPLIER
        price_min = self.price_example / self.LIMIT_PRICE_MULTIPLIER

        self.market_status[Ecmsc.LIMITS.value] = {
            Ecmsc.LIMITS_AMOUNT.value: {
                Ecmsc.LIMITS_AMOUNT_MIN.value: amount_min,
                Ecmsc.LIMITS_AMOUNT_MAX.value: amount_max,
            },
            Ecmsc.LIMITS_PRICE.value: {
                Ecmsc.LIMITS_PRICE_MIN.value: price_min,
                Ecmsc.LIMITS_PRICE_MAX.value: price_max,
            },
            Ecmsc.LIMITS_COST.value: {
                Ecmsc.LIMITS_COST_MIN.value: price_min * amount_min,
                Ecmsc.LIMITS_COST_MAX.value: price_max * amount_max,
            }
        }

    def _get_price_precision(self):
        return -Decimal(f"{self.price_example}").as_tuple().exponent

    def _fix_market_status_precision_with_price(self):
        precision = self._get_price_precision()
        self.market_status[Ecmsc.PRECISION.value] = {
            Ecmsc.PRECISION_AMOUNT.value: precision,
            Ecmsc.PRECISION_COST.value: precision,
            Ecmsc.PRECISION_PRICE.value: precision,
        }

    def _fix_market_status_precision_with_specific(self):
        # binance specific
        pass  # nothing for binance

    def _fix_market_status_limits_with_specific(self):
        market_limit = self.market_status[Ecmsc.LIMITS.value]

        try:
            # binance specific
            if Ecmsic.FILTERS.value in self.market_status_specific:
                filters = self.market_status_specific[Ecmsic.FILTERS.value]

                for filter_dict in filters:
                    if Ecmsic.FILTER_TYPE.value in filter_dict:
                        if filter_dict[Ecmsic.FILTER_TYPE.value] == Ecmsic.PRICE_FILTER.value:
                            if self.is_ms_valid(float(filter_dict[Ecmsic.MAX_PRICE.value])) \
                                    and not self.is_ms_valid(
                                        market_limit[Ecmsc.LIMITS_PRICE.value][Ecmsc.LIMITS_PRICE_MAX.value]):
                                market_limit[Ecmsc.LIMITS_PRICE.value][Ecmsc.LIMITS_PRICE_MAX.value] = \
                                    float(filter_dict[Ecmsic.MAX_PRICE.value])

                            if self.is_ms_valid(float(filter_dict[Ecmsic.MIN_PRICE.value])) \
                                    and not self.is_ms_valid(
                                        market_limit[Ecmsc.LIMITS_PRICE.value][Ecmsc.LIMITS_PRICE_MIN.value]):
                                market_limit[Ecmsc.LIMITS_PRICE.value][Ecmsc.LIMITS_PRICE_MIN.value] = \
                                    float(filter_dict[Ecmsic.MIN_PRICE.value])
                        elif filter_dict[Ecmsic.FILTER_TYPE.value] == Ecmsic.LOT_SIZE.value:
                            if self.is_ms_valid(float(filter_dict[Ecmsic.MAX_QTY.value])) \
                                    and not self.is_ms_valid(
                                        market_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MAX.value]):
                                market_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MAX.value] = \
                                    float(filter_dict[Ecmsic.MAX_QTY.value])

                            if self.is_ms_valid(float(filter_dict[Ecmsic.MIN_QTY.value])) \
                                    and not self.is_ms_valid(
                                        market_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MIN.value]):
                                market_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MIN.value] = \
                                    float(filter_dict[Ecmsic.MIN_QTY.value])
                self._calculate_costs(market_limit)
        except Exception:
            pass
