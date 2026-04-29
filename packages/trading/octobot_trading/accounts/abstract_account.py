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

import octobot_commons.tentacles_management as tentacles_management


class AbstractAccount(tentacles_management.AbstractTentacle):
    """
    Defines interactions with an account, which can be 
    an exchange account or a blockchain wallet
    """

    async def get_balance(self, **kwargs: dict) -> dict:
        """
        :return: current user balance from this account
        """
        raise NotImplementedError("get_balance is not implemented")


    async def withdraw(
        self, 
        asset: str, 
        amount: decimal.Decimal, 
        network: str,
        address: str, 
    ) -> dict:
        """
        Withdraw funds from this account
        :param asset: the asset to withdraw
        :param amount: the amount to withdraw
        :param network: the network to withdraw to
        :param address: the address to withdraw to
        """
        raise NotImplementedError("withdraw is not implemented")


    async def get_deposit_address(self, asset: str, params: dict = None) -> dict:
        """
        Get the deposit address for the given asset
        :param asset: the asset to get the deposit address for
        :param params: the parameters for the deposit address request
        """
        raise NotImplementedError("get_deposit_address is not implemented")
