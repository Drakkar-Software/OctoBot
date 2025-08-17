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
import logging
import typing
import asyncio
import aiohttp

import sentry_sdk
import sentry_sdk.consts
import sentry_sdk.utils
import sentry_sdk.envelope
import sentry_sdk.transport
import sentry_sdk.types


class SentryAiohttpTransport(sentry_sdk.HttpTransport):
    def __init__(
        self, options: typing.Dict[str, typing.Any]
    ):
        super().__init__(options)
        # WARNING: override default "br" value: not supported by Glitchtip yet
        self._compression_algo = "gzip"
        # use custom async worker instead of default sentry thread worker
        # does not support proxies, at least for now
        self._worker = AiohttpWorker(queue_size=options["transport_queue_size"])

    async def _async_send_request(
        self,
        body,  # type: bytes
        headers,  # type: typing.Dict[str, str]
        endpoint_type="store",  # type: sentry_sdk.consts.EndpointType
        envelope=None,  # type: typing.Optional[sentry_sdk.envelope.Envelope]
    ) -> None:

        def record_loss(reason: str) -> None:
            if envelope is None:
                self.record_lost_event(reason, data_category="error")
            else:
                for item in envelope.items:
                    self.record_lost_event(reason, item=item)

        headers.update(
            {
                "User-Agent": str(self._auth.client),
                "X-Sentry-Auth": str(self._auth.to_header()),
            }
        )
        try:
            async with self._worker.session.post(
                str(self._auth.get_api_url(endpoint_type)),
                data=body,
                headers=headers,
            ) as response:
                self._update_rate_limits(response)

                if response.status == 429:
                    # if we hit a 429.  Something was rate limited but we already
                    # acted on this in `self._update_rate_limits`.  Note that we
                    # do not want to record event loss here as we will have recorded
                    # an outcome in relay already.
                    self.on_dropped_event("status_429")
                    pass

                elif response.status >= 300 or response.status < 200:
                    logging.getLogger(self.__class__.__name__).warning(
                        "Unexpected status code: %s (body: %s)",
                        response.status,
                        await response.text(),
                    )
                    self.on_dropped_event("status_{}".format(response.status))
                    record_loss("network_error")
        except BaseException as err:
            logging.getLogger(self.__class__.__name__).warning(f"Sentry post error: {err} {err.__class__.__name__}")
            self.on_dropped_event("network")
            record_loss("network_error")
            raise

    async def _async_send_envelope(
        self, envelope: sentry_sdk.envelope.Envelope
    ) -> None:
        """
        Async version of super()._send_envelope
        """

        # remove all items from the envelope which are over quota
        new_items = []
        for item in envelope.items:
            if self._check_disabled(item.data_category):
                if item.data_category in ("transaction", "error", "default", "statsd"):
                    self.on_dropped_event("self_rate_limits")
                self.record_lost_event("ratelimit_backoff", item=item)
            else:
                new_items.append(item)

        # Since we're modifying the envelope here make a copy so that others
        # that hold references do not see their envelope modified.
        envelope = sentry_sdk.envelope.Envelope(headers=envelope.headers, items=new_items)

        if not envelope.items:
            return None

        # since we're already in the business of sending out an envelope here
        # check if we have one pending for the stats session envelopes so we
        # can attach it to this enveloped scheduled for sending.  This will
        # currently typically attach the client report to the most recent
        # session update.
        client_report_item = self._fetch_pending_client_report(interval=30)
        if client_report_item is not None:
            envelope.items.append(client_report_item)

        content_encoding, body = self._serialize_envelope(envelope)

        assert self.parsed_dsn is not None
        sentry_sdk.utils.logger.debug(
            "Sending envelope [%s] project:%s host:%s",
            envelope.description,
            self.parsed_dsn.project_id,
            self.parsed_dsn.host,
        )

        headers = {
            "Content-Type": "application/x-sentry-envelope",
        }
        if content_encoding:
            headers["Content-Encoding"] = content_encoding

        await self._async_send_request(
            body.getvalue(),
            headers=headers,
            endpoint_type=sentry_sdk.consts.EndpointType.ENVELOPE,
            envelope=envelope,
        )
        return None

    def capture_event(
        self, event  # type: sentry_sdk.types.Event
    ) -> None:
        """
        DEPRECATED: Please use capture_envelope instead.
        """
        return super().capture_event(event)

    def capture_envelope(
        self, envelope: sentry_sdk.envelope.Envelope
    ) -> None:

        async def send_envelope_wrapper() -> None:
            with sentry_sdk.utils.capture_internal_exceptions():
                await self._async_send_envelope(envelope)
                self._flush_client_reports()

        if not self._worker.submit(send_envelope_wrapper):
            self.on_dropped_event("full_queue")
            for item in envelope.items:
                self.record_lost_event("queue_overflow", item=item)

    async def async_kill(self):
        await self._worker.async_kill()

class AiohttpWorker:
    def __init__(self, queue_size=sentry_sdk.consts.DEFAULT_QUEUE_SIZE):
        self.session = None
        self.call_tasks = []
        self._queue_size = queue_size
        self._kill_task = None
        self._stopped = False

    @property
    def is_alive(self) -> bool:
        if self.session is None or self.session.closed:
            return False
        # session is not closed
        # no pending kill task
        if self._kill_task is None or self._kill_task.done():
            return not self.session.closed
        # pending kill task, will stop
        return False

    def _ensure_session(self) -> None:
        if not self.is_alive:
            self.start()

    def start(self) -> None:
        if self._kill_task and not self._kill_task.done():
            self._kill_task.cancel()
        self.session = aiohttp.ClientSession()

    def kill(self) -> None:
        for task in self.call_tasks:
            if not task.done():
                task.cancel()
        self.call_tasks = []
        if self.is_alive:
            self._kill_task = asyncio.create_task(self.session.close())

    async def async_kill(self):
        self._stopped = type
        self.kill()
        if self._kill_task and not self._kill_task.done():
            await self._kill_task

    def full(self) -> bool:
        return len(self.call_tasks) > self._queue_size

    def flush(self, timeout: float, callback=None) -> None:
        sentry_sdk.utils.logger.debug("Custom background worker got flush request, ignored")

    async def _async_call(self, callback):
        try:
            await callback()
        finally:
            if asyncio.current_task() in self.call_tasks:
                self.call_tasks.remove(asyncio.current_task())

    def _schedule_async_send(self, callback):
        self.call_tasks.append(asyncio.create_task(self._async_call(callback)))

    def submit(self, callback) -> bool:
        if self._stopped:
            return False
        self._ensure_session()
        if self.full():
            return False
        self._schedule_async_send(callback)
        return True
