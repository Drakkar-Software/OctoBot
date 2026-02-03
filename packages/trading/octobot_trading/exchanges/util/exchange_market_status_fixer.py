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
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import decimal
import math

import octobot_commons.logging as logging
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc
from octobot_trading.enums import ExchangeConstantsMarketStatusInfoColumns as Ecmsic


def is_ms_valid(value, zero_valid=False):
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return False
    return value is not None and value is not math.nan and (value >= 0 if zero_valid else value > 0)


def check_market_status_limits(market_limit):
    return all([check_market_status_values(market_limit[key].values())
                for key in market_limit])


def check_market_status_values(values, zero_valid=False):
    return all([is_ms_valid(value, zero_valid=zero_valid) for value in values])


def get_markets_limit(market_limit):
    return market_limit[Ecmsc.LIMITS_COST.value] if Ecmsc.LIMITS_COST.value in market_limit else None, \
           market_limit[Ecmsc.LIMITS_PRICE.value] if Ecmsc.LIMITS_PRICE.value in market_limit else None, \
           market_limit[Ecmsc.LIMITS_AMOUNT.value] if Ecmsc.LIMITS_AMOUNT.value in market_limit else None


def calculate_amounts(market_limit):
    limit_cost, limit_price, limit_amount = get_markets_limit(market_limit)

    if not is_ms_valid(limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value]) and \
        Ecmsc.LIMITS_COST_MAX.value in limit_cost and Ecmsc.LIMITS_PRICE_MAX.value in limit_price:
        if is_ms_valid(limit_cost[Ecmsc.LIMITS_COST_MAX.value]) \
                and is_ms_valid(limit_price[Ecmsc.LIMITS_PRICE_MAX.value]) \
                and limit_price[Ecmsc.LIMITS_PRICE_MAX.value] > 0:
            limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value] = limit_cost[Ecmsc.LIMITS_COST_MAX.value] / \
                                                          limit_price[Ecmsc.LIMITS_PRICE_MAX.value]

    if not is_ms_valid(limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value]) and \
        Ecmsc.LIMITS_COST_MIN.value in limit_cost and Ecmsc.LIMITS_PRICE_MIN.value in limit_price:
        if is_ms_valid(limit_cost[Ecmsc.LIMITS_COST_MIN.value]) \
                and is_ms_valid(limit_price[Ecmsc.LIMITS_PRICE_MIN.value]) \
                and limit_price[Ecmsc.LIMITS_PRICE_MIN.value] > 0:
            limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value] = limit_cost[Ecmsc.LIMITS_COST_MIN.value] / \
                                                          limit_price[Ecmsc.LIMITS_PRICE_MIN.value]


def calculate_costs(market_limit):
    limit_cost, limit_price, limit_amount = get_markets_limit(market_limit)

    if not is_ms_valid(limit_cost[Ecmsc.LIMITS_COST_MAX.value]) and \
        Ecmsc.LIMITS_AMOUNT_MAX.value in limit_amount and Ecmsc.LIMITS_PRICE_MAX.value in limit_price:
        if is_ms_valid(limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value]) \
                and is_ms_valid(limit_price[Ecmsc.LIMITS_PRICE_MAX.value]):
            limit_cost[Ecmsc.LIMITS_COST_MAX.value] = limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value] * \
                                                      limit_price[Ecmsc.LIMITS_PRICE_MAX.value]

    if not is_ms_valid(limit_cost[Ecmsc.LIMITS_COST_MIN.value]) and \
        Ecmsc.LIMITS_AMOUNT_MIN.value in limit_amount and Ecmsc.LIMITS_PRICE_MIN.value in limit_price:
        if is_ms_valid(limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value]) \
                and is_ms_valid(limit_price[Ecmsc.LIMITS_PRICE_MIN.value]):
            limit_cost[Ecmsc.LIMITS_COST_MIN.value] = limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value] * \
                                                      limit_price[Ecmsc.LIMITS_PRICE_MIN.value]


def update_prices(market_limit):
    _, limit_price, _ = get_markets_limit(market_limit)

    if not is_ms_valid(limit_price[Ecmsc.LIMITS_PRICE_MAX.value]):
        limit_price[Ecmsc.LIMITS_PRICE_MAX.value] = None

    if not is_ms_valid(limit_price[Ecmsc.LIMITS_PRICE_MIN.value]):
        limit_price[Ecmsc.LIMITS_PRICE_MIN.value] = None


