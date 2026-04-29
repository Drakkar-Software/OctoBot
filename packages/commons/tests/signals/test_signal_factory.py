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
import octobot_commons.signals as signals

from tests.signals import signal_dict, signal_bundle_dict, signal_with_dependencies_dict


def test_create_signal_bundle(signal_bundle_dict):
    created_bundle = signals.create_signal_bundle(signal_bundle_dict)
    assert len(created_bundle.signals) == 1
    assert created_bundle.identifier == "dict identifier"
    assert created_bundle.version == "dict_version"
    assert created_bundle.signals[0].topic == "dict topic"
    assert created_bundle.signals[0].content == {"dict": "content", "hi": 1}


def test_create_signal(signal_dict):
    created_signal = signals.create_signal(signal_dict)
    assert created_signal.topic == "dict topic"
    assert created_signal.content == {"dict": "content", "hi": 1}


def test_create_signal_with_dependencies(signal_with_dependencies_dict):
    created_signal = signals.create_signal(signal_with_dependencies_dict)
    assert created_signal.topic == "dict topic"
    assert created_signal.content == {"dict": "content", "hi": 1}
    assert created_signal.dependencies == signals.SignalDependencies([
        {"plop": "123"},
        {"PLIP": "456"}
    ])
