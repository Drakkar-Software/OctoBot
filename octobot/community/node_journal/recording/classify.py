#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import octobot_protocol.models as protocol_models
import octobot_trading.util.protocol_trading_mapping as protocol_trading_mapping

import octobot.constants as constants
import octobot_sync.sync.collection_backend.errors as collection_errors

import octobot.community.node_journal.enums as journal_enums


def classify_octobot_kind(
    strategy: protocol_models.Strategy,
) -> tuple[journal_enums.OctobotKind, str | None]:
    configuration_wrapper = strategy.configuration
    if configuration_wrapper is None or configuration_wrapper.actual_instance is None:
        return journal_enums.OctobotKind.MANUAL, None
    inner_configuration = configuration_wrapper.actual_instance
    if isinstance(inner_configuration, protocol_models.GenericProcessConfiguration):
        return journal_enums.OctobotKind.MANUAL, None
    if isinstance(inner_configuration, protocol_models.MarketMakingConfiguration):
        return journal_enums.OctobotKind.MARKET_MAKING, None
    if isinstance(inner_configuration, protocol_models.CopyConfiguration):
        return journal_enums.OctobotKind.FLOW, journal_enums.FlowSubtype.COPY.value
    if isinstance(inner_configuration, protocol_models.SignalBotConfiguration):
        return journal_enums.OctobotKind.FLOW, journal_enums.FlowSubtype.SIGNAL_BOT.value
    if isinstance(inner_configuration, protocol_models.GenericWorkflowConfiguration):
        return journal_enums.OctobotKind.FLOW, journal_enums.FlowSubtype.AI_AGENTS.value
    if isinstance(inner_configuration, protocol_models.TradingTentaclesConfiguration):
        tentacle_name = inner_configuration.name or ""
        if not tentacle_name:
            return journal_enums.OctobotKind.FLOW, journal_enums.FlowSubtype.OTHER.value
        return journal_enums.OctobotKind.FLOW, tentacle_name
    return journal_enums.OctobotKind.FLOW, journal_enums.FlowSubtype.OTHER.value


def configuration_type_from_strategy(strategy: protocol_models.Strategy) -> journal_enums.ConfigurationType:
    configuration_wrapper = strategy.configuration
    if configuration_wrapper is None or configuration_wrapper.actual_instance is None:
        return journal_enums.ConfigurationType.GENERIC_PROCESS
    inner_configuration = configuration_wrapper.actual_instance
    if isinstance(inner_configuration, protocol_models.GenericProcessConfiguration):
        return journal_enums.ConfigurationType.GENERIC_PROCESS
    if isinstance(inner_configuration, protocol_models.MarketMakingConfiguration):
        return journal_enums.ConfigurationType.MARKET_MAKING
    if isinstance(inner_configuration, protocol_models.CopyConfiguration):
        return journal_enums.ConfigurationType.COPY
    if isinstance(inner_configuration, protocol_models.SignalBotConfiguration):
        return journal_enums.ConfigurationType.SIGNAL_BOT
    if isinstance(inner_configuration, protocol_models.GenericWorkflowConfiguration):
        return journal_enums.ConfigurationType.GENERIC_WORKFLOW
    if isinstance(inner_configuration, protocol_models.TradingTentaclesConfiguration):
        return journal_enums.ConfigurationType.TRADING_TENTACLES
    return journal_enums.ConfigurationType.GENERIC_PROCESS


def resolve_account_exchange_name(
    checked_account: protocol_models.Account,
    user_id: str,
) -> str:
    specifics = checked_account.specifics
    if specifics is None or specifics.actual_instance is None:
        return constants.METRICS_GENERIC_EXCHANGE_NAME
    exchange_account = specifics.actual_instance
    if not isinstance(exchange_account, protocol_models.ExchangeAccount):
        return constants.METRICS_GENERIC_EXCHANGE_NAME
    config_ids = exchange_account.exchange_config_ids or []
    if not config_ids:
        return constants.METRICS_GENERIC_EXCHANGE_NAME
    import octobot_sync.sync.collection_providers as collection_providers
    try:
        exchange_config = collection_providers.AccountProvider.instance().get_exchange_config(
            user_id,
            config_ids[0],
        )
    except collection_errors.CollectionNoDataError:
        return constants.METRICS_GENERIC_EXCHANGE_NAME
    exchange_type = protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(
        protocol_models.TradingType.SPOT
    )
    if exchange_type is None:
        return exchange_config.exchange
    return exchange_config.exchange
