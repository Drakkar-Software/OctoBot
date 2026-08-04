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
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges
from octobot_trading.enums import ExchangeConstantsOrderColumns as ecoc


class CoinRabbit(exchanges.RestExchange):
    @classmethod
    def get_name(cls):
        return "coinrabbit"

    def get_adapter_class(self):
        return CoinRabbitCCXTAdapter

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        return [
            trading_enums.ExchangeTypes.SPOT,
        ]


class CoinRabbitCCXTAdapter(exchanges.CCXTAdapter):
    def fix_order(self, raw, **kwargs):
        fixed = super().fix_order(raw, **kwargs)
        if self._is_buy_market_without_price(fixed):
            self.logger.error(
                "CoinRabbit buy market order parsed without price; "
                "amount is quote cost (USDT), not base quantity: %s",
                fixed,
            )
        return fixed

    def _is_buy_market_without_price(self, fixed: dict) -> bool:
        if fixed.get(ecoc.TYPE.value) != trading_enums.TradeOrderType.MARKET.value:
            return False
        if fixed.get(ecoc.SIDE.value) != trading_enums.TradeOrderSide.BUY.value:
            return False
        return not self._has_usable_price(fixed)

    def _has_usable_price(self, fixed: dict) -> bool:
        for price_key in (ecoc.PRICE.value, ecoc.AVERAGE.value):
            price = fixed.get(price_key)
            if price is None:
                continue
            try:
                if float(price) > 0:
                    return True
            except (TypeError, ValueError):
                continue
        return False
