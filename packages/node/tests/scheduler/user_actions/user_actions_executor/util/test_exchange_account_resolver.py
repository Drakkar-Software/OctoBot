import datetime
import typing

import pytest

import octobot_copy.enums as copy_enums
import octobot_protocol.models as protocol_models
import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading
import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading
import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading
import tentacles.Trading.Mode.staggered_orders_trading_mode.staggered_orders_trading as staggered_orders_trading
import tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_trading as simple_market_making_trading

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.util.exchange_account_resolver as exchange_account_resolver_module
import octobot_node.scheduler.user_actions.user_actions_executor.util.trading_tentacles_config as trading_tentacles_config

from ..account import account_executor_test_utils
from . import trading_tentacles_test_utils


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


def _minimal_market_making_configuration(
    *trading_pairs: str,
) -> protocol_models.MarketMakingConfiguration:
    return protocol_models.MarketMakingConfiguration(
        configuration_type=protocol_models.ActionConfigurationType.MARKET_MAKING,
        pair_settings=[
            protocol_models.MarketMakingSymbolConfiguration(
                trading_pair=trading_pair,
                exchange="binanceus",
                reference_price=[
                    protocol_models.MarketMakingReferencePair(
                        exchange="binanceus",
                        pair=trading_pair,
                    )
                ],
                min_spread=0.5,
                max_spread=1.0,
                bids_count=1,
                asks_count=1,
                orders_distribution=protocol_models.MarketMakingOrdersDistribution.LINEAR,
                funds_distribution=protocol_models.MarketMakingFundsDistribution.FLAT,
            )
            for trading_pair in trading_pairs
        ],
    )


def _grid_configuration_from_pair_settings_only(
    pair_settings: list[dict[str, typing.Any]],
    *,
    trading_mode_name: str | None = None,
) -> protocol_models.TradingTentaclesConfiguration:
    return trading_tentacles_test_utils.trading_tentacles_configuration(
        name=trading_mode_name or grid_trading.GridTradingMode.get_name(),
        config={
            grid_trading.GridTradingMode.CONFIG_PAIR_SETTINGS: pair_settings,
        },
    )


