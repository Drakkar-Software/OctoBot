import datetime
import json

import octobot_commons.constants as commons_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_copy.enums as copy_enums
import octobot_flow.entities as flow_entities
import octobot_flow.entities.accounts.exchange_account_details as flow_exchange_account_details
import octobot_flow.enums as flow_enums
import octobot_protocol.models as protocol_models
import octobot_trading.exchanges.util.exchange_data as exchange_data_module

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_authentication_resolver as account_authentication_resolver
import octobot_node.scheduler.user_actions.user_actions_executor.util.exchange_account_resolver as exchange_account_resolver


_ACTION_ID_INIT = "action_init"
_ACTION_ID_MAIN = "action_1"
_ACTION_ID_COPY = "action_copy_exchange_account"


def _protocol_account_updated_at_unix_seconds(protocol_account: protocol_models.Account) -> float:
    moment = protocol_account.updated_at
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.UTC)
    return moment.timestamp()


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
        id=_ACTION_ID_MAIN,
        dsl_script=dsl_script,
        dependencies=[{"action_id": init_action.id}],
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
        id=_ACTION_ID_COPY,
        dsl_script=dsl_script,
        dependencies=[{"action_id": init_action.id}],
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
        id=_ACTION_ID_MAIN,
        dsl_script=dsl_script,
        dependencies=[{"action_id": init_action.id}],
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
            dependencies=[{"action_id": previous_action_id}],
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
        id=_ACTION_ID_MAIN,
        dsl_script=run_dsl,
        dependencies=[{"action_id": init_action.id}],
    )


def exchange_protocol_account_to_apply_configuration_dict(
    protocol_account: protocol_models.Account,
    *,
    wallet_address: str,
    account_id_override: str | None = None,
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
    account_identifier = account_id_override if account_id_override is not None else protocol_account.id
    exchange_config = exchange_account_resolver.get_exchange_config(
        wallet_address,
        exchange_payload,
    )

    exchange_details = commons_profile_data.ExchangeData(internal_name=exchange_config.exchange)
    if exchange_payload.remote_account_id:
        exchange_details.exchange_account_id = exchange_payload.remote_account_id
    if protocol_account.is_simulated:
        auth_details = exchange_data_module.ExchangeAuthDetails()
    else:
        authentication = account_authentication_resolver.get_exchange_authentication(
            wallet_address,
            protocol_account,
        )
        auth_details = exchange_data_module.ExchangeAuthDetails(
            api_key=authentication.api_key,
            api_secret=authentication.api_secret,
            api_password=authentication.api_passphrase or "",
        )

    exchange_account_details = flow_entities.ExchangeAccountDetails(
        metadata=flow_exchange_account_details.ExchangeAccountMetadata(
            id=account_identifier,
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
