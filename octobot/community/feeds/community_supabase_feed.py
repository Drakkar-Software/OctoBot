#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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
import json
import realtime
import packaging.version as packaging_version

import octobot_commons.enums as commons_enums
import octobot_commons.authentication as authentication
import octobot_commons.errors as commons_errors
import octobot.community.supabase_backend.enums as enums
import octobot.community.feeds.abstract_feed as abstract_feed
import octobot.constants as constants


class CommunitySupabaseFeed(abstract_feed.AbstractFeed):
    SCHEMA = "public"
    SIGNALS_TABLE = "signals"
    INSERT_EVENT = "INSERT"
    MAX_MESSAGE_ID_CACHE_SIZE = 100

    def __init__(self, feed_url, authenticator):
        super().__init__(feed_url, authenticator)
        self._realtime_client = authenticator.supabase_client.realtime
        self._processed_messages = []

    def _ensure_supported(self, parsed_message):
        if packaging_version.Version(parsed_message[commons_enums.CommunityFeedAttrs.VERSION.value]) \
                < packaging_version.Version(constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION):
            raise commons_errors.UnsupportedError(
                f"Minimum version: {constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION}"
            )

    def _should_process(self, parsed_message):
        if parsed_message[commons_enums.CommunityFeedAttrs.ID.value] in self._processed_messages:
            self.logger.debug(f"Ignored already processed message with id: "
                              f"{parsed_message[commons_enums.CommunityFeedAttrs.ID.value]}")
            return False
        self._processed_messages.append(parsed_message[commons_enums.CommunityFeedAttrs.ID.value])
        if len(self._processed_messages) > self.MAX_MESSAGE_ID_CACHE_SIZE:
            self._processed_messages = [
                message_id
                for message_id in self._processed_messages[self.MAX_MESSAGE_ID_CACHE_SIZE // 2:]
            ]
        return True

    def _get_callbacks(self, table, identifier):
        for callback in self.feed_callbacks.get(table, {}).get(identifier, tuple()):
            yield callback

    async def _process_message(self, table: str, message: dict):
        try:
            content = message["new"]
            parsed_message = content["signal"]
            self._ensure_supported(parsed_message)
            if self._should_process(parsed_message):
                self.update_last_message_time()
                product_id = content[enums.SignalKeys.PRODUCT_ID.value]
                for callback in self._get_callbacks(table, product_id):
                    await callback(parsed_message)
        except commons_errors.UnsupportedError as err:
            self.logger.error(f"Unsupported message: {err}")
        except Exception as err:
            self.logger.exception(err, True, f"Unexpected error when processing message: {err}")

    async def start(self):
        # handled in supabase client directly, just ensure no subscriptions are pending
        for table in self.feed_callbacks:
            await self._subscribe_to_table_if_necessary(table)

    async def stop(self):
        # handled in supabase client directly
        pass

    async def register_feed_callback(self, channel_type: commons_enums.CommunityChannelTypes, callback, identifier=None):
        self.is_signal_receiver = True
        table = self._get_table(channel_type)
        try:
            self.feed_callbacks[table][identifier].append(callback)
        except KeyError:
            if table not in self.feed_callbacks:
                self.feed_callbacks[table] = {}
            if identifier not in self.feed_callbacks[table]:
                self.feed_callbacks[table][identifier] = [callback]
        await self._subscribe_to_table_if_necessary(table)

    async def _subscribe_to_table_if_necessary(self, table):
        if table not in self.authenticator.supabase_client.get_subscribed_channel_tables():
            if self.authenticator.is_logged_in():
                await self._subscribe_to_table(table)
            else:
                raise authentication.AuthenticationRequired("You need to be authenticated to be able to "
                                                            "connect to signals")

    def _get_table(self, channel_type: commons_enums.CommunityChannelTypes):
        if channel_type is commons_enums.CommunityChannelTypes.SIGNAL:
            return self.SIGNALS_TABLE
        raise NotImplementedError(channel_type)

    async def _subscribe_to_table(self, table):
        channel = await self._realtime_client.channel(self.SCHEMA, table)
        await channel.on(self.INSERT_EVENT, self._message_callback).subscribe(self._subscribed_callback)

    async def _message_callback(self, message: dict):
        self.logger.debug(f"Received message: {message['new']}")
        await self._process_message(message["table"], message)

    async def _subscribed_callback(self, state: str, message: realtime.Message):
        self.logger.debug(f"Subscribe to {self._get_table_from_message(message)}: {state}")

    def _get_table_from_message(self, message: realtime.Message):
        return message.topic.split(":")[-1]

    async def send(self, message, channel_type, identifier, **kwargs):
        self.is_signal_emitter = True
        if not self.authenticator.is_logged_in():
            self.logger.warning(f"Can't send {channel_type.name}, invalid feed authentication.")
            return
        self.logger.info(f"Sending signal on identifier: {identifier}, message: {message}")
        await self.authenticator.supabase_client.send_signal(
            self._get_table(channel_type),
            identifier,
            self._build_message(channel_type, message)
        )

    def _build_message(self, channel_type, message):
        if message:
            return json.dumps({
                commons_enums.CommunityFeedAttrs.CHANNEL_TYPE.value: channel_type.value,
                commons_enums.CommunityFeedAttrs.VERSION.value: constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION,
                commons_enums.CommunityFeedAttrs.VALUE.value: message,
                commons_enums.CommunityFeedAttrs.ID.value: str(uuid.uuid4()),
                # assign unique id to each message
            })
        return {}

    def is_connected_to_remote_feed(self):
        return self.authenticator.supabase_client.is_realtime_connected()

    def is_connected(self):
        return self.authenticator.is_logged_in()
