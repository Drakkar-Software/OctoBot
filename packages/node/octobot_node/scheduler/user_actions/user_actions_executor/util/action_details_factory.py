import datetime
import json
import typing

import octobot_commons.configuration.fields_utils as fields_utils
import octobot_commons.constants as commons_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_evaluators.evaluators.evaluator_dsl_factory as evaluator_dsl_factory
import octobot_flow.entities as flow_entities
import octobot_flow.entities.accounts.exchange_account_details as flow_exchange_account_details
import octobot_flow.enums as flow_enums
import octobot_protocol.models as protocol_models
import octobot_trading.exchanges.util.exchange_data as exchange_data_module

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_authentication_resolver as account_authentication_resolver
import octobot_node.scheduler.user_actions.user_actions_executor.util.exchange_account_resolver as exchange_account_resolver
import octobot_node.scheduler.user_actions.user_actions_executor.util.trading_tentacles_config as trading_tentacles_config


_ACTION_ID_INIT = "action_init"


def _protocol_account_updated_at_unix_seconds(protocol_account: protocol_models.Account) -> float:
    moment = protocol_account.updated_at
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.UTC)
    return moment.timestamp()


def _action_dependency(
    action_id: str,
    *,
    parameter: str | None = None,
    result_path: str | None = None,
) -> dict[str, str]:
    dependency: dict[str, str] = {
        flow_enums.ActionDependencyParameter.ACTION_ID.value: action_id,
    }
    if parameter is not None:
        dependency[flow_enums.ActionDependencyParameter.PARAMETER.value] = parameter
    if result_path is not None:
        dependency[flow_enums.ActionDependencyParameter.RESULT_PATH.value] = result_path
    return dependency


def _next_action_id_for_tentacle_name(
    tentacle_name: str,
    tentacle_name_counters: dict[str, int],
) -> str:
    normalized_tentacle_name = trading_tentacles_config.normalize_tentacle_name(tentacle_name)
    tentacle_name_counters[normalized_tentacle_name] = (
        tentacle_name_counters.get(normalized_tentacle_name, 0) + 1
    )
    return f"{normalized_tentacle_name}_{tentacle_name_counters[normalized_tentacle_name]}"


def _action_id_from_configuration(
    configuration: typing.Any,
    configuration_type_counters: dict[str, int] | None = None,
) -> str:
    counters: dict[str, int] = {} if configuration_type_counters is None else configuration_type_counters
    return _next_action_id_for_configuration_type(
        configuration.configuration_type.value,
        counters,
    )


def _next_action_id_for_configuration_type(
    configuration_type_value: str,
    configuration_type_counters: dict[str, int],
) -> str:
    configuration_type_counters[configuration_type_value] = (
        configuration_type_counters.get(configuration_type_value, 0) + 1
    )
    return f"{configuration_type_value}_{configuration_type_counters[configuration_type_value]}"


def _tentacle_config_dict(config: dict[str, typing.Any] | None) -> dict[str, typing.Any]:
    if config is None:
        return {}
    return dict(config)


def _dsl_kwargs_from_config_dict(tentacle_config: dict[str, typing.Any]) -> str:
    config_parts = [
        f"{config_key}={dsl_interpreter.format_parameter_value(config_value)}"
        for config_key, config_value in tentacle_config.items()
        if config_value is not None
    ]
    return ", ".join(config_parts)


def _dsl_script_from_name_and_config(tentacle_name: str, config: dict[str, typing.Any] | None) -> str:
    operator_name = trading_tentacles_config.normalize_tentacle_name(tentacle_name)
    config_kwargs = _dsl_kwargs_from_config_dict(_tentacle_config_dict(config))
    if config_kwargs:
        return f"{operator_name}({config_kwargs})"
    return f"{operator_name}()"


def validate_trading_tentacles_strategies_evaluators(
    trading_configuration: protocol_models.TradingTentaclesConfiguration,
) -> protocol_models.StrategyEvaluatorConfiguration | None:
    strategies = list(trading_configuration.strategies or [])
    evaluators = list(trading_configuration.evaluators or [])
    if evaluators:
        if not strategies:
            raise node_errors.InvalidTradingTentaclesConfigurationError(
                "Trading tentacles configuration with evaluators requires exactly one strategy evaluator."
            )
        if len(strategies) > 1:
            raise node_errors.InvalidTradingTentaclesConfigurationError(
                f"Trading tentacles configuration supports at most one strategy evaluator, got {len(strategies)}."
            )
        return strategies[0]
    if strategies:
        raise node_errors.InvalidTradingTentaclesConfigurationError(
            "Trading tentacles configuration without evaluators must not include strategy evaluators."
        )
    return None


