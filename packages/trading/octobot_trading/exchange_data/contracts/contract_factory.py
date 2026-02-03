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
import octobot_commons.symbols as symbols_util

import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.exchange_data.contracts.contract as contract_module
import octobot_trading.exchange_data.contracts.margin_contract as margin_contract
import octobot_trading.exchange_data.contracts.future_contract as future_contract
import octobot_trading.exchange_data.contracts.option_contract as option_contract


def update_contracts_from_positions(exchange_manager, positions) -> bool:
    updated = False
    for position in positions:
        pair = position.get(enums.ExchangeConstantsPositionColumns.SYMBOL.value, None)
        if pair and pair not in exchange_manager.exchange.pair_contracts:
            contract = exchange_manager.exchange.create_pair_contract(
                pair=pair,
                current_leverage=position.get(
                    enums.ExchangeConstantsPositionColumns.LEVERAGE.value, constants.ZERO),
                contract_size=position.get(
                    enums.ExchangeConstantsPositionColumns.CONTRACT_SIZE.value, constants.DEFAULT_SYMBOL_CONTRACT_SIZE),
                margin_type=position.get(enums.ExchangeConstantsPositionColumns.MARGIN_TYPE.value, None),
                contract_type=position.get(enums.ExchangeConstantsPositionColumns.CONTRACT_TYPE.value, None),
                position_mode=position.get(enums.ExchangeConstantsPositionColumns.POSITION_MODE.value, None),
                maintenance_margin_rate=position.get(
                    enums.ExchangeConstantsPositionColumns.MAINTENANCE_MARGIN_RATE.value,
                    constants.DEFAULT_SYMBOL_MAINTENANCE_MARGIN_RATE)
            )
            # contracts are updated from positions are fully initialized
            if contract.is_handled_contract():
                updated = True
            else:
                message = f"Unhandled contract {contract}. This contract can't be traded"
                if pair in exchange_manager.exchange_config.traded_symbol_pairs:
                    # inform user that the contract can't be used
                    _get_logger().error(message)
                else:
                    # no need to inform as the contract is not requested
                    _get_logger().debug(message)
    return updated


def update_future_contract_from_dict(exchange_manager, contract: dict) -> bool:
    return exchange_manager.exchange.create_pair_contract(
        pair=contract[enums.ExchangeConstantsMarginContractColumns.PAIR.value],
        current_leverage=decimal.Decimal(str(
            contract[enums.ExchangeConstantsMarginContractColumns.CURRENT_LEVERAGE.value]
        )),
        contract_size=decimal.Decimal(str(
            contract[enums.ExchangeConstantsMarginContractColumns.CONTRACT_SIZE.value]
        )),
        margin_type=enums.MarginType(contract[enums.ExchangeConstantsMarginContractColumns.MARGIN_TYPE.value]),
        contract_type=enums.FutureContractType(contract[enums.ExchangeConstantsFutureContractColumns.CONTRACT_TYPE.value]),
        position_mode=enums.PositionMode(contract[enums.ExchangeConstantsFutureContractColumns.POSITION_MODE.value])
            if contract[enums.ExchangeConstantsFutureContractColumns.POSITION_MODE.value]
            else contract[enums.ExchangeConstantsFutureContractColumns.POSITION_MODE.value],
        maintenance_margin_rate=decimal.Decimal(str(
            contract[enums.ExchangeConstantsFutureContractColumns.MAINTENANCE_MARGIN_RATE.value]
        )),
        maximum_leverage=None if contract[enums.ExchangeConstantsMarginContractColumns.MAXIMUM_LEVERAGE.value] is None
            else decimal.Decimal(str(
                contract[enums.ExchangeConstantsMarginContractColumns.MAXIMUM_LEVERAGE.value]
            ))
    )


