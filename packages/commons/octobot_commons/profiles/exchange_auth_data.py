# pylint: disable=C0103,R0902
#  Drakkar-Software OctoBot-Commons
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
import dataclasses

import octobot_commons.dataclasses
import octobot_commons.constants


@dataclasses.dataclass
class ExchangeAuthData(octobot_commons.dataclasses.FlexibleDataclass):
    internal_name: str
    exchange_credential_id: str = ""
    encrypted: str = ""
    api_key: str = ""
    api_secret: str = ""
    api_password: str = ""
    exchange_type: str = octobot_commons.constants.DEFAULT_EXCHANGE_TYPE
    sandboxed: bool = False

    def apply_to_exchange_config(self, config):
        """
        Updates the given Configuration object to use the local authentication data
        :param config: Configuration object to update
        """
        applied = False
        for exchange, exchange_config in config.config[
            octobot_commons.constants.CONFIG_EXCHANGES
        ].items():
            if exchange == self.internal_name:
                self._apply_config(exchange_config)
                applied = True
                break
        if not applied:
            # exchange doesn't already exist: add it
            exchange_config = {octobot_commons.constants.CONFIG_ENABLED_OPTION: True}
            self._apply_config(exchange_config)
            config.config[octobot_commons.constants.CONFIG_EXCHANGES][
                self.internal_name
            ] = exchange_config

    def _apply_config(self, exchange_config: dict):
        exchange_config[octobot_commons.constants.CONFIG_EXCHANGE_KEY] = self.api_key
        exchange_config[octobot_commons.constants.CONFIG_EXCHANGE_SECRET] = (
            self.api_secret
        )
        exchange_config[octobot_commons.constants.CONFIG_EXCHANGE_PASSWORD] = (
            self.api_password
        )
        exchange_config[octobot_commons.constants.CONFIG_EXCHANGE_SANDBOXED] = (
            self.sandboxed
        )
        exchange_config[octobot_commons.constants.CONFIG_EXCHANGE_TYPE] = (
            self.exchange_type
        )
