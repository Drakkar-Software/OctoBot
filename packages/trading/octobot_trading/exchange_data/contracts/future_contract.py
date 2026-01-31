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
import octobot_commons.logging as logging

import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.errors as errors

import octobot_trading.exchange_data.contracts.margin_contract as margin_contract


class FutureContract(margin_contract.MarginContract):
    def __init__(self, pair, margin_type, 
                 contract_type: enums.FutureContractType,
                 contract_size=constants.ONE,
                 maximum_leverage=constants.ONE,
                 current_leverage=constants.ONE,
                 position_mode=enums.PositionMode.ONE_WAY,
                 maintenance_margin_rate=constants.DEFAULT_SYMBOL_MAINTENANCE_MARGIN_RATE,
                 minimum_tick_size=0.5,
                 take_profit_stop_loss_mode=None):
        super().__init__(pair, margin_type=margin_type, contract_size=contract_size,
                         maximum_leverage=maximum_leverage, current_leverage=current_leverage)
        self.contract_type = contract_type
        self.minimum_tick_size = minimum_tick_size
        self.position_mode = position_mode
        self.maintenance_margin_rate = maintenance_margin_rate

        # None when unsupported by exchange
        self.take_profit_stop_loss_mode = take_profit_stop_loss_mode

    def __str__(self):
        if self.is_handled_contract():
            return (f"{self.pair} "
                    f"{'inverse' if self.is_inverse_contract() else 'linear'} "
                    f"{'perpetual' if self.is_perpetual_contract() else 'future'} "
                    f"{self.margin_type.value} x{self.current_leverage}")
        return (f"{self.pair} "
                f"unhandled contract "
                f"{self.margin_type.value if self.margin_type else 'unknown margin type'} "
                f"x{self.current_leverage}")

    def is_inverse_contract(self):
        """
        Inverse Contract is a contract using the coin itself as collateral
        if not inverted the contract uses fiat as the collateral
        :return: True if the contract is an inverse contract
        """
        return self.contract_type in [enums.FutureContractType.INVERSE_EXPIRABLE,
                                      enums.FutureContractType.INVERSE_PERPETUAL]

    def get_fees_currency_side(self):
        """
        :return: the force side to take fees from (ex: pay fees only in USDT on BTC/BTC positions)
        """
        return enums.FeesCurrencySide.CURRENCY if self.is_inverse_contract() else enums.FeesCurrencySide.MARKET

    def is_perpetual_contract(self):
        """
        Perpetual Contract is a contract without an expiry date
        :return: True if the contract is a perpetual contract
        """
        return self.contract_type in [enums.FutureContractType.LINEAR_PERPETUAL,
                                      enums.FutureContractType.INVERSE_PERPETUAL]

    def is_one_way_position_mode(self):
        """
        :return: True if the contract position_mode is equals to PositionMode's ONE_WAY
        """
        return self.position_mode is enums.PositionMode.ONE_WAY

    def set_position_mode(self, is_one_way=True, is_hedge=False):
        """
        Set the contract position mode
        :param is_one_way: should be True if the position mode is one way
        :param is_hedge: should be True if the position mode is hedge
        """
        self.position_mode = enums.PositionMode.ONE_WAY if is_one_way and not is_hedge else enums.PositionMode.HEDGE

    def set_take_profit_stop_loss_mode(self, take_profit_stop_loss_mode):
        self.take_profit_stop_loss_mode = take_profit_stop_loss_mode

    def is_handled_contract(self):
        # unhandled / unknown contracts have None in self.contract_type
        return self.contract_type is not None

    def ensure_supported_configuration(self):
        """
        will raise on unsupported configuration
        """
        if not self.is_one_way_position_mode():
            raise errors.UnsupportedHedgeContractError(
                f"{self.position_mode.value} position mode ({self.pair}) is not supported"
            )

    def update_from_position(self, raw_position) -> bool:
        changed = super().update_from_position(raw_position)
        leverage = raw_position.get(enums.ExchangeConstantsPositionColumns.LEVERAGE.value, None)
        if leverage is not None and self.current_leverage != leverage:
            self.set_current_leverage(leverage)
            logging.get_logger(str(self)).debug(f"Changed leverage to {self.current_leverage}")
            changed = True
        pos_mode = raw_position.get(enums.ExchangeConstantsPositionColumns.POSITION_MODE.value, None)
        if pos_mode is not None and self.position_mode != pos_mode:
            self.set_position_mode(
                is_one_way=pos_mode is enums.PositionMode.ONE_WAY,
                is_hedge=pos_mode is enums.PositionMode.HEDGE
            )
            logging.get_logger(str(self)).debug(f"Changed position mode to {pos_mode}")
            changed = True
        return changed

    def to_dict(self):
        return {
            **super().to_dict(),
            **{
                enums.ExchangeConstantsFutureContractColumns.CONTRACT_TYPE.value:
                    self.contract_type.value if self.contract_type else self.contract_type,
                enums.ExchangeConstantsFutureContractColumns.MINIMUM_TICK_SIZE.value: self.minimum_tick_size,
                enums.ExchangeConstantsFutureContractColumns.POSITION_MODE.value:
                    self.position_mode.value if self.position_mode else self.position_mode,
                enums.ExchangeConstantsFutureContractColumns.MAINTENANCE_MARGIN_RATE.value:
                    self.maintenance_margin_rate,
                enums.ExchangeConstantsFutureContractColumns.TAKE_PROFIT_STOP_LOSS_MODE.value:
                    self.take_profit_stop_loss_mode,
            }
        }
