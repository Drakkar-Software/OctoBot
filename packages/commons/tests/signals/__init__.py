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
import pytest

import octobot_commons.signals as signals
import octobot_commons.enums as enums


@pytest.fixture
def signal():
    return signals.Signal("hello topic", {"hi": "plop"})


@pytest.fixture
def signal_bundle(signal):
    return signals.SignalBundle("hello identifier", [signal], "version")


@pytest.fixture
def signal_bundle_builder():
    return signals.SignalBundleBuilder("hello builder identifier")


@pytest.fixture
def signal_builder_wrapper():
    return signals.SignalBuilderWrapper(
        "hello wrapper identifier",
        signal_builder_class=signals.SignalBundleBuilder,
        timeout=-2
    )


@pytest.fixture
def signal_dict():
    return {
        enums.SignalsAttrs.TOPIC.value:  "dict topic",
        enums.SignalsAttrs.CONTENT.value: {"dict": "content", "hi": 1},
        enums.SignalsAttrs.DEPENDENCIES.value: None,
    }


@pytest.fixture
def signal_with_dependencies_dict():
    return {
        enums.SignalsAttrs.TOPIC.value:  "dict topic",
        enums.SignalsAttrs.CONTENT.value: {"dict": "content", "hi": 1},
        enums.SignalsAttrs.DEPENDENCIES.value: {
            enums.SignalDependenciesAttrs.DEPENDENCY.value: [
                {"plop": "123"},
                {"PLIP": "456"}
            ]
        },
    }


@pytest.fixture
def signal_bundle_dict(signal_dict):
    return {
        enums.CommunityFeedAttrs.VALUE.value: {
            enums.SignalBundlesAttrs.IDENTIFIER.value: "dict identifier",
            enums.SignalBundlesAttrs.SIGNALS.value: [signal_dict],
            enums.SignalBundlesAttrs.VERSION.value: "dict_version"
        },
    }
