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

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import tentacles.Trading.Mode.daily_trading_mode.daily_trading as daily_trading_mode


class SignalTradingMode(daily_trading_mode.DailyTradingMode):

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
            trading_enums.ExchangeTypes.FUTURE,
        ]

    def get_current_state(self) -> (str, float):
        return super().get_current_state()[0] if self.producers[0].state is None else self.producers[0].state.name, \
            self.producers[0].final_eval

    def get_mode_producer_classes(self) -> list:
        return [SignalTradingModeProducer]

    def get_mode_consumer_classes(self) -> list:
        return [SignalTradingModeConsumer]

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return False


class SignalTradingModeConsumer(daily_trading_mode.DailyTradingModeConsumer):
    def __init__(self, trading_mode):
        super().__init__(trading_mode)

        self.STOP_LOSS_ORDER_MAX_PERCENT = decimal.Decimal(str(0.99))
        self.STOP_LOSS_ORDER_MIN_PERCENT = decimal.Decimal(str(0.95))

        self.QUANTITY_MIN_PERCENT = decimal.Decimal(str(0.1))
        self.QUANTITY_MAX_PERCENT = decimal.Decimal(str(0.9))

        self.QUANTITY_MARKET_MIN_PERCENT = decimal.Decimal(str(0.5))
        self.QUANTITY_MARKET_MAX_PERCENT = trading_constants.ONE
        self.QUANTITY_BUY_MARKET_ATTENUATION = decimal.Decimal(str(0.2))

        self.BUY_LIMIT_ORDER_MAX_PERCENT = decimal.Decimal(str(0.995))
        self.BUY_LIMIT_ORDER_MIN_PERCENT = decimal.Decimal(str(0.99))


class SignalTradingModeProducer(daily_trading_mode.DailyTradingModeProducer):
    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)

        # If final_eval not is < X_THRESHOLD --> state = X
        self.VERY_LONG_THRESHOLD = decimal.Decimal(str(-0.88))
        self.LONG_THRESHOLD = decimal.Decimal(str(-0.4))
        self.NEUTRAL_THRESHOLD = decimal.Decimal(str(0.4))
        self.SHORT_THRESHOLD = decimal.Decimal(str(0.88))
        self.RISK_THRESHOLD = decimal.Decimal(str(0.15))
