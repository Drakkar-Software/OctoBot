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

import io
import json
import zipfile

try:
    from tentacles.Services.Interfaces.node_api_interface.api.routes.feedback import (
        FEEDBACK_JOURNAL_JSON_FILENAME,
    )
except ImportError:
    from api.routes.feedback import FEEDBACK_JOURNAL_JSON_FILENAME  # type: ignore[no-redef]


class TestPostFeedbackExport:
    def test_export_returns_zip_without_auth(self, client):
        response = client.post(
            "/api/v1/feedback/export",
            json={"note": "http export", "ui_error_name": "boot_failed"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/zip")
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            assert zip_file.namelist() == [FEEDBACK_JOURNAL_JSON_FILENAME]
            payload = json.loads(zip_file.read(FEEDBACK_JOURNAL_JSON_FILENAME))
        assert payload["note"] == "http export"
        assert payload["ui_error_name"] == "boot_failed"
