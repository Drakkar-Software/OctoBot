#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""CoinRabbit ticker-wise DCA helpers for DBOS functional tests."""

from __future__ import annotations

import typing

import octobot_protocol.models as protocol_models_module
import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading

from tests.scheduler.user_actions.user_actions_executor.util import trading_tentacles_test_utils

from . import dca_workflow as dca_workflow_module
from . import price_mocks as price_mocks_module
from . import workflow_common as workflow_common_module

EXCHANGE_INTERNAL_NAME = "coinrabbit"
REFERENCE_MARKET = "USDT@ETH"
TRADED_SYMBOL = "BTC@BTC/USDT@ETH"
FIXED_TRADED_SYMBOL_CLOSE = 100_000.0
INITIAL_REFERENCE_HOLDING = 1000.0

COINRABBIT_DCA_DEFAULT_STRATEGY_ID = "coinrabbit_dca_ticker_wise_functional_strategy"
COINRABBIT_FUNCTIONAL_EXCHANGE_CONFIG_ID = "functional-test-coinrabbit-exchange-config-id"


def default_close_prices_by_symbol() -> dict[str, float]:
    return {TRADED_SYMBOL: FIXED_TRADED_SYMBOL_CLOSE}


def dca_configuration_for_coinrabbit_ticker_wise() -> protocol_models_module.TradingTentaclesConfiguration:
    return trading_tentacles_test_utils.trading_tentacles_configuration(
        name=dca_trading.DCATradingMode.get_name(),
        config=trading_tentacles_test_utils.dca_tentacle_config(
            **{
                dca_trading.DCATradingModeProducer.TRIGGER_MODE: (
                    dca_trading.TriggerMode.ALWAYS_TRIGGER_LONG.value
                ),
                dca_trading.DCATradingMode.TRADING_PAIRS: [TRADED_SYMBOL],
                dca_trading.DCATradingModeConsumer.USE_MARKET_ENTRY_ORDERS: True,
            }
        ),
    )


def protocol_exchange_config_for_coinrabbit_functional() -> protocol_models_module.ExchangeConfig:
    return protocol_models_module.ExchangeConfig(
        id=COINRABBIT_FUNCTIONAL_EXCHANGE_CONFIG_ID,
        name="coinrabbit-main",
        exchange=EXCHANGE_INTERNAL_NAME,
        sandboxed=False,
    )


def protocol_account_for_coinrabbit_functional(
    *,
    account_id: str,
    reference_total: float = INITIAL_REFERENCE_HOLDING,
    account_name: str = "CoinRabbit ticker-wise functional DCA account",
) -> protocol_models_module.Account:
    return protocol_models_module.Account(
        id=account_id,
        name=account_name,
        is_simulated=True,
        created_at=workflow_common_module._FUNCTIONAL_PROTOCOL_ACCOUNT_TS,
        updated_at=workflow_common_module._FUNCTIONAL_PROTOCOL_ACCOUNT_TS,
        assets=[
            protocol_models_module.DetailedAssetsForTradingType(
                trading_type=protocol_models_module.TradingType.SPOT,
                assets=[
                    protocol_models_module.DetailedAsset(
                        symbol=REFERENCE_MARKET,
                        total=reference_total,
                        available=reference_total,
                    )
                ],
            )
        ],
        specifics=protocol_models_module.AccountSpecifics(
            actual_instance=protocol_models_module.ExchangeAccount(
                account_type=protocol_models_module.AccountType.EXCHANGE,
                remote_account_id=account_id,
                exchange_config_ids=[COINRABBIT_FUNCTIONAL_EXCHANGE_CONFIG_ID],
            ),
        ),
    )


def seeded_dca_strategy_for_coinrabbit_wallet(
    *,
    stored_strategy_id: str,
) -> protocol_models_module.Strategy:
    return protocol_models_module.Strategy(
        id=stored_strategy_id,
        version=workflow_common_module.SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
        name="CoinRabbit ticker-wise DCA automation strategy",
        reference_market=REFERENCE_MARKET,
        configuration=protocol_models_module.StrategyConfiguration(
            dca_configuration_for_coinrabbit_ticker_wise(),
        ),
    )


def build_create_dca_user_action(
    *,
    account_id: str,
    name: str,
    strategy_id: str | None = None,
    automation_id: str | None = None,
) -> protocol_models_module.UserAction:
    return dca_workflow_module.build_create_dca_user_action(
        account_id=account_id,
        name=name,
        strategy_id=strategy_id or COINRABBIT_DCA_DEFAULT_STRATEGY_ID,
        automation_id=automation_id,
    )


def tickers_repository_fetch_tickers_close_override(
    get_close_price_for_symbol: typing.Callable[[str], typing.Union[int, float]],
):
    return price_mocks_module.tickers_repository_fetch_tickers_close_override(
        get_close_price_for_symbol,
        traded_symbols=[TRADED_SYMBOL],
    )