def validate_tentacles_config(
    trading_configuration: protocol_models.TradingTentaclesConfiguration,
) -> protocol_models.StrategyEvaluatorConfiguration | None:
    strategy_evaluator_configuration = validate_trading_tentacles_strategies_evaluators(
        trading_configuration
    )
    trading_tentacles_config.validate_trading_tentacles_configuration(trading_configuration)
    return strategy_evaluator_configuration


def init_action_factory(
    *,
    automation_id: str,
    protocol_account: protocol_models.Account,
    strategy_reference: protocol_models.StrategyReference,
    stored_strategy: protocol_models.Strategy,
    wallet_address: str,
    reference_market: str,
) -> flow_entities.AbstractActionDetails:
    """
    Build an init APPLY_CONFIGURATION action like flow functional tests, but sourced from AccountProvider.
    """
    if protocol_account.specifics is None or protocol_account.specifics.actual_instance is None:
        raise node_errors.InvalidAutomationConfigurationError(
            "Account.specifics.actual_instance is required to build init configuration."
        )
    specifics_instance = protocol_account.specifics.actual_instance
    if not isinstance(specifics_instance, protocol_models.ExchangeAccount):
        raise node_errors.InvalidAutomationConfigurationError(
            f"Only exchange accounts are supported for automations, got {type(specifics_instance).__name__}"
        )

    portfolio_assets = _portfolio_assets_from_account(
        protocol_account,
        exchange_account_resolver.trading_type_from_strategy(stored_strategy),
    )
    portfolio_content = _portfolio_content_from_detailed_assets(portfolio_assets)
    base_exchange_config = exchange_protocol_account_to_apply_configuration_dict(
        protocol_account,
        wallet_address=wallet_address,
        reference_market=reference_market,
    )

    automation_metadata = flow_entities.AutomationMetadata(
        automation_id=automation_id,
        strategy_id=strategy_reference.id,
        emit_signals=bool(strategy_reference.emit_signals),
        strategy_version=strategy_reference.version,
    )
    automation_details = flow_entities.AutomationDetails(
        metadata=automation_metadata,
        exchange_account_elements=flow_entities.ExchangeAccountElements(
            portfolio=exchange_data_module.PortfolioDetails(content=portfolio_content),
        ),
    )
    init_config = {
        "automation": automation_details.to_dict(include_default_values=False),
        **base_exchange_config,
    }

    return flow_entities.ConfiguredActionDetails(
        id=_ACTION_ID_INIT,
        action=flow_enums.ActionType.APPLY_CONFIGURATION.value,
        config=init_config,
    )


def copy_action_factory(
    init_action: flow_entities.AbstractActionDetails,
    copy_configuration: protocol_models.CopyConfiguration,
) -> flow_entities.AbstractActionDetails:
    dsl_script = (
        f"copy_exchange_account(strategy_id={json.dumps(copy_configuration.strategy_id)}, "
        "reference_market='', reference_account='', account_copy_settings='{}')"
    )
    return flow_entities.DSLScriptActionDetails(
        id=_action_id_from_configuration(copy_configuration),
        dsl_script=dsl_script,
        dependencies=[_action_dependency(init_action.id)],
    )


def _protocol_time_frame_values(
    time_frames: typing.Iterable[typing.Any],
) -> list[str]:
    return [
        time_frame.value if hasattr(time_frame, "value") else str(time_frame)
        for time_frame in time_frames
    ]


