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

from tests.signals import signal_bundle_builder


def test_register_signal(signal_bundle_builder):
    assert signal_bundle_builder.signals == []
    signal_bundle_builder.register_signal("plop_topic", {"content_key1": 0}, other_kwarg=11)
    assert len(signal_bundle_builder.signals) == 1
    assert signal_bundle_builder.signals[0].topic == "plop_topic"
    assert signal_bundle_builder.signals[0].content == {"content_key1": 0}


def test_create_signal(signal_bundle_builder):
    created_signal = signal_bundle_builder.create_signal("plop_topic", {"content_key1": 0}, other_kwarg=11)
    assert created_signal.topic == "plop_topic"
    assert created_signal.content == {"content_key1": 0}


def test_is_empty(signal_bundle_builder):
    assert signal_bundle_builder.is_empty()
    signal_bundle_builder.register_signal("plop_topic", {"content_key1": 0}, other_kwarg=11)
    assert not signal_bundle_builder.is_empty()


def test_build(signal_bundle_builder):
    signal_bundle_builder.version = "1"
    empty_build_bundle = signal_bundle_builder.build()
    assert empty_build_bundle.identifier == "hello builder identifier"
    assert empty_build_bundle.signals == []
    assert empty_build_bundle.version == "1"
    signal_bundle_builder.register_signal("plop_topic", {"content_key1": 0}, other_kwarg=11)
    full_build_bundle = signal_bundle_builder.build()
    assert full_build_bundle.identifier == "hello builder identifier"
    assert full_build_bundle.signals is signal_bundle_builder.signals
    assert full_build_bundle.version == "1"


def test_reset(signal_bundle_builder):
    assert signal_bundle_builder.signals == []
    signal_bundle_builder.register_signal("plop_topic", {"content_key1": 0}, other_kwarg=11)
    assert len(signal_bundle_builder.signals) == 1
    signal_bundle_builder.reset()
    assert signal_bundle_builder.signals == []
