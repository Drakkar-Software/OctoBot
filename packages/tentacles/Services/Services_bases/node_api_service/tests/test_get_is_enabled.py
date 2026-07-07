#  Drakkar-Software OctoBot-Tentacles
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

import octobot.constants as octobot_constants
import octobot.enums as octobot_enums
import tentacles.Services.Services_bases.node_api_service.node_api as node_api_service_module


class TestNodeApiServiceGetIsEnabled:
    def test_returns_true_when_distribution_is_node(self, monkeypatch):
        monkeypatch.setattr(octobot_constants, "FORCED_DISTRIBUTION", octobot_enums.OctoBotDistribution.NODE.value)
        assert node_api_service_module.NodeApiService.get_is_enabled({}) is True

    def test_returns_false_when_distribution_is_default_and_not_configured(self, monkeypatch):
        monkeypatch.setattr(octobot_constants, "FORCED_DISTRIBUTION", None)
        assert node_api_service_module.NodeApiService.get_is_enabled({}) is False
