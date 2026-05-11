#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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

import octobot_commons.singleton.singleton_class as singleton_class

import octobot_node.user_actions.user_actions_provider as user_actions_provider_module


@pytest.fixture(autouse=True)
def reset_user_actions_provider_singleton():
    singleton_class.Singleton._instances.pop(user_actions_provider_module.UserActionsProvider, None)
    yield
    singleton_class.Singleton._instances.pop(user_actions_provider_module.UserActionsProvider, None)
