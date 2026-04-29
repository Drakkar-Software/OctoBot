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
import octobot_commons.databases as databases
import octobot_commons.errors as commons_errors
import octobot_commons.enums as commons_enums
import tentacles.Meta.Keywords.scripting_library.data as data


def set_script_name(ctx, name):
    ctx.tentacle.script_name = name


async def _read_backtesting_metadata(optimizer_run_dbs_identifier, metadata_list, optimizer_id):
    async with data.MetadataReader.database(optimizer_run_dbs_identifier.get_backtesting_metadata_identifier()) \
            as reader:
        try:
            metadata = await reader.read()
            for metadata_element in metadata:
                metadata_element[commons_enums.BacktestingMetadata.OPTIMIZER_ID.value] = optimizer_id
            metadata_list += metadata
        except commons_errors.DatabaseNotFoundError:
            pass


async def read_metadata(runs_to_load_settings, trading_mode, include_optimizer_runs=False):
    metadata = []
    optimizer_run_dbs_identifiers = []
    run_dbs_identifier = databases.RunDatabasesIdentifier(trading_mode)
    try:
        campaigns_to_load = runs_to_load_settings["campaigns"]
    except KeyError:
        campaigns_to_load = runs_to_load_settings["campaigns"] = {}
    available_campaigns = await run_dbs_identifier.get_optimization_campaign_names()
    campaigns = {}
    for optimization_campaign_name in available_campaigns:
        if optimization_campaign_name in campaigns_to_load:
            if campaigns_to_load[optimization_campaign_name]:
                campaigns[optimization_campaign_name] = True
            else:
                campaigns[optimization_campaign_name] = False
                continue
        else:
            campaigns[optimization_campaign_name] = True

        backtesting_run_dbs_identifier = databases.RunDatabasesIdentifier(trading_mode, optimization_campaign_name,
                                                                          backtesting_id="1")
        if include_optimizer_runs:
            optimizer_ids = await backtesting_run_dbs_identifier.get_optimizer_run_ids()
            if optimizer_ids:
                optimizer_run_dbs_identifiers = [
                    databases.RunDatabasesIdentifier(trading_mode, optimization_campaign_name,
                                                     optimizer_id=optimizer_id)
                    for optimizer_id in optimizer_ids]
        try:
            await _read_backtesting_metadata(backtesting_run_dbs_identifier, metadata, 0)
        except commons_errors.DatabaseNotFoundError:
            pass
        for optimizer_run_dbs_identifier in optimizer_run_dbs_identifiers:
            await _read_backtesting_metadata(optimizer_run_dbs_identifier, metadata,
                                             optimizer_run_dbs_identifier.optimizer_id)
    return campaigns, metadata


async def _read_bot_recording_metadata(run_dbs_identifier, metadata_list):
    async with data.MetadataReader.database(run_dbs_identifier.get_bot_live_metadata_identifier()) \
            as reader:
        try:
            metadata = await reader.read()
            metadata_list += metadata
        except commons_errors.DatabaseNotFoundError:
            pass


async def read_bot_recording_runs_metadata(trading_mode):
    metadata = []
    run_dbs_identifier = databases.RunDatabasesIdentifier(trading_mode)
    try:
        await _read_bot_recording_metadata(run_dbs_identifier, metadata)
    except commons_errors.DatabaseNotFoundError:
        pass
    return metadata
