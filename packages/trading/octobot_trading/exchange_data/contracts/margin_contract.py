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

import octobot_commons.logging as logging

import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.exchange_data.contracts.contract as contract


class MarginContract(contract.Contract):
    def __init__(self, pair, margin_type,
                 contract_size=constants.ONE,
                 maximum_leverage=constants.ONE,
                 current_leverage=constants.ONE):
        super().__init__(pair)
        self.pair: str = pair
        self.margin_type = margin_type

        self.contract_size: decimal.Decimal = contract_size
        self.maximum_leverage: decimal.Decimal = maximum_leverage
        self.current_leverage: decimal.Decimal = current_leverage

        self.risk_limit = {}

    def is_isolated(self):
        """
        Margin in isolated margin mode is independent for each trading pair
        Margin in cross margin mode is shared among the user’s margin account
        :return: True if the contract use isolation margin
        """
        return self.margin_type is enums.MarginType.ISOLATED

    def check_leverage_update(self, new_leverage):
        """
        Check if the new leverage value is matching requirements (0 < maximum_leverage)
        :param new_leverage: the leverage value to check
        :return: True if valid
        """
        dec_leverage = decimal.Decimal(str(new_leverage))
        return (
            constants.ZERO < dec_leverage
            if self.maximum_leverage is None
            else constants.ZERO < dec_leverage <= self.maximum_leverage
        )

    def set_current_leverage(self, new_leverage):
        """
        Set the contract current leverage value
        :param new_leverage: the new leverage value
        """
        if self.check_leverage_update(new_leverage):
            self.current_leverage = new_leverage

    def set_margin_type(self, is_isolated=True, is_cross=False):
        """
        Set the contract margin type
        :param is_isolated: should be True if the margin type is isolated
        :param is_cross: should be True if the margin type is cross
        """
        self.margin_type = enums.MarginType.ISOLATED if is_isolated and not is_cross else enums.MarginType.CROSS

    def is_handled_contract(self):
        """
        :return: False if this contract can't be traded in OctoBot
        """
        return True

    def ensure_supported_configuration(self):
        pass

    def update_from_position(self, raw_position) -> bool:
        changed = False
        margin_type = raw_position.get(enums.ExchangeConstantsPositionColumns.MARGIN_TYPE.value, None)
        if margin_type is not None and self.margin_type != margin_type:
            self.set_margin_type(
                is_isolated=margin_type is enums.MarginType.ISOLATED,
                is_cross=margin_type is enums.MarginType.CROSS
            )
            logging.get_logger(str(self)).debug(f"Changed margin type to {margin_type}")
            changed = True
        return changed

    def to_dict(self):
        return {
            enums.ExchangeConstantsMarginContractColumns.PAIR.value: self.pair,
            enums.ExchangeConstantsMarginContractColumns.MARGIN_TYPE.value: self.margin_type.value,
            enums.ExchangeConstantsMarginContractColumns.CONTRACT_SIZE.value: self.contract_size,
            enums.ExchangeConstantsMarginContractColumns.MAXIMUM_LEVERAGE.value: self.maximum_leverage,
            enums.ExchangeConstantsMarginContractColumns.CURRENT_LEVERAGE.value: self.current_leverage,
            enums.ExchangeConstantsMarginContractColumns.RISK_LIMIT.value: self.risk_limit,
        }
