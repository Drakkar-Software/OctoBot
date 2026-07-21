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
import octobot_commons.configuration.user_inputs as user_inputs


class TestFindParentConfigNode:
    def test_extends_empty_object_array_with_placeholder(self):
        tentacle_config = {"items": []}
        parent_node = user_inputs._find_parent_config_node(
            tentacle_config, "items", [0]
        )
        assert parent_node == {}
        assert tentacle_config["items"] == [{}]

    def test_extends_object_array_until_requested_index(self):
        tentacle_config = {"items": [{"existing": True}]}
        parent_node = user_inputs._find_parent_config_node(
            tentacle_config, "items", [2]
        )
        assert parent_node == {}
        assert tentacle_config["items"] == [{"existing": True}, {}, {}]
