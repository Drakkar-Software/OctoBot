# pylint: disable=C0116
#  Drakkar-Software OctoBot-Commons
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
import typing
import octobot_commons.enums

import octobot_commons.signals.signal_dependencies as signal_dependencies


class Signal:
    def __init__(
        self,
        topic: str,
        content: dict,
        dependencies: typing.Optional[signal_dependencies.SignalDependencies] = None,
        **_,
    ):
        self.topic: str = topic
        self.content: dict = content
        self.dependencies: typing.Optional[signal_dependencies.SignalDependencies] = (
            dependencies
        )

    def to_dict(self) -> dict:
        return {
            octobot_commons.enums.SignalsAttrs.TOPIC.value: self.topic,
            octobot_commons.enums.SignalsAttrs.CONTENT.value: self.content,
            octobot_commons.enums.SignalsAttrs.DEPENDENCIES.value: (
                self.dependencies.to_dict() if self.dependencies else None
            ),
        }

    def __str__(self):
        return f"{self.to_dict()}"
