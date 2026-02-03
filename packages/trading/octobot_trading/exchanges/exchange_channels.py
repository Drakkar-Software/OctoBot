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
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import async_channel.producer as channel_producer
import async_channel.util as channel_util

import octobot_commons.tentacles_management as tentacles_management

import octobot_trading.exchanges as exchanges
import octobot_trading.exchange_channel as exchange_channel


async def create_exchange_channels(exchange_manager) -> None:
    """
    Create exchange related channels
    # TODO filter creation --> not required if pause is managed
    :param exchange_manager: the related exchange manager
    """
    for exchange_channel_class_type in [exchange_channel.ExchangeChannel, exchange_channel.TimeFrameExchangeChannel]:
        await channel_util.create_all_subclasses_channel(exchange_channel_class_type, exchange_channel.set_chan,
                                                         is_synchronized=exchange_manager.is_backtesting,
                                                         exchange_manager=exchange_manager)


async def create_exchange_producers(exchange_manager, forced_producers=None) -> None:
    """
    Create exchange channels producers according to exchange manager context (backtesting, simulator, real)
    :param exchange_manager: the related exchange manager
    :param forced_producers: producers to create no anyway
    """
    import octobot_trading.personal_data as personal_data

    # Always init exchange user data first on real trading
    if _should_create_authenticated_producers(exchange_manager):
        await _create_producers(exchange_manager, personal_data.AUTHENTICATED_UPDATER_PRODUCERS)

    # Real data producers
    if _should_create_unauthenticated_producers(exchange_manager):
        import octobot_trading.exchange_data as exchange_data
        await _create_producers(exchange_manager, exchange_data.UNAUTHENTICATED_UPDATER_PRODUCERS)

    # Simulated producers
    if _should_create_simulated_producers(exchange_manager):
        await _create_producers(exchange_manager, personal_data.AUTHENTICATED_UPDATER_SIMULATOR_PRODUCERS)

    if forced_producers:
        await _create_producers(exchange_manager, forced_producers)


def _should_create_authenticated_producers(exchange_manager):
    """
    :param exchange_manager: the related exchange manager
    :return: True if should create authenticated producers
    """
    return exchange_manager.exchange.authenticated() \
           and exchange_manager.trader and exchange_manager.is_trading \
           and not (exchange_manager.is_simulated
                    or exchange_manager.is_backtesting
                    or exchange_manager.exchange_only)


def _should_create_simulated_producers(exchange_manager):
    """
    :param exchange_manager: the related exchange manager
    :return: True if should create simulated producers
    """
    return (not exchange_manager.exchange.authenticated()
            or exchange_manager.is_simulated
            or exchange_manager.is_backtesting) \
           and exchange_manager.trader and exchange_manager.is_trading and not exchange_manager.exchange_only


def _should_create_unauthenticated_producers(exchange_manager):
    """
    :param exchange_manager: the related exchange manager
    :return: True if should create unauthenticated real data producers
    """
    return not exchange_manager.is_backtesting


async def _create_producers(exchange_manager, producers_classes) -> None:
    """
    Create a list of producer instance
    :param exchange_manager: the related exchange manager
    :param producers_classes: the list of producer classes
    """
    for updater in producers_classes:
        await _create_producer(exchange_manager, updater)


async def _create_producer(exchange_manager, producer) -> channel_producer.Producer:
    """
    Create a producer instance
    :param exchange_manager: the related exchange manager
    :param producer: the producer to create
    :return: the producer instance created
    """
    should_start_producer = True
    producer_instance = producer(exchange_channel.get_chan(producer.CHANNEL_NAME, exchange_manager.id))
    if exchanges.is_channel_managed_by_websocket(exchange_manager, producer.CHANNEL_NAME):
        # websocket is handling this channel: initialize data if required
        exchange_manager.logger.debug(
            f"{exchange_manager.exchange_name} {producer.CHANNEL_NAME} channel is updated by websocket feed"
        )
        should_start_producer = \
            not exchanges.is_channel_fully_managed_by_websocket(exchange_manager, producer.CHANNEL_NAME)
        if exchanges.is_websocket_feed_requiring_init(exchange_manager, producer.CHANNEL_NAME):
            try:
                producer_instance.trigger_single_update()
            except Exception as e:
                exchange_manager.logger.exception(e, True,
                                                  f"Error when initializing data for {producer.CHANNEL_NAME} "
                                                  f"channel required by websocket: {e}")
    if should_start_producer:
        # no websocket for this channel (or channel is not fully managed by ws): start a producer
        exchange_manager.logger.debug(
            f"{exchange_manager.exchange_name} {producer.CHANNEL_NAME} channel "
            f"is updated by {producer_instance.__class__.__name__}"
        )
        await producer_instance.run()
    else:
        # register producer to be able to reach it later on in modify() if needed
        await producer_instance.channel.register_producer(producer_instance)
    return producer_instance


async def create_authenticated_producer_from_parent(exchange_manager,
                                                    parent_producer_class,
                                                    force_register_producer=False):
    """
    Create an authenticated producer from its parent class
    :param exchange_manager: the related exchange manager
    :param parent_producer_class: the authenticated producer parent class
    :param force_register_producer: force the producer to register to its channel
    """
    producer = _get_authenticated_producer_from_parent(parent_producer_class)
    if producer is not None:
        producer_instance = await _create_producer(exchange_manager, producer)
        if force_register_producer:
            await producer_instance.channel.register_producer(producer_instance)


def _get_authenticated_producer_from_parent(parent_producer_class):
    """
    :param parent_producer_class: the authenticated producer parent class
    :return: the authenticated producer that inherit from parent_producer_class
    """
    import octobot_trading.personal_data as personal_data
    for authenticated_producer_candidate in personal_data.AUTHENTICATED_UPDATER_PRODUCERS:
        if tentacles_management.default_parent_inspection(authenticated_producer_candidate, parent_producer_class):
            return authenticated_producer_candidate
    return None


def requires_refresh_trigger(exchange_manager, channel):
    """
    Return True if the given channel is to be updated artificially (ex: via channel updater). In this case it
    is necessary to trigger a manual update to get the exact picture at a given time (last updater push might
    have been a few seconds ago)
    Return False if this channels updates by its exchange_manager
    and manual refresh trigger is not necessary (ex: websocket feed)
    :param exchange_manager: the related exchange manager
    :param channel: name of the channel
    :return: True if it should be refreshed via a manual trigger to be exactly up to date
    """
    return not (
        exchanges.is_channel_managed_by_websocket(exchange_manager, channel)
        or _is_updater_refresh_disabled(exchange_manager)
    )


def _is_updater_refresh_disabled(exchange_manager):
    # channel updaters are disabled on exchange_only mode
    return exchange_manager.exchange_only
