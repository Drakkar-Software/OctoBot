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

import os

import octobot_trading.exchanges as exchanges


class alchemy(exchanges.RestExchange):

    @classmethod
    def get_name(cls):
        return "alchemy"

    def get_additional_connector_config(self):
        if api_key := os.getenv("ALCHEMY_API_KEY"):
            return {
                "apiKey": api_key,
            }
        return {}
