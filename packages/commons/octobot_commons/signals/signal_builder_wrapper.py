# pylint: disable=C0116
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
import asyncio
import time

import octobot_commons.signals.signal_bundle_builder as signal_bundle_builder


class SignalBuilderWrapper:
    NO_TIMEOUT_VALUE = -1

    def __init__(
        self,
        identifier: str,
        signal_builder_class=signal_bundle_builder.SignalBundleBuilder,
        timeout: float = NO_TIMEOUT_VALUE,
        builder_args: tuple = None,
    ):
        self.signal_builder_class = signal_builder_class
        self.signal_bundle_builder = (
            signal_builder_class(identifier, *builder_args)
            if builder_args
            else signal_builder_class(identifier)
        )
        self.is_being_emitted = False
        self.timeout = timeout
        self.timeout_event = asyncio.Event()
        self.signal_emit_time = time.time() + timeout
        self._users_count = 0

    def register_user(self):
        self._users_count += 1

    def unregister_user(self):
        self._users_count -= 1

    def has_single_user(self):
        return self._users_count == 1