def evaluator_action_factory(
    init_action: flow_entities.AbstractActionDetails,
    evaluator_configuration: protocol_models.EvaluatorConfiguration,
    *,
    time_frames: list[str],
    action_id: str,
) -> flow_entities.AbstractActionDetails:
    operator_name = trading_tentacles_config.normalize_tentacle_name(evaluator_configuration.name)
    tentacle_config = _tentacle_config_dict(evaluator_configuration.config)
    symbols_list = ", ".join(f"{symbol!r}" for symbol in (evaluator_configuration.symbols or []))
    time_frames_list = ", ".join(f"{time_frame!r}" for time_frame in time_frames)
    dsl_parameter_parts = [
        f"{evaluator_dsl_factory.SYMBOLS_PARAM}=[{symbols_list}]",
        f"{evaluator_dsl_factory.TIME_FRAMES_PARAM}=[{time_frames_list}]",
    ]
    for config_key, config_value in tentacle_config.items():
        dsl_parameter_parts.append(
            f"{config_key}={dsl_interpreter.format_parameter_value(config_value)}"
        )
    if evaluator_configuration.include_in_construction_candle:
        dsl_parameter_parts.append(
            f"{evaluator_dsl_factory.INCLUDE_IN_CONSTRUCTION_CANDLE_PARAM}="
            f"{dsl_interpreter.format_parameter_value(True)}"
        )
    dsl_script = f"{operator_name}({', '.join(dsl_parameter_parts)})"
    return flow_entities.DSLScriptActionDetails(
        id=action_id,
        dsl_script=dsl_script,
        dependencies=[_action_dependency(init_action.id)],
    )


def strategy_evaluator_action_factory(
    init_action: flow_entities.AbstractActionDetails,
    strategy_evaluator_configuration: protocol_models.StrategyEvaluatorConfiguration,
    evaluator_actions: list[flow_entities.AbstractActionDetails],
    *,
    action_id: str,
) -> flow_entities.AbstractActionDetails:
    operator_name = trading_tentacles_config.normalize_tentacle_name(strategy_evaluator_configuration.name)
    time_frames = _protocol_time_frame_values(strategy_evaluator_configuration.time_frames or [])
    time_frames_list = ", ".join(f"{time_frame!r}" for time_frame in time_frames)
    tentacle_config = _tentacle_config_dict(strategy_evaluator_configuration.config)
    dsl_parameter_parts = [f"{evaluator_dsl_factory.TIME_FRAMES_PARAM}=[{time_frames_list}]"]
    for config_key, config_value in tentacle_config.items():
        dsl_parameter_parts.append(
            f"{config_key}={dsl_interpreter.format_parameter_value(config_value)}"
        )
    unresolved_placeholder = commons_constants.UNRESOLVED_PARAMETER_PLACEHOLDER
    dynamic_dependencies_key = dsl_interpreter.DynamicDependenciesOperatorMixin.DYNAMIC_DEPENDENCIES_KEY
    dsl_parameter_parts.append(f"{dynamic_dependencies_key}={unresolved_placeholder}")
    dependencies: list[dict[str, str]] = [_action_dependency(init_action.id)]
    for evaluator_action in evaluator_actions:
        dependencies.append(_action_dependency(
            evaluator_action.id,
            parameter=dynamic_dependencies_key,
        ))
    dsl_script = f"{operator_name}({', '.join(dsl_parameter_parts)})"
    return flow_entities.DSLScriptActionDetails(
        id=action_id,
        dsl_script=dsl_script,
        dependencies=dependencies,
    )


def trading_tentacles_action_factory(
    init_action: flow_entities.AbstractActionDetails,
    trading_configuration: protocol_models.TradingTentaclesConfiguration,
    *,
    action_id: str | None = None,
) -> flow_entities.AbstractActionDetails:
    if action_id is None:
        tentacle_name_counters: dict[str, int] = {}
        resolved_action_id = _next_action_id_for_tentacle_name(
            trading_configuration.name,
            tentacle_name_counters,
        )
    else:
        resolved_action_id = action_id
    dsl_script = _dsl_script_from_name_and_config(
        trading_configuration.name,
        trading_configuration.config,
    )
    return flow_entities.DSLScriptActionDetails(
        id=resolved_action_id,
        dsl_script=dsl_script,
        dependencies=[_action_dependency(init_action.id)],
    )


