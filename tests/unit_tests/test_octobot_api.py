#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import mock

import octobot.octobot_api as octobot_api


class TestGetActivityMetrics:
    def test_returns_octobot_activity_metrics(self):
        activity_metrics = mock.Mock(name="activity-metrics")
        octobot = mock.Mock()
        octobot.bot_id = "bot-id"
        octobot.activity_metrics = activity_metrics
        with mock.patch.object(octobot_api.OctoBotAPIProvider, "instance") as provider_mock:
            provider_mock.return_value.register_api = mock.Mock()
            api = octobot_api.OctoBotAPI(octobot)
        assert api.get_activity_metrics() is activity_metrics
