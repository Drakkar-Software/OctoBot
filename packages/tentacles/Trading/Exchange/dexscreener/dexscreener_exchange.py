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

import octobot_commons.enums as commons_enums
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants


class dexscreener(exchanges.RestExchange):
    CHAIN_ID_KEY = "chainId"
    DEX_ID_KEY = "dexId"
    BASE_TOKEN_ADDRESSES_KEY = "baseTokenAddresses"
    QUOTE_TOKEN_ADDRESSES_KEY = "quoteTokenAddresses"

    @classmethod
    def get_name(cls):
        return "dexscreener"

    def get_additional_connector_config(self):
        tentacle_config = self.tentacle_config or {}
        return {
            ccxt_constants.CCXT_OPTIONS: {
                "chainId": tentacle_config.get(self.CHAIN_ID_KEY),
                "dexId": tentacle_config.get(self.DEX_ID_KEY),
                "baseTokenAddresses": tentacle_config.get(self.BASE_TOKEN_ADDRESSES_KEY) or [],
                "quoteTokenAddresses": tentacle_config.get(self.QUOTE_TOKEN_ADDRESSES_KEY) or [],
            },
        }

    @classmethod
    def init_user_inputs_from_class(cls, inputs: dict) -> None:
        """
        Called at constructor, should define all the exchange's user inputs.
        """
        cls.CLASS_UI.user_input(
            cls.CHAIN_ID_KEY, commons_enums.UserInputTypes.TEXT, "", inputs,
            title=f"Chain ID from dexscreener to use for the exchange. Used to filter tokens. ex: solana, ethereum, base, bsc, polygon, etc."
        )
        cls.CLASS_UI.user_input(
            cls.DEX_ID_KEY, commons_enums.UserInputTypes.TEXT, "", inputs,
            title=f"DEX ID from dexscreener to use for the exchange. Used to filter tokens. ex: uniswap, curve, balancer, pancakeswap, pumpswap, pumpfun, meteora, raydium, etc."
        )
        cls.CLASS_UI.user_input(
            cls.BASE_TOKEN_ADDRESSES_KEY, commons_enums.UserInputTypes.STRING_ARRAY, [], inputs,
            title=f"Base token addresses from dexscreener to use for the exchange. Used to filter tokens. ex: 0x514910771AF9Ca656af840dff83E8264EcF986CA for LINK on ETH."
        )
        cls.CLASS_UI.user_input(
            cls.QUOTE_TOKEN_ADDRESSES_KEY, commons_enums.UserInputTypes.STRING_ARRAY, [], inputs,
            title=f"Quote token addresses from dexscreener to use for the exchange. Used to filter tokens. ex: 0xD6DF932A45C0f255f85145f286eA0b292B21C90B for Aave (PoS) on Polygon."
        )

    @classmethod
    def is_configurable(cls):
        return True
