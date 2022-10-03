#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants
import octobot_commons.databases as commons_databases
import octobot_commons.configuration as commons_configuration

import octobot_backtesting.api as backtesting_api

import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums


async def clear_run_metadata(bot_id):
    run_db = commons_databases.RunDatabasesProvider.instance().get_run_db(bot_id)
    await run_db.delete(common_enums.DBTables.METADATA.value, None)


async def store_run_metadata(bot_id, exchange_managers, start_time, user_inputs=None) -> dict:
    run_db = commons_databases.RunDatabasesProvider.instance().get_run_db(bot_id)
    user_inputs = user_inputs or await commons_configuration.get_user_inputs(run_db)
    run_dbs_identifier = commons_databases.RunDatabasesProvider.instance().get_run_databases_identifier(bot_id)
    metadata = await _get_trading_metadata(exchange_managers, start_time, user_inputs, run_dbs_identifier, False)
    await run_db.log(
        common_enums.DBTables.METADATA.value,
        metadata
    )
    return metadata


async def store_backtesting_run_metadata(exchange_managers, start_time, user_inputs, run_dbs_identifier) -> dict:
    run_metadata = await _get_trading_metadata(exchange_managers, start_time, user_inputs, run_dbs_identifier, True)

    # use local database as a lock is required
    async with commons_databases.DBWriter.database(
         run_dbs_identifier.get_backtesting_metadata_identifier(),
         with_lock=True) as writer:
        await writer.log(common_enums.DBTables.METADATA.value, run_metadata)
    return run_metadata


