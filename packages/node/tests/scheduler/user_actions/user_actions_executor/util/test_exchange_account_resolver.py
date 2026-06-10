import datetime
import typing

import pytest

import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.util.exchange_account_resolver as exchange_account_resolver_module

from ..account import account_executor_test_utils


def _strategy_with_configuration(
    configuration_instance: typing.Any,
) -> protocol_models.Strategy:
    return protocol_models.Strategy(
        id="strategy-1",
        version="1.0.0",
        reference_market="USDT",
        configuration=protocol_models.StrategyConfiguration(configuration_instance),
    )


def _account_with_asset_buckets(
    *trading_types: protocol_models.TradingType,
) -> protocol_models.Account:
    assets = [
        protocol_models.DetailedAssetsForTradingType(
            trading_type=trading_type,
            assets=[
                protocol_models.DetailedAsset(
                    symbol=f"{trading_type.value.upper()}-ASSET",
                    total=1.0,
                    available=1.0,
                )
            ],
        )
        for trading_type in trading_types
    ]
    return protocol_models.Account(
        id="acc-1",
        name="Test account",
        is_simulated=True,
        created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        updated_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        assets=assets,
        specifics=protocol_models.AccountSpecifics(
            actual_instance=account_executor_test_utils.exchange_account_payload(),
        ),
    )


def _exchange_account_with_config_ids(
    exchange_config_ids: list[str],
) -> protocol_models.ExchangeAccount:
    return account_executor_test_utils.exchange_account_payload().model_copy(
        update={"exchange_config_ids": exchange_config_ids},
    )


def _minimal_dca_configuration(**symbol_overrides) -> protocol_models.DCAConfiguration:
    payload = {
        "configuration_type": protocol_models.ActionConfigurationType.DCA,
        "symbols": ["BTC/USDT"],
        "entry_order_amount": "10%t",
        "exit_limit_orders_price_percent": 5,
        "entry_limit_orders_price_percent": 1,
        "secondary_entry_orders_count": 1,
        "secondary_entry_orders_amount": "7%t",
        "secondary_entry_orders_price_percent": 1.0,
        "enable_stop_loss": False,
        "stop_loss_price_discount_percent": 0,
        "trigger_mode": "Time based",
        "use_init_entry_orders": True,
        "strategies": [],
        "evaluators": [],
    }
    payload.update(symbol_overrides)
    return protocol_models.DCAConfiguration(**payload)


class TestGetPrimaryExchangeConfigId:
    def test_returns_single_exchange_config_id(self):
        exchange_account = _exchange_account_with_config_ids(["cfg-1"])
        assert exchange_account_resolver_module.get_primary_exchange_config_id(exchange_account) == "cfg-1"

    def test_raises_when_exchange_config_ids_empty(self):
        exchange_account = _exchange_account_with_config_ids([])
        with pytest.raises(node_errors.InvalidUserActionPayloadError):
            exchange_account_resolver_module.get_primary_exchange_config_id(exchange_account)

    def test_raises_when_multiple_exchange_config_ids(self):
        exchange_account = _exchange_account_with_config_ids(["cfg-1", "cfg-2"])
        with pytest.raises(node_errors.AmbiguousExchangeConfigError):
            exchange_account_resolver_module.get_primary_exchange_config_id(exchange_account)


class TestGetExchangeConfig:
    def test_raises_ambiguous_exchange_config_before_provider_lookup(self):
        exchange_account = _exchange_account_with_config_ids(["cfg-1", "cfg-2"])
        with pytest.raises(node_errors.AmbiguousExchangeConfigError):
            exchange_account_resolver_module.get_exchange_config(
                "0xwallet",
                exchange_account,
            )


