#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import functools
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.str_util as str_util
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors


def normalize_tentacle_name(tentacle_name: str) -> str:
    if not tentacle_name:
        return tentacle_name
    if not any(character.isupper() for character in tentacle_name):
        return tentacle_name
    return str_util.camel_to_snake(tentacle_name)


@functools.cache
def _trading_mode_classes_by_name() -> dict[str, type]:
    import octobot_trading.modes.modes_factory as modes_factory

    trading_mode_classes_by_name: dict[str, type] = {}
    for trading_mode_class in modes_factory.get_all_concrete_trading_mode_classes():
        camel_case_name = trading_mode_class.get_name()
        snake_case_name = normalize_tentacle_name(camel_case_name)
        trading_mode_classes_by_name[camel_case_name] = trading_mode_class
        trading_mode_classes_by_name[snake_case_name] = trading_mode_class
    return trading_mode_classes_by_name


def get_trading_mode_class_from_tentacle_name(tentacle_name: str) -> type | None:
    try:
        return _trading_mode_classes_by_name()[tentacle_name]
    except KeyError:
        return None


def _register_operator_aliases(
    operators_by_name: dict[str, type],
    operator_class: type,
    tentacle_class: type,
) -> None:
    dsl_keyword = operator_class.get_name()
    camel_name = tentacle_class.get_name()
    snake_name = normalize_tentacle_name(camel_name)
    for alias in {dsl_keyword, camel_name, snake_name}:
        operators_by_name[alias] = operator_class


@functools.cache
def _validation_config() -> dict[str, typing.Any]:
    return {commons_constants.CONFIG_EXCHANGES: {}}


@functools.cache
def _trading_mode_operators_by_tentacle_name() -> dict[str, type]:
    import octobot_trading.modes.mode_dsl_factory as mode_dsl_factory
    import octobot_trading.modes.modes_factory as modes_factory

    operators_by_name: dict[str, type] = {}
    validation_config = _validation_config()
    for trading_mode_class in modes_factory.get_all_concrete_trading_mode_classes():
        operator_class = mode_dsl_factory.create_trading_mode_operator(
            trading_mode_class,
            None,
            validation_config,
        )
        _register_operator_aliases(operators_by_name, operator_class, trading_mode_class)
    return operators_by_name


@functools.cache
def _evaluator_operators() -> tuple[tuple[type, type], ...]:
    import octobot_commons.tentacles_management as tentacles_management
    import octobot_evaluators.evaluators as evaluators_module
    import octobot_evaluators.evaluators.evaluator_dsl_factory as evaluator_dsl_factory

    evaluator_operators: list[tuple[type, type]] = []
    validation_config = _validation_config()
    for evaluator_class in tentacles_management.get_all_classes_from_parent(
        evaluators_module.AbstractEvaluator
    ):
        operator_class = evaluator_dsl_factory.create_evaluator_operator(
            evaluator_class,
            None,
            validation_config,
            None,
        )
        evaluator_operators.append((operator_class, evaluator_class))
    return tuple(evaluator_operators)


@functools.cache
def _strategy_evaluator_operators_by_tentacle_name() -> dict[str, type]:
    import octobot_evaluators.evaluators as evaluators_module

    strategy_operators_by_name: dict[str, type] = {}
    for operator_class, evaluator_class in _evaluator_operators():
        if not issubclass(evaluator_class, evaluators_module.StrategyEvaluator):
            continue
        _register_operator_aliases(strategy_operators_by_name, operator_class, evaluator_class)
    return strategy_operators_by_name


@functools.cache
def _non_strategy_evaluator_operators_by_tentacle_name() -> dict[str, type]:
    import octobot_evaluators.evaluators as evaluators_module

    evaluator_operators_by_name: dict[str, type] = {}
    for operator_class, evaluator_class in _evaluator_operators():
        if issubclass(evaluator_class, evaluators_module.StrategyEvaluator):
            continue
        _register_operator_aliases(evaluator_operators_by_name, operator_class, evaluator_class)
    return evaluator_operators_by_name


def _is_value_castable_to_parameter_type(value: typing.Any, param_type: type) -> bool:
    if isinstance(value, param_type):
        return True
    if param_type is int:
        if isinstance(value, bool):
            return False
        if isinstance(value, float) and value.is_integer():
            return True
        if isinstance(value, str):
            try:
                int(value)
            except ValueError:
                return False
            return True
        return False
    if param_type is float:
        if isinstance(value, int):
            return True
        if isinstance(value, str):
            try:
                float(value)
            except ValueError:
                return False
            return True
        return False
    if param_type is bool:
        return isinstance(value, bool)
    if param_type is str:
        return isinstance(value, str)
    if param_type is list:
        return isinstance(value, list)
    if param_type is dict:
        return isinstance(value, dict)
    return False


def _parameter_names_by_operator(operator_class: type) -> dict[str, type]:
    return {
        operator_parameter.name: operator_parameter.type
        for operator_parameter in operator_class.get_parameters()
    }