def _trading_tentacles_with_evaluators_trading_mode_action_factory(
    init_action: flow_entities.AbstractActionDetails,
    strategy_action: flow_entities.AbstractActionDetails,
    trading_configuration: protocol_models.TradingTentaclesConfiguration,
    *,
    action_id: str,
) -> flow_entities.AbstractActionDetails:
    tentacle_config = _tentacle_config_dict(trading_configuration.config)
    tentacle_config["dag_reset_to_action_id"] = _ACTION_ID_INIT
    config_parts = _dsl_kwargs_from_config_dict(tentacle_config)
    unresolved_placeholder = commons_constants.UNRESOLVED_PARAMETER_PLACEHOLDER
    dynamic_dependencies_key = dsl_interpreter.DynamicDependenciesOperatorMixin.DYNAMIC_DEPENDENCIES_KEY
    operator_name = trading_tentacles_config.normalize_tentacle_name(trading_configuration.name)
    dsl_script = (
        f"{operator_name}({config_parts}, {dynamic_dependencies_key}={unresolved_placeholder})"
    )
    return flow_entities.DSLScriptActionDetails(
        id=action_id,
        dsl_script=dsl_script,
        dependencies=[
            _action_dependency(init_action.id),
            _action_dependency(
                strategy_action.id,
                parameter=dynamic_dependencies_key,
            ),
        ],
    )


def trading_tentacles_with_evaluators_actions_factory(
    init_action: flow_entities.AbstractActionDetails,
    trading_configuration: protocol_models.TradingTentaclesConfiguration,
) -> list[flow_entities.AbstractActionDetails]:
    strategy_evaluator_configuration = validate_tentacles_config(trading_configuration)
    if strategy_evaluator_configuration is None:
        raise node_errors.InvalidAutomationConfigurationError(
            "Trading tentacles evaluators orchestration requires at least one evaluator."
        )
    time_frames = _protocol_time_frame_values(strategy_evaluator_configuration.time_frames or [])
    tentacle_name_counters: dict[str, int] = {}
    evaluator_actions: list[flow_entities.AbstractActionDetails] = []
    for evaluator_configuration in (trading_configuration.evaluators or []):
        evaluator_action_id = _next_action_id_for_tentacle_name(
            evaluator_configuration.name,
            tentacle_name_counters,
        )
        evaluator_actions.append(
            evaluator_action_factory(
                init_action,
                evaluator_configuration,
                time_frames=time_frames,
                action_id=evaluator_action_id,
            )
        )
    strategy_action_id = _next_action_id_for_tentacle_name(
        strategy_evaluator_configuration.name,
        tentacle_name_counters,
    )
    strategy_action = strategy_evaluator_action_factory(
        init_action,
        strategy_evaluator_configuration,
        evaluator_actions,
        action_id=strategy_action_id,
    )
    trading_mode_action_id = _next_action_id_for_tentacle_name(
        trading_configuration.name,
        tentacle_name_counters,
    )
    trading_mode_action = _trading_tentacles_with_evaluators_trading_mode_action_factory(
        init_action,
        strategy_action,
        trading_configuration,
        action_id=trading_mode_action_id,
    )
    return [init_action, *evaluator_actions, strategy_action, trading_mode_action]


def generic_workflow_actions_factory(
    init_action: flow_entities.AbstractActionDetails,
    generic_workflow_configuration: protocol_models.GenericWorkflowConfiguration,
) -> list[flow_entities.AbstractActionDetails]:
    translated: list[flow_entities.AbstractActionDetails] = []
    previous_action_id = init_action.id
    for workflow_action in generic_workflow_configuration.actions or []:
        translated_action = _translate_workflow_action(
            workflow_action,
            dependencies=[_action_dependency(previous_action_id)],
        )
        translated.append(translated_action)
        previous_action_id = translated_action.id
    return translated


def market_making_action_factory(
    init_action: flow_entities.AbstractActionDetails,
    market_making_configuration: protocol_models.MarketMakingConfiguration,
    protocol_account: protocol_models.Account,
    wallet_address: str,
    reference_market: str,
    stored_strategy: protocol_models.Strategy,
) -> flow_entities.AbstractActionDetails:
    profile_data = market_making_profile_data_factory(
        protocol_account=protocol_account,
        market_making_configuration=market_making_configuration,
        reference_market=reference_market,
        wallet_address=wallet_address,
        stored_strategy=stored_strategy,
    )
    profile_data_dict = profile_data.to_dict(include_default_values=False)
    exchange_auth_data = _exchange_auth_data_list_from_protocol_account(
        protocol_account,
        wallet_address,
    )
    exchange_auth_segment = dsl_interpreter.format_parameter_value(exchange_auth_data)
    run_dsl = (
        "run_octobot_process("
        f"{protocol_account.id!r}, {dsl_interpreter.format_parameter_value(profile_data_dict)}, "
        f"{exchange_auth_segment}, "
        "waiting_time=2.0, ping_timeout=30.0)"
    )
    return flow_entities.DSLScriptActionDetails(
        id=_action_id_from_configuration(market_making_configuration),
        dsl_script=run_dsl,
        dependencies=[_action_dependency(init_action.id)],
    )


