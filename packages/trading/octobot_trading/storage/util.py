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
#  License along with this library
import octobot_commons.constants as commons_constants
import octobot_commons.databases as databases
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.optimization_campaign as optimization_campaign
import octobot_trading.enums as enums
import octobot_trading.modes as modes
import octobot_trading.util


def get_run_databases_identifier(
    config: dict, tentacles_setup_config, trading_mode_class=None, enable_storage=True
) -> databases.RunDatabasesIdentifier:
    trading_mode = commons_constants.DEFAULT_STORAGE_TRADING_MODE
    try:
        trading_mode = trading_mode_class or modes.get_activated_trading_mode(tentacles_setup_config)
    except commons_errors.ConfigTradingError:
        # use default value
        pass
    return databases.RunDatabasesIdentifier(
        trading_mode,
        optimization_campaign.OptimizationCampaign.get_campaign_name(tentacles_setup_config),
        backtesting_id=config.get(commons_constants.CONFIG_BACKTESTING_ID),
        optimizer_id=config.get(commons_constants.CONFIG_OPTIMIZER_ID),
        live_id=octobot_trading.util.get_current_bot_live_id(config),
        enable_storage=enable_storage
    )




def get_account_type_suffix_from_exchange_manager(exchange_manager) -> str:
    return get_account_type_suffix(
        exchange_manager.is_future,
        exchange_manager.is_margin,
        exchange_manager.is_option,
        exchange_manager.is_sandboxed,
        exchange_manager.is_trader_simulated
    )


def get_account_type_suffix_from_run_metadata(run_metadata) -> str:
    trading_type = run_metadata[commons_enums.DBRows.TRADING_TYPE.value]
    trader_simulator = True  # todo: update when displaying live data in strat designer
    is_sandboxed = False  # todo: update when displaying live data in strat designer
    return get_account_type_suffix(
        trading_type == enums.ExchangeTypes.FUTURE.value,
        trading_type == enums.ExchangeTypes.MARGIN.value,
        trading_type == enums.ExchangeTypes.OPTION.value,
        is_sandboxed,
        trader_simulator
    )


def get_account_type_suffix(is_future, is_margin, is_option, is_sandboxed, is_trader_simulated) -> str:
    suffix = ""
    if is_future:
        suffix = f"{suffix}_{commons_constants.CONFIG_EXCHANGE_FUTURE}"
    elif is_margin:
        suffix = f"{suffix}_{commons_constants.CONFIG_EXCHANGE_MARGIN}"
    elif is_option:
        suffix = f"{suffix}_{commons_constants.CONFIG_EXCHANGE_OPTION}"
    else:
        suffix = f"{suffix}_{commons_constants.CONFIG_EXCHANGE_SPOT}"
    if is_sandboxed:
        suffix = f"{suffix}_{commons_constants.CONFIG_EXCHANGE_SANDBOXED}"
    if is_trader_simulated:
        suffix = f"{suffix}_{commons_constants.CONFIG_SIMULATOR}"
    return suffix