class TestTradingTypeFromStrategy:
    def test_index_configuration_is_always_spot(self):
        strategy = _strategy_with_configuration(
            protocol_models.IndexConfiguration(
                configuration_type=protocol_models.ActionConfigurationType.INDEX,
                coins=[protocol_models.IndexCoin(name="BTC", ratio=1)],
                rebalance_trigger_min_percent=5,
            )
        )
        assert (
            exchange_account_resolver_module.trading_type_from_strategy(strategy)
            == protocol_models.TradingType.SPOT
        )

    def test_copy_configuration_has_no_trading_type(self):
        strategy = _strategy_with_configuration(
            protocol_models.CopyConfiguration(
                configuration_type=protocol_models.ActionConfigurationType.COPY,
                strategy_id="copied-strategy",
            )
        )
        assert exchange_account_resolver_module.trading_type_from_strategy(strategy) is None

    def test_generic_workflow_configuration_has_no_trading_type(self):
        strategy = _strategy_with_configuration(
            protocol_models.GenericWorkflowConfiguration(
                configuration_type=protocol_models.ActionConfigurationType.GENERIC_WORKFLOW,
                actions=[],
            )
        )
        assert exchange_account_resolver_module.trading_type_from_strategy(strategy) is None

    def test_generic_process_configuration_has_no_trading_type(self):
        strategy = _strategy_with_configuration(
            protocol_models.GenericProcessConfiguration(
                configuration_type=protocol_models.ActionConfigurationType.GENERIC_PROCESS,
                profile_data={},
            )
        )
        assert exchange_account_resolver_module.trading_type_from_strategy(strategy) is None

    def test_all_spot_symbols_return_spot(self):
        strategy = _strategy_with_configuration(
            protocol_models.GridConfiguration(
                configuration_type=protocol_models.ActionConfigurationType.GRID,
                symbol="BTC/USDT",
                spread=100,
                increment=50,
                buy_count=2,
                sell_count=2,
                enable_trailing_up=False,
                enable_trailing_down=False,
                order_by_order_trailing=False,
            )
        )
        assert (
            exchange_account_resolver_module.trading_type_from_strategy(strategy)
            == protocol_models.TradingType.SPOT
        )

    def test_all_futures_symbols_return_futures(self):
        strategy = _strategy_with_configuration(
            _minimal_dca_configuration(symbols=["BTC/USDT:USDT"]),
        )
        assert (
            exchange_account_resolver_module.trading_type_from_strategy(strategy)
            == protocol_models.TradingType.FUTURES
        )

    def test_all_option_symbols_return_options(self):
        strategy = _strategy_with_configuration(
            _minimal_dca_configuration(symbols=["BTC/USDT:USDT-211225-60000-P"]),
        )
        assert (
            exchange_account_resolver_module.trading_type_from_strategy(strategy)
            == protocol_models.TradingType.OPTIONS
        )

    def test_mixed_symbol_types_raise_ambiguous_trading_type(self):
        strategy = _strategy_with_configuration(
            _minimal_dca_configuration(symbols=["BTC/USDT", "BTC/USDT:USDT"]),
        )
        with pytest.raises(node_errors.AmbiguousTradingTypeError):
            exchange_account_resolver_module.trading_type_from_strategy(strategy)

    def test_empty_symbols_raise_unknown_trading_type(self):
        strategy = _strategy_with_configuration(
            _minimal_dca_configuration(symbols=[]),
        )
        with pytest.raises(node_errors.UnknownTradingTypeError):
            exchange_account_resolver_module.trading_type_from_strategy(strategy)


class TestDetailedAssetsFromAccount:
    def test_filters_assets_for_concrete_trading_type(self):
        account = _account_with_asset_buckets(
            protocol_models.TradingType.SPOT,
            protocol_models.TradingType.FUTURES,
        )
        assets = exchange_account_resolver_module.detailed_assets_from_account(
            account,
            protocol_models.TradingType.SPOT,
        )
        assert len(assets) == 1
        assert assets[0].symbol == "SPOT-ASSET"

    def test_flattens_all_buckets_when_trading_type_is_none(self):
        account = _account_with_asset_buckets(
            protocol_models.TradingType.SPOT,
            protocol_models.TradingType.FUTURES,
        )
        assets = exchange_account_resolver_module.detailed_assets_from_account(account, None)
        assert {asset.symbol for asset in assets} == {"SPOT-ASSET", "FUTURES-ASSET"}

    def test_raises_when_matching_bucket_missing(self):
        account = _account_with_asset_buckets(protocol_models.TradingType.SPOT)
        with pytest.raises(node_errors.InvalidAutomationConfigurationError):
            exchange_account_resolver_module.detailed_assets_from_account(
                account,
                protocol_models.TradingType.FUTURES,
            )

    def test_raises_when_account_assets_missing(self):
        account = account_executor_test_utils.minimal_exchange_account(account_id="acc-1")
        account = account.model_copy(update={"assets": None})
        with pytest.raises(node_errors.InvalidAutomationConfigurationError):
            exchange_account_resolver_module.detailed_assets_from_account(
                account,
                protocol_models.TradingType.SPOT,
            )


def _evaluator_configuration_with_symbols(symbols: list[str]) -> protocol_models.EvaluatorConfiguration:
    return protocol_models.EvaluatorConfiguration(
        symbols=symbols,
        include_in_construction_candle=False,
        configuration=protocol_models.EvaluatorConfigurationConfiguration(
            protocol_models.RSIMomentumEvaluatorConfiguration(
                configuration_type=protocol_models.EvaluatorType.RSIMOMENTUMEVALUATOR,
                period_length=12,
                long_threshold=50,
                short_threshold=70,
            )
        ),
    )


class TestStrategyTradedSymbols:
    def test_dca_returns_explicit_symbols_when_set(self):
        dca_configuration = _minimal_dca_configuration(
            symbols=["BTC/USDT"],
            evaluators=[_evaluator_configuration_with_symbols(["ETH/USDT"])],
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(dca_configuration) == [
            "BTC/USDT"
        ]

    def test_dca_falls_back_to_evaluator_symbols_when_symbols_empty(self):
        dca_configuration = _minimal_dca_configuration(
            symbols=[],
            evaluators=[
                _evaluator_configuration_with_symbols(["BTC/USDT", "ETH/USDT"]),
                _evaluator_configuration_with_symbols(["ETH/USDT"]),
            ],
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(dca_configuration) == [
            "BTC/USDT",
            "ETH/USDT",
        ]