def fix_market_status_limits_from_current_data(market_limit):
    # calculate cost
    if not (check_market_status_values(market_limit[Ecmsc.LIMITS_COST.value].values())):
        calculate_costs(market_limit)

    # calculate amounts
    if not (check_market_status_values(market_limit[Ecmsc.LIMITS_AMOUNT.value].values())):
        calculate_amounts(market_limit)

    # set price to None if missing
    if not (check_market_status_values(market_limit[Ecmsc.LIMITS_PRICE.value].values())):
        update_prices(market_limit)

    if not is_ms_valid(
            market_limit[Ecmsc.LIMITS_COST.value][Ecmsc.LIMITS_COST_MIN.value]):
        market_limit[Ecmsc.LIMITS_COST.value][Ecmsc.LIMITS_COST_MIN.value] = 0


class ExchangeMarketStatusFixer:
    # todo move to connector/ccxt
    LIMIT_PRICE_MULTIPLIER = 1000
    LIMIT_COST_MULTIPLIER = 1

    # calculated from popular exchanges
    LIMIT_AMOUNT_MAX_SUP_ATTENUATION = 8  # when log(price, 10) >= 0
    LIMIT_AMOUNT_MAX_MINUS_3_ATTENUATION = 8  # when log(price, 10) < 0
    LIMIT_AMOUNT_MIN_ATTENUATION = 3  # when log(price, 10) < 0
    LIMIT_AMOUNT_MIN_SUP_ATTENUATION = 1  # when log(price, 10) >= 0

    """
    Utility class that performs exchange_self.market_status fixes
    """

    def __init__(self, market_status, price_example=None):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.market_status = market_status
        self.price_example = price_example

        if Ecmsc.INFO.value in self.market_status:
            self.market_status_specific = self.market_status[Ecmsc.INFO.value]
        else:
            self.market_status_specific = None

        self._fix_typing()
        self._fix_market_status_precision()
        self._fix_market_status_limits()

    def _convert_values_to_float(self, element, parent_keys, key_whitelist):
        try:
            for parent_key in parent_keys:
                element = element[parent_key]
        except KeyError:
            # no parent_key in element, nothing to convert
            return
        for key, val in element.items():
            if key in key_whitelist and isinstance(val, str):
                try:
                    element[key] = float(val)
                except ValueError:
                    self.logger.debug(f"Impossible to convert {val} to float in {key} market status. "
                                      f"Full market status: {self.market_status}")

    def _fix_typing(self):
        self._convert_values_to_float(
            self.market_status,
            [Ecmsc.PRECISION.value, ],
            [Ecmsc.PRECISION_AMOUNT.value, Ecmsc.PRECISION_PRICE.value],
        )
        self._convert_values_to_float(
            self.market_status,
            [Ecmsc.LIMITS.value, Ecmsc.LIMITS_COST.value],
            [Ecmsc.LIMITS_COST_MAX.value, Ecmsc.LIMITS_COST_MIN.value],
        )
        self._convert_values_to_float(
            self.market_status,
            [Ecmsc.LIMITS.value, Ecmsc.LIMITS_AMOUNT.value],
            [Ecmsc.LIMITS_AMOUNT_MAX.value, Ecmsc.LIMITS_AMOUNT_MIN.value],
        )
        self._convert_values_to_float(
            self.market_status,
            [Ecmsc.LIMITS.value, Ecmsc.LIMITS_PRICE.value],
            [Ecmsc.LIMITS_PRICE_MAX.value, Ecmsc.LIMITS_PRICE_MIN.value],
        )

    def _fix_market_status_precision(self):
        if Ecmsc.PRECISION.value not in self.market_status:
            self.market_status[Ecmsc.PRECISION.value] = {
                Ecmsc.PRECISION_AMOUNT.value: None,
                Ecmsc.PRECISION_PRICE.value: None,
            }

        market_precision = self.market_status[Ecmsc.PRECISION.value]

        if not check_market_status_values(
            (market_precision.get(Ecmsc.PRECISION_AMOUNT.value), market_precision.get(Ecmsc.PRECISION_PRICE.value)),
            zero_valid=True
         ):
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
        if not check_market_status_limits(market_limit):
            fix_market_status_limits_from_current_data(market_limit)

            if self.market_status_specific and not check_market_status_limits(market_limit):
                self._fix_market_status_limits_with_specific()

            if self.price_example is not None and not check_market_status_limits(market_limit):
                self._fix_market_status_limits_with_price()

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
        candidate_amount_min, candidate_amount_max = self._calculate_amount()
        limits_amount = self.market_status[Ecmsc.LIMITS.value][Ecmsc.LIMITS_AMOUNT.value]
        amount_min = limits_amount.get(Ecmsc.LIMITS_AMOUNT_MIN.value)
        if not is_ms_valid(amount_min, zero_valid=True):
            amount_min = candidate_amount_min
        amount_max = limits_amount.get(Ecmsc.LIMITS_AMOUNT_MAX.value)
        if not is_ms_valid(amount_max, zero_valid=False):
            amount_max = candidate_amount_max

        limits_price = self.market_status[Ecmsc.LIMITS.value][Ecmsc.LIMITS_PRICE.value]
        price_min = limits_price.get(Ecmsc.LIMITS_PRICE_MIN.value)
        if not is_ms_valid(price_min, zero_valid=True):
            price_min = self.price_example / self.LIMIT_PRICE_MULTIPLIER
        price_max = limits_price.get(Ecmsc.LIMITS_PRICE_MAX.value)
        if not is_ms_valid(price_max, zero_valid=False):
            price_max = self.price_example * self.LIMIT_PRICE_MULTIPLIER
        limit_cost = self.market_status[Ecmsc.LIMITS.value].get(Ecmsc.LIMITS_COST.value, {})
        cost_min = limit_cost.get(Ecmsc.LIMITS_COST_MIN.value)
        if not is_ms_valid(cost_min, zero_valid=False):
            updated_cost = False
            if (
                is_ms_valid(limits_price.get(Ecmsc.LIMITS_PRICE_MIN.value))
                and is_ms_valid(limits_amount.get(Ecmsc.LIMITS_AMOUNT_MIN.value))
            ):
                # min cost can be computed from min price and amount: those values come from exchange data
                candidate_cost_min = (
                    limits_price.get(Ecmsc.LIMITS_PRICE_MIN.value)
                    * limits_amount.get(Ecmsc.LIMITS_AMOUNT_MIN.value)
                )
                if is_ms_valid(candidate_cost_min, zero_valid=False):
                    cost_min = candidate_cost_min
                    updated_cost = True
            if not updated_cost:
                # avoid computing min cost based on indirect min price or amount
                cost_min = 0
        cost_max = limit_cost.get(Ecmsc.LIMITS_COST_MAX.value)
        if not is_ms_valid(cost_max, zero_valid=False):
            cost_max = price_max * amount_max
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
                Ecmsc.LIMITS_COST_MIN.value: cost_min,
                Ecmsc.LIMITS_COST_MAX.value: cost_max,
            }
        }

    def _get_price_precision(self):
        return -decimal.Decimal(f"{self.price_example}").as_tuple().exponent

    def _fix_market_status_precision_with_price(self):
        precision = self._get_price_precision()
        # only patch value when necessary
        if not is_ms_valid(
            self.market_status[Ecmsc.PRECISION.value].get(Ecmsc.PRECISION_AMOUNT.value),
            zero_valid=True
        ):
            self.market_status[Ecmsc.PRECISION.value][Ecmsc.PRECISION_AMOUNT.value] = precision
        if not is_ms_valid(
            self.market_status[Ecmsc.PRECISION.value].get(Ecmsc.PRECISION_PRICE.value),
            zero_valid=True
        ):
            self.market_status[Ecmsc.PRECISION.value][Ecmsc.PRECISION_PRICE.value] = precision

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
                            if is_ms_valid(float(filter_dict[Ecmsic.MAX_PRICE.value])) and \
                                    not is_ms_valid(
                                        market_limit[Ecmsc.LIMITS_PRICE.value][Ecmsc.LIMITS_PRICE_MAX.value]):
                                market_limit[Ecmsc.LIMITS_PRICE.value][Ecmsc.LIMITS_PRICE_MAX.value] = \
                                    float(filter_dict[Ecmsic.MAX_PRICE.value])

                            if is_ms_valid(float(filter_dict[Ecmsic.MIN_PRICE.value])) and \
                                    not is_ms_valid(
                                        market_limit[Ecmsc.LIMITS_PRICE.value][Ecmsc.LIMITS_PRICE_MIN.value]):
                                market_limit[Ecmsc.LIMITS_PRICE.value][Ecmsc.LIMITS_PRICE_MIN.value] = \
                                    float(filter_dict[Ecmsic.MIN_PRICE.value])
                        elif filter_dict[Ecmsic.FILTER_TYPE.value] == Ecmsic.LOT_SIZE.value:
                            if is_ms_valid(float(filter_dict[Ecmsic.MAX_QTY.value])) and \
                                    not is_ms_valid(
                                        market_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MAX.value]):
                                market_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MAX.value] = \
                                    float(filter_dict[Ecmsic.MAX_QTY.value])

                            if is_ms_valid(float(filter_dict[Ecmsic.MIN_QTY.value])) and \
                                    not is_ms_valid(
                                        market_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MIN.value]):
                                market_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MIN.value] = \
                                    float(filter_dict[Ecmsic.MIN_QTY.value])
                calculate_costs(market_limit)
        except Exception:
            pass
