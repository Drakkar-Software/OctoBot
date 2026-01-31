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

from tests.signals import signal_builder_wrapper


def test_register_user(signal_builder_wrapper):
    assert signal_builder_wrapper._users_count == 0
    signal_builder_wrapper.register_user()
    assert signal_builder_wrapper._users_count == 1
    signal_builder_wrapper.register_user()
    assert signal_builder_wrapper._users_count == 2


def test_unregister_user(signal_builder_wrapper):
    assert signal_builder_wrapper._users_count == 0
    signal_builder_wrapper.register_user()
    assert signal_builder_wrapper._users_count == 1
    signal_builder_wrapper.register_user()
    assert signal_builder_wrapper._users_count == 2
    signal_builder_wrapper.unregister_user()
    assert signal_builder_wrapper._users_count == 1
    signal_builder_wrapper.register_user()
    assert signal_builder_wrapper._users_count == 2
    signal_builder_wrapper.unregister_user()
    assert signal_builder_wrapper._users_count == 1
    signal_builder_wrapper.unregister_user()
    assert signal_builder_wrapper._users_count == 0


def test_has_single_user(signal_builder_wrapper):
    assert signal_builder_wrapper.has_single_user() is False
    signal_builder_wrapper._users_count = 1
    assert signal_builder_wrapper.has_single_user() is True
    signal_builder_wrapper._users_count = 10
    assert signal_builder_wrapper.has_single_user() is False
    signal_builder_wrapper._users_count = 1
    assert signal_builder_wrapper.has_single_user() is True
