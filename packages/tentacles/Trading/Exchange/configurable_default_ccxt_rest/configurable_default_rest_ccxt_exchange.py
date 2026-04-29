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
import octobot_trading.exchanges as exchanges


class ConfigurableDefaultCCXTRestExchange(exchanges.DefaultRestExchange):

    @classmethod
    def load_user_inputs_from_class(cls, tentacles_setup_config, tentacle_config):
        # bypass parent to use the real load_user_inputs and enable user inputs configuration
        return exchanges.RestExchange.load_user_inputs_from_class(tentacles_setup_config, tentacle_config)