def exchange_protocol_account_to_apply_configuration_dict(
    protocol_account: protocol_models.Account,
    *,
    wallet_address: str,
    reference_market: str | None = None,
) -> dict:
    """
    Build an AutomationState-shaped dict fragment for AutomationConfigurationUpdater:
    only ``exchange_account_details`` is populated from a protocol Account.
    """
    if protocol_account.specifics is None or protocol_account.specifics.actual_instance is None:
        raise node_errors.InvalidUserActionPayloadError(
            "Account.specifics.actual_instance is required for exchange account user actions."
        )
    specifics_instance = protocol_account.specifics.actual_instance
    if not isinstance(specifics_instance, protocol_models.ExchangeAccount):
        raise node_errors.InvalidUserActionPayloadError(
            f"Only EXCHANGE accounts are supported for this translation; got {type(specifics_instance).__name__}."
        )

    exchange_payload = specifics_instance
    account_identifier = protocol_account.id
    exchange_config = exchange_account_resolver.get_exchange_config(
        wallet_address,
        exchange_payload,
    )

    exchange_details = commons_profile_data.ExchangeData(internal_name=exchange_config.exchange)
    exchange_details.exchange_account_id = (
        exchange_payload.remote_account_id or account_identifier
    )
    if protocol_account.is_simulated:
        auth_details = exchange_data_module.ExchangeAuthDetails()
    else:
        authentication = account_authentication_resolver.get_exchange_authentication(
            wallet_address,
            protocol_account,
        )
        api_password = ""
        if authentication.api_passphrase:
            api_password = fields_utils.encrypt(authentication.api_passphrase).decode()
        auth_details = exchange_data_module.ExchangeAuthDetails(
            api_key=fields_utils.encrypt(authentication.api_key).decode(),
            api_secret=fields_utils.encrypt(authentication.api_secret).decode(),
            api_password=api_password,
        )

    exchange_account_details = flow_entities.ExchangeAccountDetails(
        metadata=flow_exchange_account_details.ExchangeAccountMetadata(
            updated_at=_protocol_account_updated_at_unix_seconds(protocol_account),
            name=protocol_account.name,
        ),
        exchange_details=exchange_details,
        auth_details=auth_details,
        portfolio=flow_entities.ExchangeAccountPortfolio(unit=reference_market or ""),
    )

    return {
        "exchange_account_details": exchange_account_details.to_dict(include_default_values=False)
    }


def market_making_profile_data_factory(
    *,
    protocol_account: protocol_models.Account,
    market_making_configuration: protocol_models.MarketMakingConfiguration,
    reference_market: str,
    wallet_address: str,
    stored_strategy: protocol_models.Strategy,
) -> commons_profile_data.ProfileData:
    if protocol_account.specifics is None or protocol_account.specifics.actual_instance is None:
        raise node_errors.InvalidAutomationConfigurationError(
            "Account.specifics.actual_instance is required to build market making profile data."
        )
    specifics_instance = protocol_account.specifics.actual_instance
    if not isinstance(specifics_instance, protocol_models.ExchangeAccount):
        raise node_errors.InvalidAutomationConfigurationError(
            f"Market making requires an exchange account; got {type(specifics_instance).__name__}"
        )

    symbols = [entry.trading_pair for entry in (market_making_configuration.pair_settings or [])]
    if not symbols:
        raise node_errors.InvalidAutomationConfigurationError(
            "MarketMakingConfiguration.pair_settings must not be empty."
        )

    reference_market_value = reference_market

    portfolio_assets = _portfolio_assets_from_account(
        protocol_account,
        exchange_account_resolver.trading_type_from_strategy(stored_strategy),
    )
    starting_portfolio = {asset.symbol: float(asset.total) for asset in portfolio_assets}

    profile_identifier = f"market_making_{protocol_account.id}"
    profile_details = commons_profile_data.ProfileDetailsData(
        name=profile_identifier,
        id=profile_identifier,
    )
    crypto_currency = commons_profile_data.CryptoCurrencyData(
        trading_pairs=list(symbols),
        name=symbols[0].split("/")[0],
        enabled=True,
    )
    exchange_entry = commons_profile_data.ExchangeData(
        internal_name=exchange_account_resolver.get_exchange_config(
            wallet_address,
            specifics_instance,
        ).exchange,
        exchange_type=commons_constants.DEFAULT_EXCHANGE_TYPE,
    )
    trader = commons_profile_data.TraderData(enabled=False)
    trader_simulator = commons_profile_data.TraderSimulatorData(
        enabled=bool(protocol_account.is_simulated),
        starting_portfolio=starting_portfolio,
        maker_fees=0.0,
        taker_fees=0.0,
    )
    trading = commons_profile_data.TradingData(
        reference_market=reference_market_value,
        risk=1.0,
        paused=False,
    )
    tentacle = commons_profile_data.TentaclesData(
        name="SimpleMarketMakingTradingMode",
        config=market_making_configuration.to_dict(),
    )
    return commons_profile_data.ProfileData(
        profile_details=profile_details,
        crypto_currencies=[crypto_currency],
        exchanges=[exchange_entry],
        trader=trader,
        trader_simulator=trader_simulator,
        trading=trading,
        tentacles=[tentacle],
        options=commons_profile_data.OptionsData(),
        distribution=commons_constants.DEFAULT_DISTRIBUTION,
    )


