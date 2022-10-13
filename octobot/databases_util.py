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
import octobot_trading.api as trading_api
import octobot_commons.databases as databases
import octobot_commons.optimization_campaign as optimization_campaign
import octobot_commons.constants as commons_constants


def get_run_databases_identifier(config, tentacles_setup_config, trading_mode_class=None, enable_storage=True):
    return databases.RunDatabasesIdentifier(
        trading_mode_class or trading_api.get_activated_trading_mode(tentacles_setup_config),
        optimization_campaign.OptimizationCampaign.get_campaign_name(tentacles_setup_config),
        backtesting_id=config.get(commons_constants.CONFIG_BACKTESTING_ID),
        optimizer_id=config.get(commons_constants.CONFIG_OPTIMIZER_ID),
        live_id=trading_api.get_current_bot_live_id(config),
        enable_storage=enable_storage
    )