def _trading_tentacles_configuration_with_name(
    *,
    trading_mode_name: str,
    config: dict[str, typing.Any],
    evaluators: list[protocol_models.EvaluatorConfiguration] | None = None,
) -> protocol_models.TradingTentaclesConfiguration:
    return trading_tentacles_test_utils.trading_tentacles_configuration(
        name=trading_mode_name,
        config=config,
        evaluators=evaluators,
    )


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
            trading_tentacles_test_utils.index_trading_configuration(
                coins=[("BTC", 1.0)],
                rebalance_trigger_min_percent=5.0,
            )
        )
        assert (
            exchange_account_resolver_module.trading_type_from_strategy(strategy)
            == protocol_models.TradingType.SPOT
        )

    @pytest.mark.parametrize(
        "trading_mode_name",
        [
            index_trading.IndexTradingMode.get_name(),
            trading_tentacles_config.normalize_tentacle_name(index_trading.IndexTradingMode.get_name()),
        ],
    )
    def test_index_configuration_snake_case_name_is_always_spot(self, trading_mode_name: str):
        index_configuration = trading_tentacles_test_utils.index_trading_configuration(
            coins=[("BTC", 1.0)],
            rebalance_trigger_min_percent=5.0,
        ).model_copy(update={"name": trading_mode_name})
        strategy = _strategy_with_configuration(index_configuration)
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
            trading_tentacles_test_utils.grid_trading_configuration(symbol="BTC/USDT")
        )
        assert (
            exchange_account_resolver_module.trading_type_from_strategy(strategy)
            == protocol_models.TradingType.SPOT
        )

    def test_all_futures_symbols_return_futures(self):
        strategy = _strategy_with_configuration(
            trading_tentacles_test_utils.minimal_dca_trading_configuration(
                trading_pairs=["BTC/USDT:USDT"],
            ),
        )
        assert (
            exchange_account_resolver_module.trading_type_from_strategy(strategy)
            == protocol_models.TradingType.FUTURES
        )

    def test_all_option_symbols_return_options(self):
        strategy = _strategy_with_configuration(
            trading_tentacles_test_utils.minimal_dca_trading_configuration(
                trading_pairs=["BTC/USDT:USDT-211225-60000-P"],
            ),
        )
        assert (
            exchange_account_resolver_module.trading_type_from_strategy(strategy)
            == protocol_models.TradingType.OPTIONS
        )

    def test_mixed_symbol_types_raise_ambiguous_trading_type(self):
        strategy = _strategy_with_configuration(
            trading_tentacles_test_utils.minimal_dca_trading_configuration(
                trading_pairs=["BTC/USDT", "BTC/USDT:USDT"],
            ),
        )
        with pytest.raises(node_errors.AmbiguousTradingTypeError):
            exchange_account_resolver_module.trading_type_from_strategy(strategy)

    def test_empty_trading_pairs_raise_unknown_trading_type(self):
        strategy = _strategy_with_configuration(
            trading_tentacles_test_utils.minimal_dca_trading_configuration(trading_pairs=[]),
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


class TestStrategyTradedSymbols:
    def test_dca_falls_back_to_evaluator_symbols_when_trading_pairs_empty(self):
        dca_configuration = trading_tentacles_test_utils.minimal_dca_trading_configuration(
            trading_pairs=[],
            evaluators=[
                trading_tentacles_test_utils.evaluator_configuration_with_symbols(
                    ["BTC/USDT", "ETH/USDT"]
                ),
                trading_tentacles_test_utils.evaluator_configuration_with_symbols(["ETH/USDT"]),
            ],
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(dca_configuration) == [
            "BTC/USDT",
            "ETH/USDT",
        ]

    def test_market_making_returns_pair_settings_trading_pairs(self):
        market_making_configuration = _minimal_market_making_configuration(
            "BTC/USDT",
            "ETH/USDT",
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(
            market_making_configuration
        ) == ["BTC/USDT", "ETH/USDT"]

    @pytest.mark.parametrize(
        "trading_mode_name",
        [
            dca_trading.DCATradingMode.get_name(),
            trading_tentacles_config.normalize_tentacle_name(dca_trading.DCATradingMode.get_name()),
        ],
    )
    def test_dca_returns_config_trading_pairs(
        self,
        trading_mode_name: str,
    ):
        dca_configuration = _trading_tentacles_configuration_with_name(
            trading_mode_name=trading_mode_name,
            config={
                dca_trading.DCATradingMode.TRADING_PAIRS: ["BTC/USDT", "ETH/USDT"],
            },
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(dca_configuration) == [
            "BTC/USDT",
            "ETH/USDT",
        ]

    def test_unknown_trading_mode_without_evaluators_returns_empty(self):
        trading_configuration = trading_tentacles_test_utils.trading_tentacles_configuration(
            name="CustomTradingMode",
            config={"symbol": "BTC/USDT"},
            evaluators=[],
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(trading_configuration) == []

    @pytest.mark.parametrize(
        "trading_mode_name",
        [
            grid_trading.GridTradingMode.get_name(),
            trading_tentacles_config.normalize_tentacle_name(grid_trading.GridTradingMode.get_name()),
        ],
    )
    def test_grid_returns_pair_settings_pairs(
        self,
        trading_mode_name: str,
    ):
        grid_configuration = _grid_configuration_from_pair_settings_only(
            [
                grid_trading.GridTradingMode.get_default_pair_config(
                    "BTC/USDT",
                    6,
                    2,
                    2,
                    2,
                    False,
                    False,
                    False,
                ),
                grid_trading.GridTradingMode.get_default_pair_config(
                    "ETH/USDT",
                    6,
                    2,
                    2,
                    2,
                    False,
                    False,
                    False,
                ),
            ],
            trading_mode_name=trading_mode_name,
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(grid_configuration) == [
            "BTC/USDT",
            "ETH/USDT",
        ]

    @pytest.mark.parametrize(
        "trading_mode_name",
        [
            staggered_orders_trading.StaggeredOrdersTradingMode.get_name(),
            trading_tentacles_config.normalize_tentacle_name(
                staggered_orders_trading.StaggeredOrdersTradingMode.get_name()
            ),
        ],
    )
    def test_staggered_orders_returns_pair_settings_pairs(
        self,
        trading_mode_name: str,
    ):
        staggered_configuration = _trading_tentacles_configuration_with_name(
            trading_mode_name=trading_mode_name,
            config={
                staggered_orders_trading.StaggeredOrdersTradingMode.CONFIG_PAIR_SETTINGS: [
                    {
                        staggered_orders_trading.StaggeredOrdersTradingMode.CONFIG_PAIR: "BTC/USDT"
                    },
                    {
                        staggered_orders_trading.StaggeredOrdersTradingMode.CONFIG_PAIR: "ETH/USDT"
                    },
                ],
            },
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(
            staggered_configuration
        ) == ["BTC/USDT", "ETH/USDT"]

    @pytest.mark.parametrize(
        "trading_mode_name",
        [
            simple_market_making_trading.SimpleMarketMakingTradingMode.get_name(),
            trading_tentacles_config.normalize_tentacle_name(
                simple_market_making_trading.SimpleMarketMakingTradingMode.get_name()
            ),
        ],
    )
    def test_simple_market_making_returns_trading_pair_from_pair_settings(
        self,
        trading_mode_name: str,
    ):
        simple_market_making_configuration = _trading_tentacles_configuration_with_name(
            trading_mode_name=trading_mode_name,
            config={
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: [
                    {
                        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: (
                            "BTC/USDT"
                        )
                    },
                    {
                        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: (
                            "ETH/USDT"
                        )
                    },
                ],
            },
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(
            simple_market_making_configuration
        ) == ["BTC/USDT", "ETH/USDT"]

    @pytest.mark.parametrize(
        "trading_mode_name",
        [
            index_trading.IndexTradingMode.get_name(),
            trading_tentacles_config.normalize_tentacle_name(index_trading.IndexTradingMode.get_name()),
        ],
    )
    def test_index_returns_symbols_from_index_content(
        self,
        trading_mode_name: str,
    ):
        index_configuration = _trading_tentacles_configuration_with_name(
            trading_mode_name=trading_mode_name,
            config={
                index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
                    {
                        copy_enums.DistributionKeys.NAME: "BTC",
                        copy_enums.DistributionKeys.VALUE: 1.0,
                    }
                ],
            },
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(
            index_configuration,
            reference_market="USDT",
        ) == ["BTC/USDT"]

    def test_pair_settings_deduplicates_symbols(self):
        grid_configuration = _grid_configuration_from_pair_settings_only(
            [
                {"pair": "BTC/USDT"},
                {"pair": "ETH/USDT"},
                {"pair": "BTC/USDT"},
            ]
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(grid_configuration) == [
            "BTC/USDT",
            "ETH/USDT",
        ]

    def test_returns_empty_list_when_no_symbol_source_found(self):
        trading_configuration = trading_tentacles_test_utils.trading_tentacles_configuration(
            name=dca_trading.DCATradingMode.get_name(),
            config={},
            evaluators=[],
        )
        assert exchange_account_resolver_module._strategy_traded_symbols(trading_configuration) == []

    def test_raises_for_unsupported_configuration_type(self):
        copy_configuration = protocol_models.CopyConfiguration(
            configuration_type=protocol_models.ActionConfigurationType.COPY,
            strategy_id="copied-strategy",
        )
        with pytest.raises(
            node_errors.InvalidAutomationConfigurationError,
            match="Unsupported strategy configuration type for trading type inference: CopyConfiguration",
        ):
            exchange_account_resolver_module._strategy_traded_symbols(copy_configuration)
