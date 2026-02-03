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

import octobot_commons.constants as commons_constants
import octobot_commons.errors as commons_errors
import octobot_commons.enums as commons_enums
import octobot_commons.dict_util as dict_util
import octobot_evaluators.matrix as matrix
import octobot_evaluators.enums as evaluators_enums
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.modes.script_keywords as script_keywords
import tentacles.Meta.Keywords.scripting_library.UI.inputs.triggers as triggers


# 10000000000 = Sat, 20 Nov 2286 17:46:40 GMT to select all values
ALL_VALUES_CACHE_KEY = 10000000000.0


def _is_first_candle_only(context):
    if not context.exchange_manager.is_backtesting:
        # this is a backtesting only optimization
        return False
    tentacle_config = context.tentacle.get_local_config()
    return tentacle_config.get(triggers.TRIGGER_ONLY_ON_THE_FIRST_CANDLE_KEY, False)


def _is_first_candle_call(context, init_key):
    # TODO: figure out if we currently are in the 1st call of the given candle (careful with timeframes)
    return not context.symbol_writer.are_data_initialized_by_key.get(init_key, False)


async def evaluator_get_result(
        context: script_keywords.Context,
        tentacle_class,
        time_frame=None,
        symbol: str = None,
        trigger: bool = False,
        value_key=commons_enums.CacheDatabaseColumns.VALUE.value,
        cache_key=None,
        config_name: str = None,
        config: dict = None
):
    tentacle_class = tentacles_manager_api.get_tentacle_class_from_string(tentacle_class) \
        if isinstance(tentacle_class, str) else tentacle_class
    config_name = context.get_config_name_or_default(tentacle_class, config_name)
    init_key = _get_init_key(context, config_name)
    is_first_candle_only = _is_first_candle_only(context)
    should_trigger = not is_first_candle_only or (is_first_candle_only and _is_first_candle_call(context, init_key))
    if not context.symbol_writer.are_data_initialized_by_key.get(init_key, False) or (should_trigger and trigger):
        with context.adapted_trigger_timestamp(tentacle_class, config_name):
            # always trigger when asked to then return the triggered evaluation return
            return (await _trigger_single_evaluation(context, tentacle_class, value_key, cache_key,
                                                     config_name, config, init_key))[0]
    if tentacle_class.use_cache():
        # try reading from cache
        try:
            with context.adapted_trigger_timestamp(tentacle_class, config_name):
                await context.ensure_tentacle_cache_requirements(tentacle_class, config_name)
                value, is_missing = await context.get_cached_value(value_key=value_key,
                                                                   cache_key=cache_key,
                                                                   tentacle_name=tentacle_class.__name__,
                                                                   config_name=config_name)
                if not is_missing:
                    return value
        except commons_errors.UninitializedCache as e:
            if tentacle_class is not None and trigger is False:
                raise commons_errors.UninitializedCache(f"Can't read cache from {tentacle_class} before initializing "
                                                        f"it. Either activate this tentacle or set the 'trigger' "
                                                        f"parameter to True (error: {e})") from None

    _ensure_cache_when_set_value_key(value_key, tentacle_class)
    # read from evaluation matrix
    for value in _tentacle_values(context, tentacle_class, time_frame=time_frame, symbol=symbol):
        return value


async def evaluator_get_results(
        context: script_keywords.Context,
        tentacle_class,
        time_frame=None,
        symbol: str = None,
        trigger: bool = False,
        value_key=commons_enums.CacheDatabaseColumns.VALUE.value,
        cache_key=None,
        limit: int = -1,
        max_history: bool = False,
        config_name: str = None,
        config: dict = None
):
    cache_key = ALL_VALUES_CACHE_KEY if max_history else cache_key
    tentacle_class = tentacles_manager_api.get_tentacle_class_from_string(tentacle_class) \
        if isinstance(tentacle_class, str) else tentacle_class
    config_name = context.get_config_name_or_default(tentacle_class, config_name)
    init_key = _get_init_key(context, config_name)
    is_first_candle_only = _is_first_candle_only(context)
    should_trigger = not is_first_candle_only or (is_first_candle_only and _is_first_candle_call(context, init_key))
    if not context.symbol_writer.are_data_initialized_by_key.get(init_key, False) or (should_trigger and trigger):
        with context.adapted_trigger_timestamp(tentacle_class, config_name):
            # always trigger when asked to
            eval_result, _ = await _trigger_single_evaluation(context, tentacle_class, value_key, cache_key,
                                                              config_name, config, init_key)
            if limit == 1:
                # return already if only one value to return
                return eval_result
    if tentacle_class.use_cache():
        try:
            with context.adapted_trigger_timestamp(tentacle_class, config_name):
                await context.ensure_tentacle_cache_requirements(tentacle_class, config_name)
                # can return multiple values
                return await context.get_cached_values(value_key=value_key, cache_key=cache_key, limit=limit,
                                                       tentacle_name=tentacle_class.__name__, config_name=config_name)
        except commons_errors.UninitializedCache:
            if tentacle_class is not None and trigger is False:
                raise commons_errors.UninitializedCache(f"Can't read cache from {tentacle_class} before initializing "
                                                        f"it. Either activate this tentacle or set the 'trigger' "
                                                        f"parameter to True") from None
    _ensure_cache_when_set_value_key(value_key, tentacle_class)
    if limit == 1:
        # read from evaluation matrix
        for value in _tentacle_values(context, tentacle_class, time_frame=time_frame, symbol=symbol):
            return value
        raise commons_errors.MissingDataError(f"No evaluator value for {tentacle_class.__name__}")
    else:
        raise commons_errors.ConfigEvaluatorError(f"Evaluator cache is required to get more than one historical value "
                                                  f"of an evaluator. Cache is disabled on {tentacle_class.__name__}")


