# pylint: disable=R0913, W0718
# Drakkar-Software OctoBot-Trading
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
import asyncio
import contextlib
import time

import octobot_commons.singleton as singleton
import octobot_commons.logging as logging
import octobot_commons.errors as errors
import octobot_commons.signals.signals_emitter as signals_emitter
import octobot_commons.signals.signal_bundle_builder as signal_bundle_builder
import octobot_commons.signals.signal_builder_wrapper as signal_builder_wrapper


class SignalPublisher(singleton.Singleton):
    DEFAULT_SIGNAL_BUILDER_CLASS = signal_bundle_builder.SignalBundleBuilder

    def __init__(self):
        self._signal_builder_wrappers = {}
        self._timeout_watcher_tasks = {}

    def get_signal_bundle_builder(
        self, wrapper_key: str
    ) -> signal_builder_wrapper.SignalBuilderWrapper:
        """
        Return the SignalBuilderWrapper registered under the given key
        """
        try:
            return self._signal_builder_wrappers[wrapper_key].signal_bundle_builder
        except KeyError as err:
            raise errors.MissingSignalBuilder from err

    @contextlib.asynccontextmanager
    async def remote_signal_bundle_builder(
        self,
        wrapper_key: str,
        identifier: str,
        timeout: float = signal_builder_wrapper.SignalBuilderWrapper.NO_TIMEOUT_VALUE,
        signal_builder_class=DEFAULT_SIGNAL_BUILDER_CLASS,
        builder_args=None,
    ):
        """
        Context manager ensuring that any signal under the given key is buildable and sent
        when context manager is closing.
        Use signal_builder_class to specify signal builders to create
        """
        signal_builder_wrap = None
        try:
            signal_builder_wrap = self._create_or_get_signal_builder_wrapper(
                wrapper_key, identifier, timeout, signal_builder_class, builder_args
            )
            signal_builder_wrap.register_user()
            self._register_timeout_if_any(wrapper_key)
            yield signal_builder_wrap.signal_bundle_builder
            # send the full signal when the last user is done
            if signal_builder_wrap.has_single_user():
                await self._emit_signal_if_necessary(signal_builder_wrap)
        finally:
            if signal_builder_wrap is not None:
                if signal_builder_wrap.has_single_user():
                    self._unregister_timeout(wrapper_key)
                    self._signal_builder_wrappers.pop(wrapper_key, None)
                else:
                    signal_builder_wrap.unregister_user()

    def stop(self):
        """
        Stop all timeout tasks and clear any remaining registered wrapper
        :return:
        """
        logging.get_logger(self.__class__.__name__).debug("Stopping ...")
        for task in self._timeout_watcher_tasks.values():
            task.cancel()
        self._timeout_watcher_tasks = {}
        self._signal_builder_wrappers = {}
        logging.get_logger(self.__class__.__name__).debug("Stopped ...")

    def _create_or_get_signal_builder_wrapper(
        self,
        wrapper_key: str,
        identifier: str,
        timeout: float,
        signal_builder_class,
        builder_args: tuple,
    ) -> signal_builder_wrapper.SignalBuilderWrapper:
        if wrapper_key in self._signal_builder_wrappers:
            return self._signal_builder_wrappers[wrapper_key]
        self._signal_builder_wrappers[wrapper_key] = (
            signal_builder_wrapper.SignalBuilderWrapper(
                identifier, signal_builder_class, timeout, builder_args
            )
        )
        return self._signal_builder_wrappers[wrapper_key]

    async def _emit_signal_if_necessary(self, signal_builder_wrap):
        # check has_single_user in case the same builder is used multiple times at once
        if (
            not signal_builder_wrap.signal_bundle_builder.is_empty()
            and not signal_builder_wrap.is_being_emitted
        ):
            try:
                signal_builder_wrap.is_being_emitted = True
                await signals_emitter.emit_signal_bundle(
                    signal_builder_wrap.signal_bundle_builder.build()
                )
            except Exception as err:
                logging.get_logger(self.__class__.__name__).exception(
                    err, True, f"Unexpected error when emitting signal: {err}"
                )
            finally:
                # always reset builder after emitting to avoid emitting the same signal twice
                signal_builder_wrap.signal_bundle_builder.reset()
                signal_builder_wrap.is_being_emitted = False

    async def _schedule_signal_auto_emit(self, wrapper_key, delay):
        while wrapper_key in self._signal_builder_wrappers:
            await asyncio.sleep(delay)
            if wrapper_key not in self._signal_builder_wrappers:
                # signal should not be emitted anymore
                break
            wrapper = self._signal_builder_wrappers[wrapper_key]
            if time.time() >= wrapper.signal_emit_time:
                await self._emit_signal_if_necessary(wrapper)
                wrapper.signal_emit_time = time.time() + delay

    def _register_timeout_if_any(self, wrapper_key):
        wrapper = self._signal_builder_wrappers[wrapper_key]
        if wrapper.timeout != wrapper.NO_TIMEOUT_VALUE:
            self._timeout_watcher_tasks[wrapper_key] = asyncio.create_task(
                self._schedule_signal_auto_emit(wrapper_key, wrapper.timeout)
            )

    def _unregister_timeout(self, wrapper_key):
        if task := self._timeout_watcher_tasks.pop(wrapper_key, None):
            task.cancel()