def _collect_config_validation_issues(
    *,
    json_path_prefix: str,
    tentacle_name: str,
    config: dict[str, typing.Any] | None,
    operator_class: type,
) -> list[str]:
    parameter_type_by_name = _parameter_names_by_operator(operator_class)
    available_parameter_names = sorted(parameter_type_by_name)
    configuration_issues: list[str] = []
    for config_key, config_value in (config or {}).items():
        if config_value is None:
            continue
        parameter_json_path = f"{json_path_prefix}.{config_key}"
        expected_type = parameter_type_by_name.get(config_key)
        if expected_type is None:
            configuration_issues.append(
                f"{parameter_json_path}: unknown parameter {config_key!r} for tentacle "
                f"{tentacle_name!r}; available parameters: {available_parameter_names}"
            )
            continue
        if not _is_value_castable_to_parameter_type(config_value, expected_type):
            configuration_issues.append(
                f"{parameter_json_path}: value {config_value!r} is not castable to "
                f"{expected_type.__name__}; expected type: {expected_type.__name__}"
            )
    return configuration_issues


def _raise_unknown_tentacle_configuration_error(
    *,
    tentacle_name: str,
    json_path: str,
    tentacle_kind: str,
) -> typing.NoReturn:
    raise node_errors.UnknownTentacleConfigurationError(
        f"Unknown {tentacle_kind} tentacle {tentacle_name!r} at {json_path}."
    )


def validate_trading_tentacles_configuration(
    trading_configuration: protocol_models.TradingTentaclesConfiguration,
) -> None:
    configuration_issues: list[str] = []

    trading_mode_operator_class = _trading_mode_operators_by_tentacle_name().get(
        trading_configuration.name
    )
    if trading_mode_operator_class is None:
        _raise_unknown_tentacle_configuration_error(
            tentacle_name=trading_configuration.name,
            json_path=".name",
            tentacle_kind="trading mode",
        )
    configuration_issues.extend(
        _collect_config_validation_issues(
            json_path_prefix=".config",
            tentacle_name=trading_configuration.name,
            config=trading_configuration.config,
            operator_class=trading_mode_operator_class,
        )
    )

    for strategy_index, strategy_configuration in enumerate(trading_configuration.strategies or []):
        strategy_operator_class = _strategy_evaluator_operators_by_tentacle_name().get(
            strategy_configuration.name
        )
        strategy_json_path = f".strategies[{strategy_index}].name"
        if strategy_operator_class is None:
            _raise_unknown_tentacle_configuration_error(
                tentacle_name=strategy_configuration.name,
                json_path=strategy_json_path,
                tentacle_kind="strategy evaluator",
            )
        configuration_issues.extend(
            _collect_config_validation_issues(
                json_path_prefix=f".strategies[{strategy_index}].config",
                tentacle_name=strategy_configuration.name,
                config=strategy_configuration.config,
                operator_class=strategy_operator_class,
            )
        )

    for evaluator_index, evaluator_configuration in enumerate(trading_configuration.evaluators or []):
        evaluator_operator_class = _non_strategy_evaluator_operators_by_tentacle_name().get(
            evaluator_configuration.name
        )
        evaluator_json_path = f".evaluators[{evaluator_index}].name"
        if evaluator_operator_class is None:
            _raise_unknown_tentacle_configuration_error(
                tentacle_name=evaluator_configuration.name,
                json_path=evaluator_json_path,
                tentacle_kind="evaluator",
            )
        configuration_issues.extend(
            _collect_config_validation_issues(
                json_path_prefix=f".evaluators[{evaluator_index}].config",
                tentacle_name=evaluator_configuration.name,
                config=evaluator_configuration.config,
                operator_class=evaluator_operator_class,
            )
        )

    if configuration_issues:
        issues_message = "\n  ".join(configuration_issues)
        raise node_errors.InvalidTradingTentaclesConfigurationError(
            f"Invalid trading tentacles configuration for {trading_configuration.name!r}:\n  "
            f"{issues_message}"
        )


def get_trading_tentacles_traded_symbols(
    trading_configuration: protocol_models.TradingTentaclesConfiguration,
    *,
    reference_market: str | None,
) -> list[str]:
    trading_config = trading_configuration.config or {}
    resolved_reference_market = reference_market or commons_constants.DEFAULT_REFERENCE_MARKET

    trading_mode_class = get_trading_mode_class_from_tentacle_name(trading_configuration.name)
    if trading_mode_class is not None:
        try:
            tentacle_symbols = trading_mode_class.get_tentacle_config_traded_symbols(
                trading_config, resolved_reference_market
            )
        except NotImplementedError:
            # Expected for trading modes that do not declare traded symbols in config;
            # fall back to evaluator symbols below.
            tentacle_symbols = []
        if tentacle_symbols:
            return tentacle_symbols

    evaluator_symbols: list[str] = []
    for evaluator_configuration in trading_configuration.evaluators or []:
        evaluator_symbols.extend(evaluator_configuration.symbols or [])
    return list(dict.fromkeys(evaluator_symbols))
