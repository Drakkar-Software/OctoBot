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
import octobot_commons.configuration as configuration
from octobot_commons.tentacles_management.abstract_tentacle import AbstractTentacle


class TentacleTest(AbstractTentacle):
    def __init__(self):
        super().__init__()


class TentacleTestChild(TentacleTest):
    def __init__(self):
        super().__init__()
        self.plop = 1


def test_get_name():
    assert TentacleTest().get_name() == "TentacleTest"
    assert TentacleTestChild().get_name() == "TentacleTestChild"


def test_get_all_subclasses():
    assert TentacleTest().get_all_subclasses() == [TentacleTestChild]


def test_user_input_factories():
    tentacle = TentacleTest()
    assert isinstance(tentacle.UI, configuration.UserInputFactory)
    assert isinstance(tentacle.CLASS_UI, configuration.UserInputFactory)
    assert isinstance(tentacle.__class__.CLASS_UI, configuration.UserInputFactory)
    assert isinstance(TentacleTestChild.CLASS_UI, configuration.UserInputFactory)
    assert TentacleTestChild.CLASS_UI is tentacle.CLASS_UI

    child_tentacle = TentacleTestChild()
    assert TentacleTestChild.CLASS_UI is child_tentacle.CLASS_UI
    assert child_tentacle.plop == 1
    assert isinstance(child_tentacle.UI, configuration.UserInputFactory)
    assert isinstance(child_tentacle.CLASS_UI, configuration.UserInputFactory)
    assert isinstance(tentacle.__class__.CLASS_UI, configuration.UserInputFactory)
    assert isinstance(TentacleTestChild.CLASS_UI, configuration.UserInputFactory)
    assert TentacleTestChild.CLASS_UI is child_tentacle.CLASS_UI
    assert tentacle.CLASS_UI is child_tentacle.CLASS_UI
