#  Demo-only agent seed protocol fixtures. Not for production.

import datetime
import typing
import uuid

import octobot_copy.enums as copy_enums
import octobot_protocol.models as protocol_models

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading_mode
import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading_mode


def _trading_tentacles_configuration(
    *,
    name: str,
    config: dict[str, typing.Any],
) -> protocol_models.TradingTentaclesConfiguration:
    return protocol_models.TradingTentaclesConfiguration(
        configuration_type=protocol_models.ActionConfigurationType.TRADING_TENTACLES,
        name=name,
        config=config,
    )


def _grid_trading_tentacles_configuration() -> protocol_models.TradingTentaclesConfiguration:
    pair_settings = [
        grid_trading_mode.GridTradingMode.get_default_pair_config(
            demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_SYMBOL,
            demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_SPREAD,
            demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_INCREMENT,
            demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_BUY_COUNT,
            demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_SELL_COUNT,
            False,
            False,
            False,
        )
    ]
    return _trading_tentacles_configuration(
        name=grid_trading_mode.GridTradingMode.get_name(),
        config={
            grid_trading_mode.GridTradingMode.CONFIG_PAIR_SETTINGS: pair_settings,
        },
    )


def _index_trading_tentacles_configuration() -> protocol_models.TradingTentaclesConfiguration:
    index_content = [
        {
            copy_enums.DistributionKeys.NAME: "BTC",
            copy_enums.DistributionKeys.VALUE: 33.34,
        },
        {
            copy_enums.DistributionKeys.NAME: "ETH",
            copy_enums.DistributionKeys.VALUE: 33.33,
        },
        {
            copy_enums.DistributionKeys.NAME: "SOL",
            copy_enums.DistributionKeys.VALUE: 33.33,
        },
    ]
    return _trading_tentacles_configuration(
        name=index_trading_mode.IndexTradingMode.get_name(),
        config={
            index_trading_mode.IndexTradingModeProducer.INDEX_CONTENT: index_content,
            index_trading_mode.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT: (
                demo_agent_seed_constants.DEMO_AGENT_SEED_INDEX_REBALANCE_TRIGGER_MIN_PERCENT
            ),
        },
    )


def build_kraken_sim_exchange_config() -> protocol_models.ExchangeConfig:
    return protocol_models.ExchangeConfig(
        id=demo_agent_seed_constants.DEMO_AGENT_SEED_EXCHANGE_CONFIG_ID,
        name="Agent seed Kraken sim",
        exchange=demo_agent_seed_constants.DEMO_AGENT_SEED_EXCHANGE_INTERNAL_NAME,
        sandboxed=False,
        historical_trade_symbols=[
            demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_SYMBOL,
            "ETH/USDC",
            "SOL/USDC",
        ],
    )


def build_sim_exchange_account(
    *,
    account_id: str,
    account_name: str,
    usdc_total: float,
) -> protocol_models.Account:
    exchange_account = protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id=account_id,
        exchange_config_ids=[demo_agent_seed_constants.DEMO_AGENT_SEED_EXCHANGE_CONFIG_ID],
    )
    return protocol_models.Account(
        id=account_id,
        name=account_name,
        is_simulated=True,
        created_at=datetime.datetime(2026, 6, 1, 12, 0, 0, tzinfo=datetime.UTC),
        updated_at=datetime.datetime(2026, 6, 1, 12, 0, 0, tzinfo=datetime.UTC),
        assets=[
            protocol_models.DetailedAssetsForTradingType(
                trading_type=protocol_models.TradingType.SPOT,
                assets=[
                    protocol_models.DetailedAsset(
                        symbol="USDC",
                        total=usdc_total,
                        available=usdc_total,
                    ),
                ],
            ),
        ],
        specifics=protocol_models.AccountSpecifics(actual_instance=exchange_account),
    )


def build_grid_strategy() -> protocol_models.Strategy:
    return protocol_models.Strategy(
        id=demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_GRID_ID,
        version=demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_VERSION,
        name="Agent seed grid BTC/USDC",
        reference_market="USDC",
        configuration=protocol_models.StrategyConfiguration(
            _grid_trading_tentacles_configuration(),
        ),
    )


def build_index_strategy() -> protocol_models.Strategy:
    return protocol_models.Strategy(
        id=demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_INDEX_ID,
        version=demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_VERSION,
        name="Agent seed index BTC/ETH/SOL",
        reference_market="USDC",
        configuration=protocol_models.StrategyConfiguration(
            _index_trading_tentacles_configuration(),
        ),
    )


def wrap_user_action_configuration(
    payload: protocol_models.UserActionConfiguration,
) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(payload.to_json())


def build_create_grid_automation_user_action() -> protocol_models.UserAction:
    strategy_reference = protocol_models.StrategyReference(
        id=demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_GRID_ID,
        version=demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_VERSION,
        emit_signals=False,
    )
    automation_configuration = protocol_models.AutomationConfiguration(
        id=demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID,
        name=demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_AUTOMATION_DISPLAY_NAME,
        created_at=datetime.datetime(2026, 6, 1, 12, 0, 0, tzinfo=datetime.UTC),
        strategy=strategy_reference,
        accounts=[
            protocol_models.AccountReference(
                id=demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID,
            ),
        ],
    )
    payload = protocol_models.CreateAutomationConfiguration(
        action_type=protocol_models.UserActionType.AUTOMATION_CREATE,
        configuration=automation_configuration,
    )
    return protocol_models.UserAction(
        id=f"ua-agent-seed-grid-{uuid.uuid4()}",
        configuration=wrap_user_action_configuration(payload),
    )
