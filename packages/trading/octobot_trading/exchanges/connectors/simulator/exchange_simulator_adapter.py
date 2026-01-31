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

import octobot_trading.exchanges.adapters as adapters


class ExchangeSimulatorAdapter(adapters.AbstractAdapter):

    def __init__(self, connector):
        super().__init__(connector)
        self._tentacle_adapter_proxy = None

    def _get_tentacle_adapter_proxy(self):
        if self._tentacle_adapter_proxy is None:
            return self
        return self._tentacle_adapter_proxy

    def set_tentacles_adapter_proxy(self, adapter_class):
        self._tentacle_adapter_proxy = adapter_class(self.connector)

    def adapt_market_status(self, raw, remove_price_limits=False, **kwargs):
        return self._get_tentacle_adapter_proxy().adapt_market_status(
            raw, remove_price_limits=remove_price_limits, **kwargs
        )
