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
import octobot_commons.enums


class SignalBundle:
    def __init__(self, identifier: str, signals=None, version=None):
        self.identifier: str = identifier
        self.signals: list = signals or []
        self.version: str = version or self._get_version()

    def to_dict(self) -> dict:
        return {
            octobot_commons.enums.SignalBundlesAttrs.IDENTIFIER.value: self.identifier,
            octobot_commons.enums.SignalBundlesAttrs.SIGNALS.value: [
                signal.to_dict() for signal in self.signals
            ],
            octobot_commons.enums.SignalBundlesAttrs.VERSION.value: self.version,
        }

    def __str__(self):
        return f"{self.to_dict()}"

    # pylint: disable=C0415
    def _get_version(self) -> str:
        try:
            import octobot.constants

            return octobot.constants.COMMUNITY_FEED_CURRENT_MINIMUM_VERSION
        except ImportError:
            return "1.0.0"
