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
import decimal

import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants


class ArbitrageContainer:
    # 0.3 %
    SIMILARITY_RATIO = decimal.Decimal(str(0.003))

    def __init__(self, own_exchange_price: decimal.Decimal, target_price: decimal.Decimal, state):
        self.own_exchange_price: decimal.Decimal = own_exchange_price
        self.target_price: decimal.Decimal = target_price
        self.state = state
        self.passed_initial_order = False
        self.initial_before_fee_filled_quantity: decimal.Decimal = None
        self.initial_limit_order_id = None
        self.secondary_limit_order_id = None
        self.secondary_stop_order_id = None

    def is_similar(self, own_exchange_price: decimal.Decimal, state):
        # if state and initial price is are the same or own_exchange_price is in current arbitrage window
        return state is self.state and (
            own_exchange_price == self.own_exchange_price
            or (
                (
                    state is trading_enums.EvaluatorStates.LONG and
                    (
                            self.own_exchange_price * (trading_constants.ONE - ArbitrageContainer.SIMILARITY_RATIO)
                            < own_exchange_price
                            < self.target_price * (trading_constants.ONE + ArbitrageContainer.SIMILARITY_RATIO)
                    )
                )
                or (
                    state is trading_enums.EvaluatorStates.SHORT and
                    (
                            self.target_price * (trading_constants.ONE - ArbitrageContainer.SIMILARITY_RATIO)
                            < own_exchange_price
                            < self.own_exchange_price * (trading_constants.ONE + ArbitrageContainer.SIMILARITY_RATIO)
                    )
                )
            )
        )

    def is_expired(self, other_exchanges_average_price):
        if self.state is trading_enums.EvaluatorStates.LONG:
            return other_exchanges_average_price < self.target_price * \
                   (trading_constants.ONE - ArbitrageContainer.SIMILARITY_RATIO)
        if self.state is trading_enums.EvaluatorStates.SHORT:
            return other_exchanges_average_price > self.target_price * \
                   (trading_constants.ONE + ArbitrageContainer.SIMILARITY_RATIO)

    def should_be_discarded_after_order_cancel(self, order_id):
        # should be discarded if initial order is cancelled
        return self.initial_limit_order_id == order_id

    def is_watching_this_order(self, order_id):
        return self.initial_limit_order_id == order_id \
           or self.secondary_limit_order_id == order_id \
           or self.secondary_stop_order_id == order_id
