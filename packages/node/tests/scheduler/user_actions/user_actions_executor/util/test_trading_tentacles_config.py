import pytest

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.util.action_details_factory as action_details_factory_module
import octobot_node.scheduler.user_actions.user_actions_executor.util.trading_tentacles_config as trading_tentacles_config_module
import tentacles.Evaluator.Strategies.mixed_strategies_evaluator.mixed_strategies as mixed_strategies_evaluator
import tentacles.Evaluator.TA.momentum_evaluator.momentum as momentum_evaluator
import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading
import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading
import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading

from . import trading_tentacles_test_utils


class TestNormalizeTentacleName:
    def test_camel_case_trading_mode(self):
        assert (
            trading_tentacles_config_module.normalize_tentacle_name("GridTradingMode")
            == "grid_trading_mode"
        )

    def test_acronym_camel_case_trading_mode(self):
        assert (
            trading_tentacles_config_module.normalize_tentacle_name("DCATradingMode")
            == "d_c_a_trading_mode"
        )

    def test_snake_case_unchanged(self):
        assert (
            trading_tentacles_config_module.normalize_tentacle_name("grid_trading_mode")
            == "grid_trading_mode"
        )

    def test_empty_string_unchanged(self):
        assert trading_tentacles_config_module.normalize_tentacle_name("") == ""


class TestGetTradingModeClassFromTentacleName:
    def test_returns_class_for_camel_case_name(self):
        trading_mode_class = trading_tentacles_config_module.get_trading_mode_class_from_tentacle_name(
            dca_trading.DCATradingMode.get_name()
        )
        assert trading_mode_class is dca_trading.DCATradingMode

    def test_returns_class_for_snake_case_name(self):
        trading_mode_class = trading_tentacles_config_module.get_trading_mode_class_from_tentacle_name(
            trading_tentacles_config_module.normalize_tentacle_name(
                grid_trading.GridTradingMode.get_name()
            )
        )
        assert trading_mode_class is grid_trading.GridTradingMode

    def test_returns_none_for_unknown_name(self):
        assert (
            trading_tentacles_config_module.get_trading_mode_class_from_tentacle_name(
                "CustomTradingMode"
            )
            is None
        )


class TestGetTradingTentaclesTradedSymbols:
    def test_returns_dca_config_trading_pairs(self):
        trading_configuration = trading_tentacles_test_utils.trading_tentacles_configuration(
            name=dca_trading.DCATradingMode.get_name(),
            config=trading_tentacles_test_utils.dca_tentacle_config(),
        )
        assert trading_tentacles_config_module.get_trading_tentacles_traded_symbols(
            trading_configuration,
            reference_market="USDT",
        ) == ["BTC/USDT"]

    def test_falls_back_to_evaluator_symbols_for_unknown_trading_mode(self):
        trading_configuration = trading_tentacles_test_utils.trading_tentacles_configuration(
            name="CustomTradingMode",
            config={},
            evaluators=[
                trading_tentacles_test_utils.evaluator_configuration_with_symbols(
                    ["BTC/USDT", "ETH/USDT"]
                ),
            ],
        )
        assert trading_tentacles_config_module.get_trading_tentacles_traded_symbols(
            trading_configuration,
            reference_market="USDT",
        ) == ["BTC/USDT", "ETH/USDT"]

    def test_grid_returns_pair_settings_symbols(self):
        trading_configuration = trading_tentacles_test_utils.grid_trading_configuration(
            symbol="ETH/USDT",
        )
        assert trading_tentacles_config_module.get_trading_tentacles_traded_symbols(
            trading_configuration,
            reference_market="USDT",
        ) == ["ETH/USDT"]

    def test_index_returns_merged_symbols_from_index_content(self):
        trading_configuration = trading_tentacles_test_utils.index_trading_configuration(
            coins=[("BTC", 1.0)],
            rebalance_trigger_min_percent=5.0,
        )
        assert trading_tentacles_config_module.get_trading_tentacles_traded_symbols(
            trading_configuration,
            reference_market="USDT",
        ) == ["BTC/USDT"]