def create_default_future_contract(
    pair: str, leverage: decimal.Decimal, contract_type: enums.FutureContractType, position_mode: enums.PositionMode
) -> future_contract.FutureContract:
    return future_contract.FutureContract(
        pair=pair,
        contract_size=constants.DEFAULT_SYMBOL_CONTRACT_SIZE,
        margin_type=constants.DEFAULT_SYMBOL_MARGIN_TYPE,
        contract_type=contract_type,
        maximum_leverage=constants.DEFAULT_SYMBOL_MAX_LEVERAGE,
        current_leverage=leverage,
        position_mode=position_mode,
        maintenance_margin_rate=constants.DEFAULT_SYMBOL_MAINTENANCE_MARGIN_RATE
    )


def create_default_option_contract(
    pair: str, leverage: decimal.Decimal, contract_type: enums.OptionContractType, position_mode: enums.PositionMode
) -> option_contract.OptionContract:
    return option_contract.OptionContract(
        pair=pair,
        contract_size=constants.DEFAULT_SYMBOL_CONTRACT_SIZE,
        margin_type=constants.DEFAULT_SYMBOL_MARGIN_TYPE,
        contract_type=contract_type,
        maximum_leverage=constants.DEFAULT_SYMBOL_MAX_LEVERAGE,
        current_leverage=leverage,
        position_mode=position_mode,
        maintenance_margin_rate=constants.DEFAULT_SYMBOL_MAINTENANCE_MARGIN_RATE
    )

def create_contract(
    pair: str, 
    current_leverage: decimal.Decimal, 
    contract_size: decimal.Decimal, 
    margin_type: enums.MarginType, 
    contract_type: enums.FutureContractType | enums.OptionContractType, 
    position_mode: enums.PositionMode, 
    maintenance_margin_rate: decimal.Decimal, 
    maximum_leverage: decimal.Decimal = constants.DEFAULT_SYMBOL_MAX_LEVERAGE
) -> contract_module.Contract:
    symbol = symbols_util.parse_symbol(pair)
    if symbol.is_option():
        return option_contract.OptionContract(
            pair=pair,
            contract_size=contract_size,
            margin_type=margin_type,
            contract_type=contract_type,
            maximum_leverage=maximum_leverage,
            current_leverage=current_leverage,
            position_mode=position_mode,
            maintenance_margin_rate=maintenance_margin_rate
        )
    if symbol.is_future():
        return future_contract.FutureContract(
            pair=pair,
            contract_size=contract_size,
            margin_type=margin_type,
            contract_type=contract_type,
            maximum_leverage=maximum_leverage,
            current_leverage=current_leverage,
            position_mode=position_mode,
            maintenance_margin_rate=maintenance_margin_rate
        )
    if not symbol.is_spot():
        return margin_contract.MarginContract(
            pair=pair,
            margin_type=margin_type,
            contract_size=contract_size,
            maximum_leverage=maximum_leverage,
            current_leverage=current_leverage
        )
    raise ValueError(f"Invalid contract for symbol: {symbol}")

def get_contract_type_from_symbol(symbol: str, is_linear: bool, is_inverse: bool) -> enums.FutureContractType | enums.OptionContractType:
    parsed_symbol = symbols_util.parse_symbol(symbol)
    if is_linear:
        if parsed_symbol.does_expire():
            if parsed_symbol.is_future():
                return enums.FutureContractType.LINEAR_EXPIRABLE
            return enums.OptionContractType.LINEAR_EXPIRABLE
        return enums.FutureContractType.LINEAR_PERPETUAL
    if is_inverse:
        if parsed_symbol.does_expire():
            if parsed_symbol.is_future():
                return enums.FutureContractType.INVERSE_EXPIRABLE
            return enums.OptionContractType.INVERSE_EXPIRABLE
        return enums.FutureContractType.INVERSE_PERPETUAL
    raise ValueError(f"Invalid contract for symbol: {symbol}")

def _get_logger():
    return logging.get_logger("contract_factory")
