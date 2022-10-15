#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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
import uuid
import gmqtt
import json
import zlib
import asyncio
import packaging.version as packaging_version

import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.constants as commons_constants
import octobot.community.errors as errors
import octobot.community.feeds.abstract_feed as abstract_feed
import octobot.constants as constants


class CommunityMQTTFeed(abstract_feed.AbstractFeed):
    MQTT_VERSION = gmqtt.constants.MQTTv311
    MQTT_BROKER_PORT = 1883
    RECONNECT_DELAY = 15
    MAX_MESSAGE_ID_CACHE_SIZE = 100
    MAX_SUBSCRIPTION_ATTEMPTS = 5
    DISABLE_RECONNECT_VALUE = -2
    DEVICE_CREATE_TIMEOUT = 5 * commons_constants.MINUTE_TO_SECONDS
    DEVICE_CREATION_REFRESH_DELAY = 2

    # Quality of Service level determines the reliability of the data flow between a client and a message broker.
    # The message may be sent in three ways:
    # QoS 0: the message will be received at most once (also known as “fire and forget”).
    # QoS 1: the message will be received at least once.
    # QoS 2: the message will be received exactly once.
    # from https://www.scaleway.com/en/docs/iot/iot-hub/concepts/#quality-of-service-levels-(qos)
    default_QOS = 1

    def __init__(self, feed_url, authenticator):
        super().__init__(feed_url, authenticator)
        self.mqtt_version = self.MQTT_VERSION
        self.mqtt_broker_port = self.MQTT_BROKER_PORT
        self.default_QOS = self.default_QOS
        self.associated_gql_bot_id = None

        self._mqtt_client: gmqtt.Client = None
        self._valid_auth = True
        self._device_uuid: str = None
        self._subscription_attempts = 0
        self._subscription_topics = set()
        self._reconnect_task = None
        self._connect_task = None
        self._connected_at_least_once = False
        self._processed_messages = set()

    async def start(self):
        self.should_stop = False
        self._device_uuid = self.authenticator.user_account.get_selected_bot_device_uuid()
        await self._connect()

    async def stop(self):
        self.logger.debug("Stopping ...")
        self.should_stop = True
        await self._stop_mqtt_client()
        if self._reconnect_task is not None and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        if self._connect_task is not None and not self._connect_task.done():
            self._connect_task.cancel()
        self._reset()
        self.logger.debug("Stopped")

    async def restart(self):
        try:
            await self.stop()
            await self.start()
        except Exception as e:
            self.logger.exception(e, True, f"Error when restarting mqtt feed: {e}")

    def _reset(self):
        self._connected_at_least_once = False
        self._subscription_attempts = 0
        self._subscription_topics = set()
        self._connect_task = None
        self._valid_auth = True

    async def _stop_mqtt_client(self):
        if self.is_connected():
            await self._mqtt_client.disconnect()

    def is_connected(self):
        return self._mqtt_client is not None and self._mqtt_client.is_connected

    def can_connect(self):
        return self._valid_auth

    async def register_feed_callback(self, channel_type, callback, identifier=None):
        topic = self._build_topic(channel_type, identifier)
        try:
            self.feed_callbacks[topic].append(callback)
        except KeyError:
            self.feed_callbacks[topic] = [callback]
        if topic not in self._subscription_topics:
            self._subscription_topics.add(topic)
            if self._valid_auth:
                self._subscribe((topic, ))
            else:
                self.logger.error(f"Can't subscribe to {channel_type.name} feed, invalid authentication")

    def remove_device_details(self):
        self._device_uuid = None

    @staticmethod
    def _build_topic(channel_type, identifier):
        return f"{channel_type.value}/{identifier}"

    async def _on_message(self, client, topic, payload, qos, properties):
        uncompressed_payload = zlib.decompress(payload).decode()
        self.logger.debug(f"Received message, client_id: {client._client_id}, topic: {topic}, "
                          f"uncompressed payload: {uncompressed_payload}, QOS: {qos}, properties: {properties}")
        parsed_message = json.loads(uncompressed_payload)
        try:
            self._ensure_supported(parsed_message)
            if self._should_process(parsed_message):
                for callback in self._get_callbacks(topic):
                    await callback(parsed_message)
        except commons_errors.UnsupportedError as e:
            self.logger.error(f"Unsupported message: {e}")

    def _should_process(self, parsed_message):
        if parsed_message[commons_enums.CommunityFeedAttrs.ID.value] in self._processed_messages:
            self.logger.debug(f"Ignored already processed message with id: "
                              f"{parsed_message[commons_enums.CommunityFeedAttrs.ID.value]}")
            return False
        self._processed_messages.add(parsed_message[commons_enums.CommunityFeedAttrs.ID.value])
        if len(self._processed_messages) > self.MAX_MESSAGE_ID_CACHE_SIZE:
            self._processed_messages = [
                message_id
                for message_id in self._processed_messages[self.MAX_MESSAGE_ID_CACHE_SIZE // 2:]
            ]
        return True

    async def send(self, message, channel_type, identifier, **kwargs):
        if not self._valid_auth:
            self.logger.warning(f"Can't send {channel_type.name}, invalid feed authentication.")
            return
        topic = self._build_topic(channel_type, identifier)
        self.logger.debug(f"Sending message on topic: {topic}, message: {message}")
        self._mqtt_client.publish(
            self._build_topic(channel_type, identifier),
            self._build_message(channel_type, message),
            qos=self.default_QOS
        )

    def _get_callbacks(self, topic):
        for callback in self.feed_callbacks.get(topic, ()):
            yield callback

    def _get_channel_type(self, message):
        return commons_enums.CommunityChannelTypes(message[commons_enums.CommunityFeedAttrs.CHANNEL_TYPE.value])

    def _build_message(self, channel_type, message):
        if message:
            return zlib.compress(
                json.dumps({
                    commons_enums.CommunityFeedAttrs.CHANNEL_TYPE.value: channel_type.value,
                    commons_enums.CommunityFeedAttrs.VERSION.value: constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION,
                    commons_enums.CommunityFeedAttrs.VALUE.value: message,
                    commons_enums.CommunityFeedAttrs.ID.value: str(uuid.uuid4()),  # assign unique id to each message
                }).encode()
            )
        return {}

    def _ensure_supported(self, parsed_message):
        if packaging_version.Version(parsed_message[commons_enums.CommunityFeedAttrs.VERSION.value]) \
                < packaging_version.Version(constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION):
            raise commons_errors.UnsupportedError(
                f"Minimum version: {constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION}"
            )

    def _on_connect(self, client, flags, rc, properties):
        self.logger.info(f"Connected, client_id: {client._client_id}")
        # Auto subscribe to known topics (mainly used in case of reconnection)
        self._subscribe(self._subscription_topics)

    def _try_reconnect_if_necessary(self, client):
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect(client))

    async def _reconnect(self, client):
        try:
            await self._stop_mqtt_client()
        except Exception as e:
            self.logger.debug(f"Ignored error while stopping client: {e}.")
        first_reconnect = True
        while not self.should_stop:
            try:
                self.logger.info(f"Reconnecting, client_id: {client._client_id}")
                await self._connect()
                return
            except Exception as e:
                delay = 0 if first_reconnect else self.RECONNECT_DELAY
                first_reconnect = False
                self.logger.debug(f"Error while reconnecting: {e}. Trying again in {delay} seconds.")
                await asyncio.sleep(delay)

    def _on_disconnect(self, client, packet, exc=None):
        if self._connected_at_least_once:
            self.logger.info(f"Disconnected, client_id: {client._client_id}")
            self._try_reconnect_if_necessary(client)
        else:
            if self._connect_task is not None and not self._connect_task.done():
                self._connect_task.cancel()

    def _on_subscribe(self, client, mid, qos, properties):
        # from https://github.com/wialon/gmqtt/blob/master/examples/resubscription.py#L28
        # in order to check if all the subscriptions were successful, we should first get all subscriptions with this
        # particular mid (from one subscription request)
        subscriptions = client.get_subscriptions_by_mid(mid)
        for subscription, granted_qos in zip(subscriptions, qos):
            # in case of bad suback code, we can resend  subscription
            if granted_qos >= gmqtt.constants.SubAckReasonCode.UNSPECIFIED_ERROR.value:
                self.logger.warning(f"Retrying subscribe to {[s.topic for s in subscriptions]}, "
                                    f"client_id: {client._client_id}, mid: {mid}, "
                                    f"reason code: {granted_qos}, properties {properties}")
                if self._subscription_attempts < self.MAX_SUBSCRIPTION_ATTEMPTS * len(subscriptions):
                    self._subscription_attempts += 1
                    client.resubscribe(subscription)
                else:
                    self.logger.error(f"Max subscription attempts reached, stopping subscription "
                                      f"to {[s.topic for s in subscriptions]}. Are you subscribing to this "
                                      f"strategy on your OctoBot account ?")
                    return
            else:
                self._subscription_attempts = 0
                self.logger.info(f"Subscribed, client_id: {client._client_id}, mid {mid}, QOS: {granted_qos}, "
                                 f"properties {properties}")

    def _register_callbacks(self, client):
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        client.on_subscribe = self._on_subscribe

    def _update_client_config(self, client):
        default_config = gmqtt.constants.DEFAULT_CONFIG
        # prevent default auto-reconnect as it loop infinitely on windows long disconnections
        default_config.update({
            'reconnect_retries': self.DISABLE_RECONNECT_VALUE,
        })
        client.set_config(default_config)

    async def _connect(self):
        if self._device_uuid is None:
            self._valid_auth = False
            raise errors.BotError("mqtt device uuid is None, impossible to connect client")
        self._mqtt_client = gmqtt.Client(self.__class__.__name__)
        self._update_client_config(self._mqtt_client)
        self._register_callbacks(self._mqtt_client)
        self._mqtt_client.set_auth_credentials(self._device_uuid, None)
        self.logger.debug(f"Connecting client using device "
                          f"'{self.authenticator.user_account.get_selected_bot_device_name()}'")
        self._connect_task = asyncio.create_task(
            self._mqtt_client.connect(self.feed_url, self.mqtt_broker_port, version=self.MQTT_VERSION)
        )
        try:
            await self._connect_task
            self._connected_at_least_once = True
        except asyncio.CancelledError:
            # got cancelled by on_disconnect, can't connect
            self.logger.error(f"Can't connect to server, please check your device uuid. "
                              f"Current mqtt uuid is: {self._device_uuid}")
            self._valid_auth = False

    def _subscribe(self, topics):
        if not topics:
            self.logger.debug("No topic to subscribe to, skipping subscribe for now")
            return
        subscriptions = [
            gmqtt.Subscription(topic, qos=self.default_QOS)
            for topic in topics
        ]
        self.logger.debug(f"Subscribing to {', '.join(topics)}")
        self._mqtt_client.subscribe(subscriptions)
