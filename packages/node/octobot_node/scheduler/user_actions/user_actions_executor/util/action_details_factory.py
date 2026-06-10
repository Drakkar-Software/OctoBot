import datetime
import decimal
import json
import typing

import octobot_commons.configuration.fields_utils as fields_utils
import octobot_commons.constants as commons_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.str_util as str_util
import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_copy.enums as copy_enums
import octobot_evaluators.evaluators.evaluator_dsl_factory as evaluator_dsl_factory
import octobot_flow.entities as flow_entities
import octobot_flow.entities.accounts.exchange_account_details as flow_exchange_account_details
import octobot_flow.enums as flow_enums
import octobot_protocol.models as protocol_models
import octobot_trading.exchanges.util.exchange_data as exchange_data_module

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_authentication_resolver as account_authentication_resolver
import octobot_node.scheduler.user_actions.user_actions_executor.util.exchange_account_resolver as exchange_account_resolver


_ACTION_ID_INIT = "action_init"


def _dsl_serializable_config_value(config_value: typing.Any) -> typing.Any:
    if isinstance(config_value, decimal.Decimal):
        return float(config_value)
    return config_value


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


def _configuration_instance_from_wrapper(
    configuration_wrapper: typing.Any,
    *,
    error_context: str,
) -> typing.Any:
    if configuration_wrapper is None or configuration_wrapper.actual_instance is None:
        raise node_errors.InvalidAutomationConfigurationError(
            f"{error_context}.configuration.actual_instance is required."
        )
    return configuration_wrapper.actual_instance


def _tentacle_config_from_protocol_configuration_instance(
    configuration_instance: typing.Any,
) -> dict[str, typing.Any]:
    tentacle_config = dict(configuration_instance.to_dict())
    tentacle_config.pop("configuration_type", None)
    return tentacle_config


def _operator_name_from_configuration_instance(configuration_instance: typing.Any) -> str:
    return str_util.camel_to_snake(configuration_instance.configuration_type.value)


def _next_action_id_for_configuration_type(
    configuration_type_value: str,
    configuration_type_counters: dict[str, int],
) -> str:
    configuration_type_counters[configuration_type_value] = (
        configuration_type_counters.get(configuration_type_value, 0) + 1
    )
    return f"{configuration_type_value}_{configuration_type_counters[configuration_type_value]}"


def _action_id_from_configuration(
    configuration: typing.Any,
    configuration_type_counters: dict[str, int] | None = None,
) -> str:
    counters: dict[str, int] = {} if configuration_type_counters is None else configuration_type_counters
    return _next_action_id_for_configuration_type(
        configuration.configuration_type.value,
        counters,
    )


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