def _translate_workflow_action(
    workflow_action: protocol_models.Action,
    *,
    dependencies: list[dict[str, str]] | None = None,
) -> flow_entities.AbstractActionDetails:
    if workflow_action.dsl:
        return flow_entities.DSLScriptActionDetails(
            id=workflow_action.id,
            dsl_script=workflow_action.dsl,
            dependencies=dependencies or [],
        )
    if workflow_action.configuration:
        # We don't have a protocol->flow mapping for arbitrary action_type configs here.
        raise node_errors.InvalidAutomationConfigurationError(
            f"Generic workflow action {workflow_action.id!r} uses configuration payload; only DSL actions are supported."
        )
    raise node_errors.InvalidAutomationConfigurationError(
        f"Generic workflow action {workflow_action.id!r} must provide a DSL script."
    )


def _portfolio_assets_from_account(
    protocol_account: protocol_models.Account,
    trading_type: protocol_models.TradingType | None,
) -> list[protocol_models.DetailedAsset]:
    return exchange_account_resolver.detailed_assets_from_account(
        protocol_account,
        trading_type,
    )


def _portfolio_content_from_detailed_assets(
    assets: list[protocol_models.DetailedAsset],
) -> dict[str, dict[str, float]]:
    content: dict[str, dict[str, float]] = {}
    for asset in assets:
        content[str(asset.symbol)] = {
            "available": float(asset.available),
            "total": float(asset.total),
        }
    return content


def _exchange_auth_data_list_from_protocol_account(
    protocol_account: protocol_models.Account,
    wallet_address: str,
) -> list[dict] | None:
    """
    Build ``exchange_auth_data`` for ``run_octobot_process`` from AccountProvider data
    and AccountAuthenticationProvider credentials.
    """
    if protocol_account.is_simulated:
        return None
    account_specifics = protocol_account.specifics
    if account_specifics is None or account_specifics.actual_instance is None:
        raise node_errors.InvalidAutomationConfigurationError(
            "Account.specifics.actual_instance is required to build exchange_auth_data for a live account."
        )
    specifics_instance = account_specifics.actual_instance
    if not isinstance(specifics_instance, protocol_models.ExchangeAccount):
        raise node_errors.InvalidAutomationConfigurationError(
            f"exchange_auth_data requires an exchange account; got {type(specifics_instance).__name__}."
        )
    authentication = account_authentication_resolver.get_exchange_authentication(
        wallet_address,
        protocol_account,
    )
    exchange_config = exchange_account_resolver.get_exchange_config(
        wallet_address,
        specifics_instance,
    )
    return [
        {
            "internal_name": exchange_config.exchange,
            "api_key": authentication.api_key,
            "api_secret": authentication.api_secret,
            "api_password": authentication.api_passphrase or "",
            "exchange_type": commons_constants.DEFAULT_EXCHANGE_TYPE,
            "sandboxed": exchange_config.sandboxed,
        }
    ]