async def _get_trading_metadata(exchange_managers, run_start_time, user_inputs, run_dbs_identifier, is_backtesting) \
        -> dict:
    # todo handle multiple exchanges metadata
    exchange_manager = exchange_managers[0]
    trading_mode = trading_api.get_trading_modes(exchange_manager)[0]
    symbols = exchange_manager.exchange_config.traded_symbol_pairs
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager.portfolio_profitability
    profitability = portfolio_manager.profitability
    profitability_percent = portfolio_manager.profitability_percent
    if user_inputs is None:
        user_inputs = {}
    origin_portfolio = trading_api.get_origin_portfolio(exchange_manager, as_decimal=False)
    end_portfolio = trading_api.get_portfolio(exchange_manager, as_decimal=False)
    for portfolio in (origin_portfolio, end_portfolio):
        for values in portfolio.values():
            values.pop("available", None)
    if exchange_manager.is_future:
        for position in trading_api.get_positions(exchange_manager):
            end_portfolio[position.get_currency()]["position"] = float(position.quantity)
    time_frames = [
        tf.value
        for tf in trading_api.get_relevant_time_frames(exchange_manager)
    ]
    start_time = backtesting_api.get_backtesting_starting_time(exchange_manager.exchange.backtesting) \
        if exchange_manager.is_backtesting \
        else exchange_manager.exchange.get_exchange_current_time()
    end_time = backtesting_api.get_backtesting_ending_time(exchange_manager.exchange.backtesting) \
        if exchange_manager.is_backtesting \
        else -1
    exchange_type = "spot"
    exchange_names = [
        exchange
        for exchange, config in exchange_manager.config[common_constants.CONFIG_EXCHANGES].items()
        if config.get(common_constants.CONFIG_ENABLED_OPTION, True)
    ]
    future_contracts_by_exchange = {}
    if exchange_manager.is_future and hasattr(exchange_manager.exchange, "pair_contracts"):
        exchange_type = "future"
        future_contracts_by_exchange = {
            exchange_manager.exchange_name: {
                symbol: {
                    "contract_type": contract.contract_type.value,
                    "position_mode": contract.position_mode.value,
                    "margin_type": contract.margin_type.value
                }
                for symbol, contract in trading_api.get_pair_contracts(exchange_manager).items()
                if symbol in trading_api.get_trading_pairs(exchange_manager)
            }
        }
    formatted_user_inputs = {}
    for user_input in user_inputs:
        if not user_input["is_nested_config"]:
            try:
                formatted_user_inputs[user_input["tentacle"]][user_input["name"]] = user_input["value"]
            except KeyError:
                formatted_user_inputs[user_input["tentacle"]] = {
                    user_input["name"]: user_input["value"]
                }
    leverage = 0
    if exchange_manager.is_future and hasattr(exchange_manager.exchange, "get_pair_future_contract"):
        leverage = float(trading_api.get_pair_contracts(exchange_manager)[symbols[0]].current_leverage)
    trades = [
        trade
        for trade in trading_api.get_trade_history(exchange_manager, include_cancelled=False)
    ]
    entries = [
        trade
        for trade in trades
        if trade.status is trading_enums.OrderStatus.FILLED and trade.side is trading_enums.TradeOrderSide.BUY
    ]
    win_rate = round(float(trading_api.get_win_rate(exchange_manager) * 100), 3)
    wins = round(win_rate * len(entries) / 100)
    draw_down = round(float(trading_api.get_draw_down(exchange_manager)), 3)
    try:
        r_sq_end_balance = await trading_api.get_coefficient_of_determination(
            exchange_manager,
            use_high_instead_of_end_balance=False
        )
    except KeyError:
        r_sq_end_balance = None
    try:
        r_sq_max_balance = await trading_api.get_coefficient_of_determination(exchange_manager)
    except KeyError:
        r_sq_max_balance = None

    backtesting_only_metadata = {
        common_enums.BacktestingMetadata.ID.value: run_dbs_identifier.backtesting_id,
        common_enums.BacktestingMetadata.OPTIMIZATION_CAMPAIGN.value: run_dbs_identifier.optimization_campaign_name,
        common_enums.BacktestingMetadata.DURATION.value: round(backtesting_api.get_backtesting_duration(
            exchange_manager.exchange.backtesting), 3),
        common_enums.BacktestingMetadata.BACKTESTING_FILES.value:
            exchange_manager.exchange.get_backtesting_data_files(),
        common_enums.BacktestingMetadata.USER_INPUTS.value: formatted_user_inputs,
    } if is_backtesting else {}
    return {
        **backtesting_only_metadata,
        **{
            common_enums.BacktestingMetadata.GAINS.value: round(float(profitability), 8),
            common_enums.BacktestingMetadata.PERCENT_GAINS.value: round(float(profitability_percent), 3),
            common_enums.BacktestingMetadata.END_PORTFOLIO.value: str(end_portfolio),
            common_enums.BacktestingMetadata.START_PORTFOLIO.value: str(origin_portfolio),
            common_enums.BacktestingMetadata.WIN_RATE.value: win_rate,
            common_enums.BacktestingMetadata.DRAW_DOWN.value: draw_down or 0,
            common_enums.BacktestingMetadata.COEFFICIENT_OF_DETERMINATION_MAX_BALANCE.value: r_sq_max_balance or 0,
            common_enums.BacktestingMetadata.COEFFICIENT_OF_DETERMINATION_END_BALANCE.value: r_sq_end_balance or 0,
            common_enums.BacktestingMetadata.SYMBOLS.value: symbols,
            common_enums.BacktestingMetadata.TIME_FRAMES.value: time_frames,
            common_enums.BacktestingMetadata.ENTRIES.value: len(entries),
            common_enums.BacktestingMetadata.WINS.value: wins,
            common_enums.BacktestingMetadata.LOSES.value: len(entries) - wins,
            common_enums.BacktestingMetadata.TRADES.value: len(trades),
            common_enums.BacktestingMetadata.TIMESTAMP.value: run_start_time,
            common_enums.BacktestingMetadata.NAME.value: trading_mode.get_name(),
            common_enums.BacktestingMetadata.LEVERAGE.value: leverage,
            common_enums.DBRows.TRADING_TYPE.value: exchange_type,
            common_enums.DBRows.EXCHANGES.value: exchange_names,
            common_enums.DBRows.REFERENCE_MARKET.value: trading_api.get_reference_market(exchange_manager.config),
            common_enums.DBRows.START_TIME.value: start_time,
            common_enums.DBRows.END_TIME.value: end_time,
            common_enums.DBRows.FUTURE_CONTRACTS.value: future_contracts_by_exchange,
        },
        **(await trading_mode.get_additional_metadata(is_backtesting))
    }
