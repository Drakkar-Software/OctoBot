#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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

import octobot_sync.constants as sync_constants


class TestGetDslKeywords:
    def test_without_auth_returns_401(self, client, mock_auth):
        response = client.get("/api/v1/dsl/keywords")
        assert response.status_code == 401, response.text

    def test_returns_keywords_state(self, admin_client):
        response = admin_client.get("/api/v1/dsl/keywords")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["version"] == sync_constants.DSL_KEYWORDS_STATE_VERSION
        assert isinstance(body["keywords"], list)
        assert len(body["keywords"]) > 0
        first_keyword = body["keywords"][0]
        assert "name" in first_keyword
        assert "category" in first_keyword
        assert "inputs" in first_keyword
        assert "outputs" in first_keyword
