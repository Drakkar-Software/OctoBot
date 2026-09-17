#  Demo agent seed protocol builder unit tests.

import uuid

import octobot_protocol.models as protocol_models

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading_mode

import tools.agent_seed.protocol.builders as agent_seed_protocol_builders


class TestBuildKrakenSimExchangeConfig:
    def test_kraken_exchange_and_btc_usdc_symbol(self):
        exchange_config = agent_seed_protocol_builders.build_kraken_sim_exchange_config()
        assert exchange_config.exchange == demo_agent_seed_constants.DEMO_AGENT_SEED_EXCHANGE_INTERNAL_NAME
        assert demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_SYMBOL in (
            exchange_config.historical_trade_symbols or []
        )


class TestBuildGridStrategy:
    def test_grid_spread_increment_and_order_counts(self):
        strategy = agent_seed_protocol_builders.build_grid_strategy()
        tentacles_configuration = strategy.configuration.actual_instance
        assert isinstance(
            tentacles_configuration,
            protocol_models.TradingTentaclesConfiguration,
        )
        pair_settings = tentacles_configuration.config.get(
            grid_trading_mode.GridTradingMode.CONFIG_PAIR_SETTINGS,
            [],
        )
        assert len(pair_settings) == 1
        pair = pair_settings[0]
        assert pair[grid_trading_mode.GridTradingMode.CONFIG_PAIR] == (
            demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_SYMBOL
        )
        assert pair[grid_trading_mode.GridTradingMode.CONFIG_FLAT_SPREAD] == (
            demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_SPREAD
        )
        assert pair[grid_trading_mode.GridTradingMode.CONFIG_FLAT_INCREMENT] == (
            demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_INCREMENT
        )
        assert pair[grid_trading_mode.GridTradingMode.CONFIG_BUY_ORDERS_COUNT] == (
            demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_BUY_COUNT
        )
        assert pair[grid_trading_mode.GridTradingMode.CONFIG_SELL_ORDERS_COUNT] == (
            demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_SELL_COUNT
        )


class TestBuildIndexStrategy:
    def test_index_coins_and_rebalance_percent(self):
        strategy = agent_seed_protocol_builders.build_index_strategy()
        tentacles_configuration = strategy.configuration.actual_instance
        import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading_mode

        index_content = tentacles_configuration.config.get(
            index_trading_mode.IndexTradingModeProducer.INDEX_CONTENT,
            [],
        )
        coin_names = {entry["name"] for entry in index_content}
        assert coin_names == {"BTC", "ETH", "SOL"}
        assert tentacles_configuration.config.get(
            index_trading_mode.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT,
        ) == demo_agent_seed_constants.DEMO_AGENT_SEED_INDEX_REBALANCE_TRIGGER_MIN_PERCENT


class TestBuildCreateGridAutomationUserAction:
    def test_create_automation_references_stable_ids(self):
        user_action = agent_seed_protocol_builders.build_create_grid_automation_user_action()
        payload = user_action.configuration.actual_instance
        assert payload.action_type == protocol_models.UserActionType.AUTOMATION_CREATE
        automation = payload.configuration
        automation_id = demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID
        assert automation.id == automation_id
        assert str(uuid.UUID(automation_id)) == automation_id
        assert automation.strategy.id == demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_GRID_ID
        assert automation.accounts[0].id == demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID
