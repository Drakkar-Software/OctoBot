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

from tests.signals import signal, signal_bundle


def test_to_dict(signal_bundle, signal):
    assert signal_bundle.to_dict() == {
        octobot_commons.enums.SignalBundlesAttrs.IDENTIFIER.value: "hello identifier",
        octobot_commons.enums.SignalBundlesAttrs.SIGNALS.value: [signal.to_dict()],
        octobot_commons.enums.SignalBundlesAttrs.VERSION.value: "version",
    }


def test__str__(signal_bundle):
    assert all(sub_str in str(signal_bundle)
               for sub_str in ("hello identifier", "version", "hello topic", "hi", "plop"))


def test_get_version(signal_bundle):
    assert signal_bundle._get_version() == "1.0.0"