class TestValidateTradingModeName:
    @pytest.mark.parametrize(
        "trading_mode_name",
        [
            dca_trading.DCATradingMode.get_name(),
            trading_tentacles_config_module.normalize_tentacle_name(
                dca_trading.DCATradingMode.get_name()
            ),
        ],
    )
    def test_accepts_known_dca_names(self, trading_mode_name: str):
        trading_configuration = trading_tentacles_test_utils.minimal_dca_trading_configuration().model_copy(
            update={"name": trading_mode_name},
        )
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    @pytest.mark.parametrize(
        "trading_mode_name",
        [
            grid_trading.GridTradingMode.get_name(),
            trading_tentacles_config_module.normalize_tentacle_name(
                grid_trading.GridTradingMode.get_name()
            ),
        ],
    )
    def test_accepts_known_grid_names(self, trading_mode_name: str):
        trading_configuration = trading_tentacles_test_utils.grid_trading_configuration().model_copy(
            update={"name": trading_mode_name},
        )
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    @pytest.mark.parametrize(
        "trading_mode_name",
        [
            index_trading.IndexTradingMode.get_name(),
            trading_tentacles_config_module.normalize_tentacle_name(
                index_trading.IndexTradingMode.get_name()
            ),
        ],
    )
    def test_accepts_known_index_names(self, trading_mode_name: str):
        trading_configuration = trading_tentacles_test_utils.index_trading_configuration(
            coins=[("BTC", 1.0)],
            rebalance_trigger_min_percent=5.0,
        ).model_copy(update={"name": trading_mode_name})
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    def test_unknown_trading_mode_raises_with_name_path(self):
        trading_configuration = trading_tentacles_test_utils.trading_tentacles_configuration(
            name="CustomTradingMode",
            config={},
            evaluators=[],
        )
        with pytest.raises(
            node_errors.UnknownTentacleConfigurationError,
            match=r"Unknown trading mode tentacle 'CustomTradingMode' at \.name\.",
        ):
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )

    def test_evaluator_name_as_trading_mode_raises_unknown_at_name_path(self):
        trading_configuration = trading_tentacles_test_utils.minimal_dca_trading_configuration().model_copy(
            update={"name": momentum_evaluator.RSIMomentumEvaluator.get_name()},
        )
        with pytest.raises(
            node_errors.UnknownTentacleConfigurationError,
            match=(
                r"Unknown trading mode tentacle 'RSIMomentumEvaluator' at \.name\."
            ),
        ):
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )


class TestValidateTradingModeConfig:
    def test_accepts_valid_dca_config(self):
        trading_configuration = trading_tentacles_test_utils.minimal_dca_trading_configuration()
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    def test_accepts_functional_dca_configuration(self):
        trading_configuration = trading_tentacles_test_utils.functional_dca_trading_configuration()
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    def test_accepts_valid_grid_configuration(self):
        trading_configuration = trading_tentacles_test_utils.grid_trading_configuration()
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    def test_accepts_valid_index_configuration(self):
        trading_configuration = trading_tentacles_test_utils.index_trading_configuration(
            coins=[("BTC", 1.0), ("ETH", 1.0)],
            rebalance_trigger_min_percent=5.0,
        )
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    def test_unknown_config_key_lists_available_parameters(self):
        trading_configuration = trading_tentacles_test_utils.minimal_dca_trading_configuration(
            unknown_key="value",
        )
        with pytest.raises(node_errors.InvalidTradingTentaclesConfigurationError) as error_info:
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )
        error_message = str(error_info.value)
        assert ".config.unknown_key" in error_message
        assert "available parameters:" in error_message
        assert dca_trading.DCATradingMode.TRADING_PAIRS in error_message

    def test_invalid_config_value_type_reports_expected_type(self):
        trading_configuration = trading_tentacles_test_utils.trading_tentacles_configuration(
            name=dca_trading.DCATradingMode.get_name(),
            config={
                dca_trading.DCATradingModeProducer.MAX_ASSET_HOLDING_PERCENT: "not-a-number",
            },
        )
        with pytest.raises(node_errors.InvalidTradingTentaclesConfigurationError) as error_info:
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )
        error_message = str(error_info.value)
        assert dca_trading.DCATradingModeProducer.MAX_ASSET_HOLDING_PERCENT in error_message
        assert "expected type: float" in error_message

    def test_collects_multiple_configuration_issues_in_one_error(self):
        trading_configuration = trading_tentacles_test_utils.trading_tentacles_configuration(
            name=dca_trading.DCATradingMode.get_name(),
            config={
                "unknown_key": "value",
                dca_trading.DCATradingModeProducer.MAX_ASSET_HOLDING_PERCENT: "not-a-number",
            },
        )
        with pytest.raises(node_errors.InvalidTradingTentaclesConfigurationError) as error_info:
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )
        error_message = str(error_info.value)
        assert ".config.unknown_key" in error_message
        assert dca_trading.DCATradingModeProducer.MAX_ASSET_HOLDING_PERCENT in error_message

    def test_ignores_none_config_values(self):
        trading_configuration = trading_tentacles_test_utils.trading_tentacles_configuration(
            name=dca_trading.DCATradingMode.get_name(),
            config={
                dca_trading.DCATradingMode.TRADING_PAIRS: None,
                dca_trading.DCATradingModeProducer.MAX_ASSET_HOLDING_PERCENT: None,
            },
        )
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )


