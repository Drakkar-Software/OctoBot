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
import typing

import octobot_trading.exchanges as exchanges
import octobot_trading.errors
import octobot_trading.enums as trading_enums


class Kraken(exchanges.RestExchange):

    def __init__(
        self, config, exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]],
        connector_class=None
    ):
        super().__init__(config, exchange_manager, exchange_config_by_exchange, connector_class=connector_class)
        self.logger.error("Kraken is not providing free and used data for account balance. "
                          "OctoBot wont be able to manage a real portfolio correctly.")

    @classmethod
    def get_name(cls):
        return 'kraken'
