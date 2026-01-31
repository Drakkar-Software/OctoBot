#  Drakkar-Software OctoBot-Evaluators
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
import octobot_commons.enums as enums
import octobot_commons.constants as constants
import octobot_commons.databases as databases
import octobot_commons.time_frame_manager as time_frame_manager
import octobot_tentacles_manager.api as tentacles_manager_api


def get_eval_time(full_candle=None, time_frame=None, partial_candle=None, kline=None):
    if full_candle is not None and time_frame is not None:
        # add one full time frame seconds since a full candle is available when the next has started
        return full_candle[enums.PriceIndexes.IND_PRICE_TIME.value] + \
               enums.TimeFramesMinutes[enums.TimeFrames(time_frame)] * constants.MINUTE_TO_SECONDS
    if partial_candle is not None:
        return partial_candle[enums.PriceIndexes.IND_PRICE_TIME.value]
    if kline is not None:
        return kline[enums.PriceIndexes.IND_PRICE_TIME.value]
    raise ValueError("Invalid arguments")


def get_shortest_time_frame(ideal_time_frame, preferred_available_time_frames, others):
    if ideal_time_frame in preferred_available_time_frames:
        return ideal_time_frame
    if preferred_available_time_frames:
        return time_frame_manager.sort_time_frames(preferred_available_time_frames)[0]
    else:
        return time_frame_manager.sort_time_frames(others)[0]


def local_trading_context(evaluator, symbol, time_frame, trigger_cache_timestamp,
                          cryptocurrency=None, exchange=None, exchange_id=None,
                          trigger_source=None, trigger_value=None):
    try:
        import octobot_trading.api as exchange_api
        import octobot_trading.modes as modes
        exchange_manager = exchange_api.get_exchange_manager_from_exchange_name_and_id(
            exchange or evaluator.exchange_name,
            exchange_id or exchange_api.get_exchange_id_from_matrix_id(evaluator.exchange_name, evaluator.matrix_id)
        )
        trading_modes = exchange_api.get_trading_modes(exchange_manager)
        return modes.Context(
            evaluator,
            exchange_manager,
            exchange_api.get_trader(exchange_manager),
            exchange or evaluator.exchange_name,
            symbol,
            evaluator.matrix_id,
            cryptocurrency,
            time_frame,
            evaluator.logger,
            trading_modes[0].__class__,
            trigger_cache_timestamp,
            trigger_source,
            trigger_value,
            None,
            None,
        )
    except ImportError:
        evaluator.logger.error("OctoBot-Evaluator local_trading_context requires OctoBot-Trading package installed")
        raise


def local_cache_client(evaluator, symbol, time_frame, exchange_name=None):
    try:
        exchange_name = exchange_name or evaluator.exchange_name
        import octobot_trading.api as exchange_api
        exchange_manager = exchange_api.get_exchange_manager_from_exchange_name_and_id(
            exchange_name,
            exchange_api.get_exchange_id_from_matrix_id(exchange_name, evaluator.matrix_id)
        )
        return databases.CacheClient(evaluator, exchange_name, symbol, time_frame,
                                     evaluator.tentacles_setup_config,
                                     not exchange_api.get_is_backtesting(exchange_manager))
    except ImportError:
        evaluator.logger.error("OctoBot-Evaluator local_cache_client requires OctoBot-Trading package installed")
        raise


def get_required_candles_count(trading_mode_class, tentacles_setup_config):
    return tentacles_manager_api.get_tentacle_config(tentacles_setup_config, trading_mode_class).get(
        constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT,
        constants.DEFAULT_IGNORED_VALUE
    )
