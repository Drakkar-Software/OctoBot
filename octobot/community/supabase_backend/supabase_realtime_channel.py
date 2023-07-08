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
import json
import enum
import realtime


import octobot_commons.logging as logging


class CHANNEL_STATES(enum.Enum):
    JOINED = "JOINED"
    JOINING = "JOINING"
    CLOSED = "CLOSED"
    ERRORED = "ERRORED"


class AuthenticatedSupabaseRealtimeChannel(realtime.Channel):
    def __init__(self, socket: realtime.Socket, topic: str, schema: str, table_name: str, params: dict = {}):
        """
        from realtime.Channel docs:
        `Channel` is an abstraction for a topic listener for an existing socket connection.
        Each Channel has its own topic and a list of event-callbacks that responds to messages.
        Should only be instantiated through `connection.Socket().set_channel(topic)`
        Topic-Channel has a 1-many relationship.


        AuthenticatedSupabaseRealtimeChannel tries to expose a similar logic and public API
        as https://github.com/supabase/realtime-js/blob/master/src/RealtimeChannel.ts
        Re-implements async methods as they are not working as is.
        """
        super().__init__(socket, topic, params=params)
        self.schema = schema
        self.table_name = table_name
        self.auth_payload = {}  # missing in realtime.Channel
        self.joined_once = False
        self.state: CHANNEL_STATES = CHANNEL_STATES.CLOSED
        self.logger = logging.get_logger(self.__class__.__name__)

    async def subscribe(self, callback=None, system_callback=None) -> None:
        """
        fix of async def realtime.Channel._join(self) -> None:
        adds self.join_payload handling (required for auth on join)

        Coroutine that attempts to join Phoenix Realtime server via a certain topic
        :return: None
        """
        if callback:
            self.socket.register_subscribe_callback(self.topic, callback)
        if system_callback:
            self.socket.register_system_callback(self.topic, system_callback)
        join_req = dict(topic=self.topic, event="phx_join", payload=self._get_join_payload(), ref=self._get_ref())
        try:
            self.state = CHANNEL_STATES.JOINING
            await self.socket.ws_connection.send(json.dumps(join_req))
            self.state = CHANNEL_STATES.JOINED
            self.joined_once = True
        except Exception as err:
            self.state = CHANNEL_STATES.ERRORED
            self.logger.exception(err, True, f"Error when joining realtime channel: {err}")
            return

    def _get_join_payload(self):
        # "postgres_changes": [
        #     {
        #         "event": "*" | "INSERT" | "UPDATE" | "DELETE",
        #         "schema": string,
        #         "table": string,
        #         "filter": string + '=' + "eq" | "neq" | "gt" | "gte" | "lt" | "lte" | "in" + '.' + string
        #     }
        # ]
        join_payload = {
            "postgres_changes": [
                {
                    "event": listener.event,
                    "schema": self.schema,
                    "table": self.table_name,
                }
            ]
            for listener in self.listeners
        }
        return {**join_payload, **self.auth_payload}

    def on(self, event, callback):
        """
        Fix payload handling
        """
        async def _cb(payload):
            enriched_payload = {
                "schema": payload["schema"],
                "table": payload["table"],
                "commit_timestamp": payload["commit_timestamp"],
                "event_type": payload["type"],
                "new": {},
                "old": {},
            }
            enriched_payload = {**enriched_payload, **_get_payload_records(payload)}
            await callback(enriched_payload)

        cl = realtime.CallbackListener(event=event, callback=_cb)
        self.listeners.append(cl)
        return self

    def update_auth_payload(self, update: dict):
        self.auth_payload.update(update)

    async def auth(self):
        full_payload = {
            "topic": self.topic,
            "event": "access_token",
            "payload": self.auth_payload,
            "ref": self._get_ref(),
            # "join_ref": 1, #todo https://github.com/supabase/realtime-js/blob/master/src/lib/push.ts#L79
        }
        await self.socket.ws_connection.send(json.dumps(full_payload))

    def is_joined(self):
        return self.state is CHANNEL_STATES.JOINED

    def is_joining(self):
        return self.state is CHANNEL_STATES.JOINING

    def _get_ref(self):
        # see https://github.com/supabase/realtime-js/blob/master/src/RealtimeClient.ts#L290
        return None  # implement if necessary


def _get_payload_records(payload):
    records: dict = {"new": {}, "old": {}}
    if payload["type"] in ["INSERT", "UPDATE"]:
        records["new"] = payload["record"]
        # skip type conversion: error with jsonb and not necessary
        # realtime.convert_change_data(payload["columns"], payload["record"], {"skip_types": realtime.jsonb})
    if payload["type"] in ["UPDATE", "DELETE"]:
        records["old"] = payload["record"]
        # skip type conversion: error with jsonb and not necessary
        # realtime.convert_change_data(payload["columns"], payload["old_record"], {"skip_types": realtime.jsonb})
    return records
