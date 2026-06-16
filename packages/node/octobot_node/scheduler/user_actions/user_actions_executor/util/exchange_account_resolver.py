#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import typing

import octobot_commons.constants as commons_constants
import octobot_commons.errors as commons_errors
import octobot_commons.symbols.symbol_util as symbol_util_module
import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.util.trading_tentacles_config as trading_tentacles_config


def get_primary_exchange_config_id(
    exchange_account: protocol_models.ExchangeAccount,
) -> str:
    exchange_config_ids = exchange_account.exchange_config_ids
    if not exchange_config_ids:
        raise node_errors.InvalidUserActionPayloadError(
            "ExchangeAccount.exchange_config_ids must not be empty."
        )
    if len(exchange_config_ids) > 1:
        raise node_errors.AmbiguousExchangeConfigError(
            "ExchangeAccount.exchange_config_ids must contain exactly one exchange config id."
        )
    return exchange_config_ids[0]


def get_exchange_config(
    user_id: str,
    exchange_account: protocol_models.ExchangeAccount,
) -> protocol_models.ExchangeConfig:
    exchange_config_id = get_primary_exchange_config_id(exchange_account)
    try:
        return collection_providers.AccountProvider.instance().get_exchange_config(
            user_id,
            exchange_config_id,
        )
    except collection_errors.ItemNotFoundError as err:
        raise node_errors.InvalidUserActionPayloadError(
            f"Exchange config {exchange_config_id!r} not found for address {user_id!r}: {err}"
        ) from err


def trading_type_from_strategy(
    strategy: protocol_models.Strategy,
) -> protocol_models.TradingType | None:
    configuration_wrapper = strategy.configuration
    if configuration_wrapper is None or configuration_wrapper.actual_instance is None:
        raise node_errors.InvalidAutomationConfigurationError(
            "Strategy.configuration.actual_instance is required to infer trading type."
        )
    inner_configuration = configuration_wrapper.actual_instance

    if isinstance(inner_configuration, protocol_models.TradingTentaclesConfiguration):
        trading_mode_class = trading_tentacles_config.get_trading_mode_class_from_tentacle_name(
            inner_configuration.name
        )
        if trading_mode_class is not None and trading_mode_class.__name__ == "IndexTradingMode":
            return protocol_models.TradingType.SPOT
    if isinstance(
        inner_configuration,
        (
            protocol_models.CopyConfiguration,
            protocol_models.GenericWorkflowConfiguration,
            protocol_models.GenericProcessConfiguration,
        ),
    ):
        return None

    traded_symbols = _strategy_traded_symbols(
        inner_configuration,
        reference_market=strategy.reference_market,
    )
    return _trading_type_from_traded_symbols(traded_symbols)


def detailed_assets_from_account(
    account: protocol_models.Account,
    trading_type: protocol_models.TradingType | None,
) -> list[protocol_models.DetailedAsset]:
    account_assets = account.assets
    if not account_assets:
        raise node_errors.InvalidAutomationConfigurationError(
            "Account.assets is required to build automation configuration."
        )

    if trading_type is None:
        detailed_assets: list[protocol_models.DetailedAsset] = []
        for assets_for_trading_type in account_assets:
            detailed_assets.extend(assets_for_trading_type.assets or [])
    else:
        matching_assets_for_trading_type = next(
            (
                assets_for_trading_type
                for assets_for_trading_type in account_assets
                if assets_for_trading_type.trading_type == trading_type
            ),
            None,
        )
        if matching_assets_for_trading_type is None:
            raise node_errors.InvalidAutomationConfigurationError(
                f"Account.assets has no bucket for trading type {trading_type.value!r}."
            )
        detailed_assets = list(matching_assets_for_trading_type.assets or [])

    if not detailed_assets:
        raise node_errors.InvalidAutomationConfigurationError(
            "Account.assets must contain at least one DetailedAsset."
        )
    return detailed_assets


def _strategy_traded_symbols(
    inner_configuration: typing.Any,
    *,
    reference_market: str | None = None,
) -> list[str]:
    if isinstance(inner_configuration, protocol_models.MarketMakingConfiguration):
        return [
            pair_setting.trading_pair
            for pair_setting in (inner_configuration.pair_settings or [])
        ]
    if isinstance(inner_configuration, protocol_models.TradingTentaclesConfiguration):
        return trading_tentacles_config.get_trading_tentacles_traded_symbols(
            inner_configuration,
            reference_market=reference_market,
        )
    raise node_errors.InvalidAutomationConfigurationError(
        f"Unsupported strategy configuration type for trading type inference: {type(inner_configuration).__name__}."
    )


def _trading_type_from_traded_symbols(
    traded_symbols: list[str],
) -> protocol_models.TradingType:
    try:
        exchange_type = symbol_util_module.trading_type_from_traded_symbols(traded_symbols)
    except commons_errors.AmbiguousTradedSymbolsTradingTypeError as err:
        raise node_errors.AmbiguousTradingTypeError(str(err)) from err
    except ValueError as err:
        raise node_errors.UnknownTradingTypeError(str(err)) from err
    try:
        return commons_constants.EXCHANGE_TYPE_TO_TRADING_TYPE[exchange_type]
    except KeyError as err:
        raise node_errors.UnknownTradingTypeError(
            f"Unsupported exchange type {exchange_type!r} inferred from traded symbols."
        ) from err
