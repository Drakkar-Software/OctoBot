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
import octobot_commons.signals as signals


from tests.signals import signal


def test_to_dict(signal):
    assert signal.to_dict() == {
        octobot_commons.enums.SignalsAttrs.TOPIC.value: "hello topic",
        octobot_commons.enums.SignalsAttrs.CONTENT.value: {"hi": "plop"},
        octobot_commons.enums.SignalsAttrs.DEPENDENCIES.value: None,
    }
    signal.dependencies = signals.SignalDependencies([
        {"plop": "123"},
        {"PLIP": "123"}
    ])
    assert signal.to_dict() == {
        octobot_commons.enums.SignalsAttrs.TOPIC.value: "hello topic",
        octobot_commons.enums.SignalsAttrs.CONTENT.value: {"hi": "plop"},
        octobot_commons.enums.SignalsAttrs.DEPENDENCIES.value: {
            octobot_commons.enums.SignalDependenciesAttrs.DEPENDENCY.value: [
                {"plop": "123"},
                {"PLIP": "123"}
            ]
        },
    }


def test__str__(signal):
    assert all(sub_str in str(signal) for sub_str in ("hello topic", "hi", "plop"))