class TestValidateEvaluatorConfig:
    def test_accepts_valid_evaluator_configuration(self):
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration()
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    @pytest.mark.parametrize(
        "evaluator_name",
        [
            momentum_evaluator.RSIMomentumEvaluator.get_name(),
            trading_tentacles_config_module.normalize_tentacle_name(
                momentum_evaluator.RSIMomentumEvaluator.get_name()
            ),
        ],
    )
    def test_accepts_known_evaluator_names(self, evaluator_name: str):
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            evaluators=[
                trading_tentacles_test_utils.evaluator_configuration_with_symbols(
                    ["BTC/USDT"],
                ).model_copy(update={"name": evaluator_name}),
            ],
        )
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    def test_accepts_string_numeric_value_when_castable_to_int(self):
        evaluator_configuration = trading_tentacles_test_utils.rsi_evaluator_configuration(
            ["BTC/USDT"],
            period_length=14,
        ).model_copy(
            update={
                "config": {
                    momentum_evaluator.RSIMomentumEvaluator.PERIOD_LENGTH: "14",
                    momentum_evaluator.RSIMomentumEvaluator.LONG_THRESHOLD: 50,
                    momentum_evaluator.RSIMomentumEvaluator.SHORT_THRESHOLD: 70,
                    momentum_evaluator.RSIMomentumEvaluator.TREND_CHANGE_IDENTIFIER: False,
                },
            }
        )
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            evaluators=[evaluator_configuration],
        )
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    def test_trading_mode_name_in_evaluator_slot_raises_unknown_at_name_path(self):
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            evaluators=[
                trading_tentacles_test_utils.evaluator_configuration_with_symbols(
                    ["BTC/USDT"],
                ).model_copy(update={"name": grid_trading.GridTradingMode.get_name()}),
            ],
        )
        with pytest.raises(
            node_errors.UnknownTentacleConfigurationError,
            match=r"Unknown evaluator tentacle 'GridTradingMode' at \.evaluators\[0\]\.name\.",
        ):
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )

    def test_unknown_evaluator_name_at_second_index_raises_with_path(self):
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            evaluators=[
                trading_tentacles_test_utils.rsi_evaluator_configuration(["BTC/USDT"]),
                trading_tentacles_test_utils.ema_evaluator_configuration(["BTC/USDT"]).model_copy(
                    update={"name": "CustomEvaluator"}
                ),
            ],
        )
        with pytest.raises(
            node_errors.UnknownTentacleConfigurationError,
            match=r"Unknown evaluator tentacle 'CustomEvaluator' at \.evaluators\[1\]\.name\.",
        ):
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )

    def test_unknown_evaluator_config_key_lists_available_parameters(self):
        evaluator_configuration = trading_tentacles_test_utils.rsi_evaluator_configuration(
            ["BTC/USDT"],
        ).model_copy(
            update={
                "config": {
                    **trading_tentacles_test_utils.rsi_evaluator_configuration(["BTC/USDT"]).config,
                    "unknown_evaluator_key": True,
                },
            }
        )
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            evaluators=[evaluator_configuration],
        )
        with pytest.raises(node_errors.InvalidTradingTentaclesConfigurationError) as error_info:
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )
        error_message = str(error_info.value)
        assert ".evaluators[0].config.unknown_evaluator_key" in error_message
        assert "available parameters:" in error_message

    def test_invalid_evaluator_config_value_type_reports_expected_type(self):
        evaluator_configuration = trading_tentacles_test_utils.rsi_evaluator_configuration(
            ["BTC/USDT"],
        ).model_copy(
            update={
                "config": {
                    **trading_tentacles_test_utils.rsi_evaluator_configuration(["BTC/USDT"]).config,
                    momentum_evaluator.RSIMomentumEvaluator.PERIOD_LENGTH: "not-a-number",
                },
            }
        )
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            evaluators=[evaluator_configuration],
        )
        with pytest.raises(node_errors.InvalidTradingTentaclesConfigurationError) as error_info:
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )
        error_message = str(error_info.value)
        assert ".evaluators[0].config.period_length" in error_message
        assert "expected type: int" in error_message


