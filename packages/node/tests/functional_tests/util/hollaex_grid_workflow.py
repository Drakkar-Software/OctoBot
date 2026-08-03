#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""Grid-specific helpers for Hollaex (Earn Curve) automation DBOS functional tests."""

from __future__ import annotations

import datetime

import octobot_commons.symbols as symbols_module
import octobot_protocol.models as protocol_models_module
import octobot_trading.exchanges.connectors.ccxt.ccxt_clients_cache as ccxt_clients_cache_module

from tests.scheduler.user_actions.user_actions_executor.util import trading_tentacles_test_utils

from . import grid_workflow as grid_workflow_module
from . import workflow_common as workflow_common_module

EARN_CURVE_API_URL = "https://www.earncurve.com.au/api"
HOLLAEX_EXCHANGE_INTERNAL_NAME = "hollaex"
EARN_CURVE_GRID_SYMBOL = "BTC/USDT"

HOLLAEX_EARNCURVE_EXCHANGE_CONFIG_ID = "functional-hollaex-earncurve-exchange-config-id"
HOLLAEX_EARNCURVE_GRID_DEFAULT_STRATEGY_ID = "hollaex-earncurve-grid-functional-default-strategy"
_FUNCTIONAL_PROTOCOL_ACCOUNT_TS = datetime.datetime(2026, 4, 1, 12, 0, 0, tzinfo=datetime.UTC)


def exchange_internal_name() -> str:
    return HOLLAEX_EXCHANGE_INTERNAL_NAME


def protocol_exchange_config_for_hollaex_grid_functional() -> protocol_models_module.ExchangeConfig:
    return protocol_models_module.ExchangeConfig(
        id=HOLLAEX_EARNCURVE_EXCHANGE_CONFIG_ID,
        name="earncurve-main",
        exchange=exchange_internal_name(),
        sandboxed=False,
        url=EARN_CURVE_API_URL,
    )


def protocol_exchange_account_for_hollaex_grid_functional(
    *,
    remote_account_id: str,
) -> protocol_models_module.ExchangeAccount:
    return protocol_models_module.ExchangeAccount(
        account_type=protocol_models_module.AccountType.EXCHANGE,
        remote_account_id=remote_account_id,
        exchange_config_ids=[HOLLAEX_EARNCURVE_EXCHANGE_CONFIG_ID],
    )


def protocol_account_for_hollaex_functional(
    *,
    account_id: str,
    quote_total: float,
    quote_symbol: str,
    account_name: str = "Hollaex Earn Curve functional test account",
) -> protocol_models_module.Account:
    return protocol_models_module.Account(
        id=account_id,
        name=account_name,
        is_simulated=True,
        created_at=_FUNCTIONAL_PROTOCOL_ACCOUNT_TS,
        updated_at=_FUNCTIONAL_PROTOCOL_ACCOUNT_TS,
        assets=[
            protocol_models_module.DetailedAssetsForTradingType(
                trading_type=protocol_models_module.TradingType.SPOT,
                assets=[
                    protocol_models_module.DetailedAsset(
                        symbol=quote_symbol,
                        total=quote_total,
                        available=quote_total,
                    )
                ],
            )
        ],
        specifics=protocol_models_module.AccountSpecifics(
            actual_instance=protocol_exchange_account_for_hollaex_grid_functional(
                remote_account_id=account_id,
            ),
        ),
    )


def grid_configuration_for_symbol(
    symbol: str,
) -> protocol_models_module.TradingTentaclesConfiguration:
    return trading_tentacles_test_utils.grid_trading_configuration(
        symbol=symbol,
        spread=grid_workflow_module.GRID_SPREAD,
        increment=grid_workflow_module.GRID_INCREMENT,
        buy_count=2,
        sell_count=2,
        enable_trailing_up=False,
        enable_trailing_down=False,
        order_by_order_trailing=False,
    )


def seeded_grid_strategy_for_hollaex_functional_wallet(
    *,
    stored_strategy_id: str,
    symbol: str = EARN_CURVE_GRID_SYMBOL,
    reference_market: str = "USDT",
) -> protocol_models_module.Strategy:
    return protocol_models_module.Strategy(
        id=stored_strategy_id,
        version=workflow_common_module.SIMULATOR_FUNCTIONAL_STRATEGY_VERSION,
        name="Hollaex Earn Curve grid automation strategy",
        reference_market=reference_market,
        configuration=protocol_models_module.StrategyConfiguration(
            grid_configuration_for_symbol(symbol),
        ),
    )


def build_create_grid_user_action(
    *,
    account_id: str,
    name: str,
    strategy_id: str | None = None,
    emit_signals: bool | None = None,
    automation_id: str | None = None,
) -> protocol_models_module.UserAction:
    return grid_workflow_module.build_create_grid_user_action(
        account_id=account_id,
        name=name,
        strategy_id=strategy_id or HOLLAEX_EARNCURVE_GRID_DEFAULT_STRATEGY_ID,
        emit_signals=emit_signals,
        automation_id=automation_id,
    )


def _earn_curve_client_cache_keys() -> list[str]:
    earn_curve_cache_keys: set[str] = set()
    for markets_cache in (
        ccxt_clients_cache_module._MARKETS_BY_EXCHANGE,
        ccxt_clients_cache_module._SHARED_MARKETS_EXCHANGE_BY_EXCHANGE,
    ):
        for client_key in markets_cache.keys():
            if EARN_CURVE_API_URL in client_key:
                earn_curve_cache_keys.add(client_key)
    return sorted(earn_curve_cache_keys)


def _cached_markets_for_client_key(client_key: str) -> list[dict]:
    markets_cache = ccxt_clients_cache_module._MARKETS_BY_EXCHANGE
    if client_key in markets_cache:
        return markets_cache[client_key]
    shared_markets_exchange = ccxt_clients_cache_module._SHARED_MARKETS_EXCHANGE_BY_EXCHANGE.get(
        client_key
    )
    if shared_markets_exchange is not None:
        return list(shared_markets_exchange.markets.values())
    return []


def assert_earncurve_markets_cached_after_automation_init() -> None:
    earn_curve_cache_keys = _earn_curve_client_cache_keys()
    assert earn_curve_cache_keys, (
        f"no markets cache entry for Earn Curve URL {EARN_CURVE_API_URL!r}; "
        "normal automation init did not fetch/cache markets"
    )
    cached_markets = _cached_markets_for_client_key(earn_curve_cache_keys[0])
    assert cached_markets, "Earn Curve markets cache entry must be non-empty after automation init"
    cached_symbols = {market["symbol"] for market in cached_markets}
    assert EARN_CURVE_GRID_SYMBOL in cached_symbols, (
        f"{EARN_CURVE_GRID_SYMBOL!r} must be in cached Earn Curve markets; got sample: {sorted(cached_symbols)[:10]}"
    )


def quote_symbol_for_grid_symbol(grid_symbol: str) -> str:
    return symbols_module.parse_symbol(grid_symbol).quote