def index_action_factory(
    init_action: flow_entities.AbstractActionDetails,
    index_configuration: protocol_models.IndexConfiguration,
) -> flow_entities.AbstractActionDetails:
    index_content = [
        {
            copy_enums.DistributionKeys.NAME: coin.name,
            copy_enums.DistributionKeys.VALUE: coin.ratio,
        }
        for coin in (index_configuration.coins or [])
    ]
    dsl_script = (
        f"index_trading_mode(index_content={json.dumps(index_content)}, "
        f"rebalance_trigger_min_percent={index_configuration.rebalance_trigger_min_percent})"
    )
    return flow_entities.DSLScriptActionDetails(
        id=_action_id_from_configuration(index_configuration),
        dsl_script=dsl_script,
        dependencies=[_action_dependency(init_action.id)],
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


def _validate_maximum_evaluators_dca_configuration(
    dca_configuration: protocol_models.DCAConfiguration,
) -> protocol_models.StrategyEvaluatorConfiguration:
    strategies = list(dca_configuration.strategies or [])
    evaluators = list(dca_configuration.evaluators or [])
    if not evaluators:
        raise node_errors.InvalidAutomationConfigurationError(
            "Maximum evaluators DCA requires at least one evaluator."
        )
    if not strategies:
        raise node_errors.InvalidAutomationConfigurationError(
            "DCA configuration with evaluators requires exactly one strategy evaluator configuration."
        )
    if len(strategies) > 1:
        raise node_errors.InvalidAutomationConfigurationError(
            f"DCA configuration supports at most one strategy evaluator, got {len(strategies)}."
        )
    return strategies[0]


def is_maximum_evaluators_dca_with_evaluators(
    dca_configuration: protocol_models.DCAConfiguration,
) -> bool:
    import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading

    if not dca_configuration.evaluators:
        return False
    return dca_configuration.trigger_mode == dca_trading.TriggerMode.MAXIMUM_EVALUATORS_SIGNALS_BASED.value


def _build_dca_tentacle_config(
    dca_configuration: protocol_models.DCAConfiguration,
    *,
    time_frames: list[str],
    trading_pairs: list[str],
    dag_reset_to_action_id: str | None = None,
) -> dict[str, typing.Any]:
    import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading

    secondary_entry_orders_count = int(dca_configuration.secondary_entry_orders_count)
    trigger_mode = dca_trading.TriggerMode(dca_configuration.trigger_mode)
    tentacle_config = dca_trading.DCATradingMode.get_default_config(
        buy_amount=dca_configuration.entry_order_amount,
        use_init_entry_orders=bool(dca_configuration.use_init_entry_orders),
        use_secondary_entry_orders=secondary_entry_orders_count > 0,
        secondary_entry_orders_count=secondary_entry_orders_count,
        secondary_entry_orders_amount=dca_configuration.secondary_entry_orders_amount,
        secondary_entry_orders_price_percent=float(dca_configuration.secondary_entry_orders_price_percent),
        exit_limit_orders_price_percent=float(dca_configuration.exit_limit_orders_price_percent),
        entry_limit_orders_price_percent=float(dca_configuration.entry_limit_orders_price_percent),
        enable_stop_loss=bool(dca_configuration.enable_stop_loss),
        stop_loss_price=float(dca_configuration.stop_loss_price_discount_percent),
        use_take_profit_exit_orders=True,
        trigger_mode=trigger_mode,
        max_asset_holding_percent=float(dca_configuration.max_asset_holding_percent),
    )
    tentacle_config[dca_trading.DCATradingMode.ENABLE_HEALTH_CHECK] = False
    tentacle_config[dca_trading.DCATradingMode.TRADING_PAIRS] = list(trading_pairs)
    tentacle_config[dca_trading.DCATradingMode.TIME_FRAMES] = list(time_frames)
    if dag_reset_to_action_id is not None:
        tentacle_config["dag_reset_to_action_id"] = dag_reset_to_action_id
    return tentacle_config


def evaluator_action_factory(
    init_action: flow_entities.AbstractActionDetails,
    evaluator_configuration: protocol_models.EvaluatorConfiguration,
    *,
    time_frames: list[str],
    action_id: str,
) -> flow_entities.AbstractActionDetails:
    configuration_instance = _configuration_instance_from_wrapper(
        evaluator_configuration.configuration,
        error_context="EvaluatorConfiguration",
    )
    operator_name = _operator_name_from_configuration_instance(configuration_instance)
    tentacle_config = _tentacle_config_from_protocol_configuration_instance(configuration_instance)
    symbols_list = ", ".join(f"{symbol!r}" for symbol in (evaluator_configuration.symbols or []))
    time_frames_list = ", ".join(f"{time_frame!r}" for time_frame in time_frames)
    dsl_parameter_parts = [
        f"{evaluator_dsl_factory.SYMBOLS_PARAM}=[{symbols_list}]",
        f"{evaluator_dsl_factory.TIME_FRAMES_PARAM}=[{time_frames_list}]",
    ]
    for config_key, config_value in tentacle_config.items():
        dsl_parameter_parts.append(
            f"{config_key}={dsl_interpreter.format_parameter_value(_dsl_serializable_config_value(config_value))}"
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
    configuration_instance = _configuration_instance_from_wrapper(
        strategy_evaluator_configuration.configuration,
        error_context="StrategyEvaluatorConfiguration",
    )
    operator_name = _operator_name_from_configuration_instance(configuration_instance)
    time_frames = _protocol_time_frame_values(strategy_evaluator_configuration.time_frames or [])
    time_frames_list = ", ".join(f"{time_frame!r}" for time_frame in time_frames)
    tentacle_config = _tentacle_config_from_protocol_configuration_instance(configuration_instance)
    dsl_parameter_parts = [f"{evaluator_dsl_factory.TIME_FRAMES_PARAM}=[{time_frames_list}]"]
    for config_key, config_value in tentacle_config.items():
        dsl_parameter_parts.append(
            f"{config_key}={dsl_interpreter.format_parameter_value(_dsl_serializable_config_value(config_value))}"
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


def maximum_evaluators_dca_action_factory(
    init_action: flow_entities.AbstractActionDetails,
    strategy_action: flow_entities.AbstractActionDetails,
    dca_configuration: protocol_models.DCAConfiguration,
    *,
    strategy_evaluator_configuration: protocol_models.StrategyEvaluatorConfiguration,
    action_id: str,
) -> flow_entities.AbstractActionDetails:
    import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading

    time_frames = _protocol_time_frame_values(strategy_evaluator_configuration.time_frames or [])
    tentacle_config = _build_dca_tentacle_config(
        dca_configuration,
        time_frames=time_frames,
        trading_pairs=[],
        dag_reset_to_action_id=_ACTION_ID_INIT,
    )
    config_parts = ", ".join(
        f"{config_key}={dsl_interpreter.format_parameter_value(_dsl_serializable_config_value(config_value))}"
        for config_key, config_value in tentacle_config.items()
        if config_value is not None
    )
    unresolved_placeholder = commons_constants.UNRESOLVED_PARAMETER_PLACEHOLDER
    dynamic_dependencies_key = dsl_interpreter.DynamicDependenciesOperatorMixin.DYNAMIC_DEPENDENCIES_KEY
    dca_operator = str_util.camel_to_snake(dca_trading.DCATradingMode.get_name())
    dsl_script = (
        f"{dca_operator}({config_parts}, {dynamic_dependencies_key}={unresolved_placeholder})"
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


def maximum_evaluators_dca_automation_actions_factory(
    init_action: flow_entities.AbstractActionDetails,
    dca_configuration: protocol_models.DCAConfiguration,
) -> list[flow_entities.AbstractActionDetails]:
    strategy_evaluator_configuration = _validate_maximum_evaluators_dca_configuration(dca_configuration)
    time_frames = _protocol_time_frame_values(strategy_evaluator_configuration.time_frames or [])
    configuration_type_counters: dict[str, int] = {}
    evaluator_actions: list[flow_entities.AbstractActionDetails] = []
    for evaluator_configuration in (dca_configuration.evaluators or []):
        configuration_instance = _configuration_instance_from_wrapper(
            evaluator_configuration.configuration,
            error_context="EvaluatorConfiguration",
        )
        evaluator_action_id = _next_action_id_for_configuration_type(
            configuration_instance.configuration_type.value,
            configuration_type_counters,
        )
        evaluator_actions.append(
            evaluator_action_factory(
                init_action,
                evaluator_configuration,
                time_frames=time_frames,
                action_id=evaluator_action_id,
            )
        )
    strategy_configuration_instance = _configuration_instance_from_wrapper(
        strategy_evaluator_configuration.configuration,
        error_context="StrategyEvaluatorConfiguration",
    )
    strategy_action_id = _next_action_id_for_configuration_type(
        strategy_configuration_instance.configuration_type.value,
        configuration_type_counters,
    )
    strategy_action = strategy_evaluator_action_factory(
        init_action,
        strategy_evaluator_configuration,
        evaluator_actions,
        action_id=strategy_action_id,
    )
    dca_action_id = _next_action_id_for_configuration_type(
        dca_configuration.configuration_type.value,
        configuration_type_counters,
    )
    dca_action = maximum_evaluators_dca_action_factory(
        init_action,
        strategy_action,
        dca_configuration,
        strategy_evaluator_configuration=strategy_evaluator_configuration,
        action_id=dca_action_id,
    )
    return [init_action, *evaluator_actions, strategy_action, dca_action]


def dca_action_factory(
    init_action: flow_entities.AbstractActionDetails,
    dca_configuration: protocol_models.DCAConfiguration,
) -> flow_entities.AbstractActionDetails:
    import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading

    tentacle_config = _build_dca_tentacle_config(
        dca_configuration,
        time_frames=[],
        trading_pairs=list(dca_configuration.symbols or []),
    )
    dca_operator = str_util.camel_to_snake(dca_trading.DCATradingMode.get_name())
    config_parts = ", ".join(
        f"{config_key}={dsl_interpreter.format_parameter_value(_dsl_serializable_config_value(config_value))}"
        for config_key, config_value in tentacle_config.items()
        if config_value is not None
    )
    dsl_script = f"{dca_operator}({config_parts})"
    return flow_entities.DSLScriptActionDetails(
        id=_action_id_from_configuration(dca_configuration),
        dsl_script=dsl_script,
        dependencies=[_action_dependency(init_action.id)],
    )


def grid_action_factory(
    init_action: flow_entities.AbstractActionDetails,
    grid_configuration: protocol_models.GridConfiguration,
) -> flow_entities.AbstractActionDetails:
    # avoid forcing tentacles import
    import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading
    pair_settings = [
        grid_trading.GridTradingMode.get_default_pair_config(
            grid_configuration.symbol,
            float(grid_configuration.spread),
            float(grid_configuration.increment),
            int(grid_configuration.buy_count),
            int(grid_configuration.sell_count),
            bool(grid_configuration.enable_trailing_up),
            bool(grid_configuration.enable_trailing_down),
            bool(grid_configuration.order_by_order_trailing),
        )
    ]
    dsl_script = (
        f"grid_trading_mode(pair_settings={dsl_interpreter.format_parameter_value(pair_settings)})"
    )
    return flow_entities.DSLScriptActionDetails(
        id=_action_id_from_configuration(grid_configuration),
        dsl_script=dsl_script,
        dependencies=[_action_dependency(init_action.id)],
    )


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
