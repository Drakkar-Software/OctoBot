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
import octobot_trading.enums as enums
import octobot_trading.constants as constants

import octobot_trading.exchange_data.contracts.future_contract as future_contract


class OptionContract(future_contract.FutureContract):
    def __init__(self, pair, margin_type, 
                 contract_type: enums.OptionContractType,
                 contract_size=constants.ONE,
                 maximum_leverage=constants.ONE,
                 current_leverage=constants.ONE,
                 position_mode=enums.PositionMode.ONE_WAY,
                 maintenance_margin_rate=constants.DEFAULT_SYMBOL_MAINTENANCE_MARGIN_RATE,
                 minimum_tick_size=0.5,
                 take_profit_stop_loss_mode=None):
        super().__init__(pair, margin_type=margin_type, contract_type=contract_type, contract_size=contract_size, maximum_leverage=maximum_leverage, current_leverage=current_leverage, position_mode=position_mode, maintenance_margin_rate=maintenance_margin_rate, minimum_tick_size=minimum_tick_size, take_profit_stop_loss_mode=take_profit_stop_loss_mode)

    def is_inverse_contract(self):
        """
        Inverse Contract is a contract using the coin itself as collateral
        if not inverted the contract uses fiat as the collateral
        :return: True if the contract is an inverse contract
        """
        return self.contract_type in [enums.OptionContractType.INVERSE_EXPIRABLE]