def _ensure_cache_when_set_value_key(value_key, tentacle_class):
    if not tentacle_class.use_cache() and value_key != commons_enums.CacheDatabaseColumns.VALUE.value:
        raise commons_errors.ConfigEvaluatorError(f"Evaluator cache is required to read a value_key different from "
                                                  f"the evaluator output evaluation. "
                                                  f"Cache is disabled on {tentacle_class.__name__}")


async def _trigger_single_evaluation(context, tentacle_class, value_key, cache_key, config_name, config, init_key):
    config_name, cleaned_config_name, config, tentacles_setup_config, tentacle_config = \
        context.get_tentacle_config_elements(tentacle_class, config_name, config)
    async with context.local_nested_tentacle_config(tentacle_class, config_name, True):
        is_eval_result_set = False
        eval_result = evaluator_instance = None
        if cleaned_config_name not in tentacle_config or \
                not context.symbol_writer.are_data_initialized_by_key.get(init_key, False):
            # always call _init_nested_call the 1st time the evaluation chain is triggered to make sure scripts
            # are executed entirely at least once
            # might need to merge config with tentacles_manager_api.get_tentacle_config if evaluator is
            # not filling default config values
            init_config = {**tentacle_config.get(cleaned_config_name, {}), **config}
            eval_result, error, evaluator_instance = await _init_nested_call(
                context, tentacle_class, config_name, cleaned_config_name,
                tentacles_setup_config, tentacle_config, init_config
            )
            if error is None:
                is_eval_result_set = True
        try:
            tentacle_config = tentacle_config[cleaned_config_name]
        except KeyError as e:
            raise commons_errors.ConfigEvaluatorError(f"Missing evaluator configuration with name {e}")
        # apply forced config if any
        dict_util.nested_update_dict(tentacle_config, config)
        await script_keywords.save_user_input(
            context,
            config_name,
            commons_constants.NESTED_TENTACLE_CONFIG,
            tentacle_config,
            {},
            is_nested_config=context.nested_depth > 1,
            nested_tentacle=tentacle_class.get_name()
        )
        if not is_eval_result_set:
            eval_result, _, evaluator_instance = (await tentacle_class.single_evaluation(
                tentacles_setup_config,
                tentacle_config,
                context=context
            ))
        if value_key == commons_enums.CacheDatabaseColumns.VALUE.value and cache_key is None:
            return eval_result, evaluator_instance.specific_config
        else:
            value, is_missing = await context.get_cached_value(value_key=value_key,
                                                               cache_key=cache_key,
                                                               tentacle_name=tentacle_class.__name__,
                                                               config_name=config_name,
                                                               ignore_requirement=True)
            return None if is_missing else value, evaluator_instance.specific_config


async def _init_nested_call(context, tentacle_class, config_name, cleaned_config_name,
                            tentacles_setup_config, tentacle_config, config):
    evaluation, error, evaluator_instance = await tentacle_class.single_evaluation(
        tentacles_setup_config,
        config,
        context=context,
        ignore_cache=True
    )
    tentacle_config[cleaned_config_name] = evaluator_instance.specific_config
    if error is not None:
        _invalidate_call_and_parents_init_status(context, config_name)
    else:
        context.symbol_writer.are_data_initialized_by_key[_get_init_key(context, config_name)] = True
    return evaluation, error, evaluator_instance


def _get_init_key(context, config_name):
    return f"{config_name}_{context.time_frame}"


def _invalidate_call_and_parents_init_status(context, config_name):
    # set are_data_initialized_by_key to False for this evaluator and its parent calls to ensure init is called
    # again later and the evaluator can be run entirely
    context.symbol_writer.are_data_initialized_by_key[_get_init_key(context, config_name)] = False
    for nested_config_name in context.nested_config_names:
        context.symbol_writer.are_data_initialized_by_key[_get_init_key(context, nested_config_name)] = False


def _tentacle_values(context,
                     tentacle_class,
                     time_frames=None,
                     symbols=None,
                     time_frame=None,
                     symbol=None):
    tentacle_name = tentacle_class if isinstance(tentacle_class, str) else tentacle_class.get_name()
    symbols = [context.symbol or symbol] or symbols
    time_frames = [context.time_frame or time_frame] or time_frames
    for symbol in symbols:
        for time_frame in time_frames:
            for tentacle_type in evaluators_enums.EvaluatorMatrixTypes:
                for evaluated_ta_node in matrix.get_tentacles_value_nodes(
                        context.matrix_id,
                        matrix.get_tentacle_nodes(context.matrix_id,
                                                  exchange_name=context.exchange_name,
                                                  tentacle_type=tentacle_type.value,
                                                  tentacle_name=tentacle_name),
                        symbol=symbol,
                        time_frame=time_frame):
                    yield evaluated_ta_node.node_value
