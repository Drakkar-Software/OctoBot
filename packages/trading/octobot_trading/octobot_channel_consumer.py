#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import enum

import async_channel.channels as channel_instances
import octobot_commons.channels_name as channels_name
import octobot_commons.logging as logging
import octobot_commons.enums as enums
import octobot_commons.constants as commons_constants
import octobot_commons.errors as commons_errors

import octobot_trading.errors as errors
import octobot_trading.exchanges as exchanges
import octobot_trading.modes as modes
import octobot_trading.util as util

OCTOBOT_CHANNEL_TRADING_CONSUMER_LOGGER_TAG = "OctoBotChannelTradingConsumer"


class OctoBotChannelTradingActions(enum.Enum):
    """
    OctoBot Channel consumer supported actions
    """

    EXCHANGE = "exchange"


class OctoBotChannelTradingDataKeys(enum.Enum):
    """
    OctoBot Channel consumer supported data keys
    """

    EXCHANGE_NAME = "exchange_name"
    EXCHANGE_CONFIG = "exchange_config"
    EXCHANGE_ID = "exchange_id"
    BACKTESTING = "backtesting"
    MATRIX_ID = "matrix_id"
    TENTACLES_SETUP_CONFIG = "tentacles_setup_config"
    ENABLE_REALTIME_DATA_FETCHING = "enable_realtime_data_fetching"


async def octobot_channel_callback(bot_id, subject, action, data) -> None:
    """
    OctoBot channel consumer callback
    :param bot_id: the callback bot id
    :param subject: the callback subject
    :param action: the callback action
    :param data: the callback data
    """
    if subject == enums.OctoBotChannelSubjects.CREATION.value:
        await _handle_creation(bot_id, action, data)


async def _handle_creation(bot_id, action, data):
    if action == OctoBotChannelTradingActions.EXCHANGE.value:
        exchange_name = data.get(OctoBotChannelTradingDataKeys.EXCHANGE_NAME.value, None)
        try:
            config = data[OctoBotChannelTradingDataKeys.EXCHANGE_CONFIG.value]
            exchange_builder = exchanges.create_exchange_builder_instance(config, exchange_name) \
                .has_matrix(data[OctoBotChannelTradingDataKeys.MATRIX_ID.value]) \
                .enable_realtime_data_fetching(data.get(OctoBotChannelTradingDataKeys.ENABLE_REALTIME_DATA_FETCHING.value, False)) \
                .use_tentacles_setup_config(data[OctoBotChannelTradingDataKeys.TENTACLES_SETUP_CONFIG.value]) \
                .set_bot_id(bot_id)
            try:
                modes.get_activated_trading_mode(data[OctoBotChannelTradingDataKeys.TENTACLES_SETUP_CONFIG.value])
            except commons_errors.ConfigTradingError:
                logging.get_logger(OCTOBOT_CHANNEL_TRADING_CONSUMER_LOGGER_TAG).error(
                    f"No configured trading mode. In order to trade, selected a profile with a trading mode."
                )
                # do not raise on missing trading mode
                exchange_builder.disable_trading_mode()
            _set_exchange_type_details(exchange_builder, config, data[OctoBotChannelTradingDataKeys.BACKTESTING.value])
            await exchange_builder.build()
            await channel_instances.get_chan_at_id(
                channels_name.OctoBotChannelsName.OCTOBOT_CHANNEL.value, bot_id
            ).get_internal_producer().send(
                bot_id=bot_id,
                subject=enums.OctoBotChannelSubjects.NOTIFICATION.value,
                action=action,
                data={OctoBotChannelTradingDataKeys.EXCHANGE_ID.value: exchange_builder.exchange_manager.id}
            )
        except errors.TradingModeIncompatibility as e:
            logging.get_logger(OCTOBOT_CHANNEL_TRADING_CONSUMER_LOGGER_TAG).error(
                f"Error when initializing trading mode, {exchange_name} "
                f"exchange connection is closed to increase performances: {e}")
        except errors.UnreachableExchange as e:
            logging.get_logger(OCTOBOT_CHANNEL_TRADING_CONSUMER_LOGGER_TAG).exception(
                e,
                True,
                f"Error when connecting to {exchange_name} exchange, please check your internet connection ({e})."
            )
        except errors.NotSupported as e:
            logging.get_logger(OCTOBOT_CHANNEL_TRADING_CONSUMER_LOGGER_TAG).exception(e, True, str(e))
        except Exception as e:
            logging.get_logger(OCTOBOT_CHANNEL_TRADING_CONSUMER_LOGGER_TAG).exception(
                e,
                True,
                f"Error when creating a new {exchange_name} exchange connexion: {e.__class__.__name__} {e}"
            )


def _set_exchange_type_details(exchange_builder, config, backtesting):
    # real, simulator, backtesting
    if util.is_trader_enabled(config):
        exchange_builder.is_real()
    elif util.is_trader_simulator_enabled(config):
        exchange_builder.is_simulated()
    if backtesting is not None:
        exchange_builder.is_simulated()
        exchange_builder.is_rest_only()
        exchange_builder.is_backtesting(backtesting)
    # use exchange sandbox
    exchange_builder.is_sandboxed(
        config[commons_constants.CONFIG_EXCHANGES].get(exchange_builder.exchange_name, {}).get(
            commons_constants.CONFIG_EXCHANGE_SANDBOXED, False)
    )
    # exchange trading type
    config_exchange_type = config[commons_constants.CONFIG_EXCHANGES].get(exchange_builder.exchange_name, {}).get(
        commons_constants.CONFIG_EXCHANGE_TYPE, exchanges.get_default_exchange_type(exchange_builder.exchange_name))
    exchange_builder.is_using_exchange_type(config_exchange_type)

    # rest, web socket
    if config[commons_constants.CONFIG_EXCHANGES].get(exchange_builder.exchange_name, {}).get(
            commons_constants.CONFIG_EXCHANGE_REST_ONLY, False):
        exchange_builder.is_rest_only()