class TestValidateStrategyEvaluator:
    def test_accepts_valid_strategy_evaluator(self):
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration()
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    @pytest.mark.parametrize(
        "strategy_name",
        [
            mixed_strategies_evaluator.SimpleStrategyEvaluator.get_name(),
            trading_tentacles_config_module.normalize_tentacle_name(
                mixed_strategies_evaluator.SimpleStrategyEvaluator.get_name()
            ),
        ],
    )
    def test_accepts_known_strategy_evaluator_names(self, strategy_name: str):
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            strategies=[
                trading_tentacles_test_utils.simple_strategy_evaluator_configuration(
                    time_frames=["1h"],
                ).model_copy(update={"name": strategy_name}),
            ],
        )
        trading_tentacles_config_module.validate_trading_tentacles_configuration(
            trading_configuration
        )

    def test_evaluator_name_in_strategy_slot_raises_unknown_at_strategy_path(self):
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            strategies=[
                trading_tentacles_test_utils.simple_strategy_evaluator_configuration(
                    time_frames=["1h"],
                ).model_copy(
                    update={"name": momentum_evaluator.RSIMomentumEvaluator.get_name()}
                ),
            ],
        )
        with pytest.raises(
            node_errors.UnknownTentacleConfigurationError,
            match=(
                r"Unknown strategy evaluator tentacle 'RSIMomentumEvaluator' at "
                r"\.strategies\[0\]\.name\."
            ),
        ):
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )

    def test_trading_mode_name_in_strategy_slot_raises_unknown_at_strategy_path(self):
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            strategies=[
                trading_tentacles_test_utils.simple_strategy_evaluator_configuration(
                    time_frames=["1h"],
                ).model_copy(update={"name": grid_trading.GridTradingMode.get_name()}),
            ],
        )
        with pytest.raises(
            node_errors.UnknownTentacleConfigurationError,
            match=(
                r"Unknown strategy evaluator tentacle 'GridTradingMode' at "
                r"\.strategies\[0\]\.name\."
            ),
        ):
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )

    def test_unknown_strategy_config_key_lists_available_parameters(self):
        strategy_configuration = trading_tentacles_test_utils.simple_strategy_evaluator_configuration(
            time_frames=["1h"],
        ).model_copy(
            update={
                "config": {
                    **trading_tentacles_test_utils.simple_strategy_evaluator_configuration(
                        time_frames=["1h"],
                    ).config,
                    "unknown_strategy_key": True,
                },
            }
        )
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            strategies=[strategy_configuration],
        )
        with pytest.raises(node_errors.InvalidTradingTentaclesConfigurationError) as error_info:
            trading_tentacles_config_module.validate_trading_tentacles_configuration(
                trading_configuration
            )
        error_message = str(error_info.value)
        assert ".strategies[0].config.unknown_strategy_key" in error_message
        assert "available parameters:" in error_message


class TestValidateTentaclesConfig:
    def test_orchestrator_runs_structural_and_dsl_validation(self):
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration()
        strategy_evaluator_configuration = action_details_factory_module.validate_tentacles_config(
            trading_configuration
        )
        assert (
            strategy_evaluator_configuration.name
            == mixed_strategies_evaluator.SimpleStrategyEvaluator.get_name()
        )

    def test_orchestrator_accepts_minimal_dca_without_evaluators(self):
        trading_configuration = trading_tentacles_test_utils.minimal_dca_trading_configuration()
        assert (
            action_details_factory_module.validate_tentacles_config(trading_configuration)
            is None
        )

    def test_orchestrator_accepts_grid_configuration(self):
        trading_configuration = trading_tentacles_test_utils.grid_trading_configuration()
        assert (
            action_details_factory_module.validate_tentacles_config(trading_configuration)
            is None
        )

    def test_structural_failure_prevents_dsl_validation(self):
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            strategies=[],
        )
        with pytest.raises(
            node_errors.InvalidTradingTentaclesConfigurationError,
            match="requires exactly one strategy evaluator",
        ):
            action_details_factory_module.validate_tentacles_config(trading_configuration)

    def test_rejects_evaluators_without_strategy(self):
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            strategies=[],
            evaluators=[
                trading_tentacles_test_utils.rsi_evaluator_configuration(["BTC/USDT"]),
            ],
        )
        with pytest.raises(
            node_errors.InvalidTradingTentaclesConfigurationError,
            match="requires exactly one strategy evaluator",
        ):
            action_details_factory_module.validate_tentacles_config(trading_configuration)

    def test_rejects_multiple_strategy_evaluators(self):
        strategy_evaluator = trading_tentacles_test_utils.simple_strategy_evaluator_configuration(
            time_frames=["1h"],
        )
        trading_configuration = trading_tentacles_test_utils.maximum_evaluators_trading_configuration(
            strategies=[strategy_evaluator, strategy_evaluator],
        )
        with pytest.raises(
            node_errors.InvalidTradingTentaclesConfigurationError,
            match="supports at most one strategy evaluator",
        ):
            action_details_factory_module.validate_tentacles_config(trading_configuration)

    def test_rejects_strategy_evaluators_without_evaluators(self):
        trading_configuration = trading_tentacles_test_utils.minimal_dca_trading_configuration(
            strategies=[
                trading_tentacles_test_utils.simple_strategy_evaluator_configuration(
                    time_frames=["1h"],
                ),
            ],
        )
        with pytest.raises(
            node_errors.InvalidTradingTentaclesConfigurationError,
            match="must not include strategy evaluators",
        ):
            action_details_factory_module.validate_tentacles_config(trading_configuration)
