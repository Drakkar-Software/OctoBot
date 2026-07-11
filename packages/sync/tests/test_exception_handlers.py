#  Drakkar-Software OctoBot-Sync
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

import mock
import pytest
import fastapi
from starlette.testclient import TestClient

import octobot_commons.logging as octobot_commons_logging
import octobot_sync.app as sync_app


class TestSyncAppUnhandledExceptionHandler:
    async def test_create_app_registers_unhandled_exception_handler(self):
        store = mock.Mock()
        wrapped_app = sync_app.create_app(store)
        inner_app = wrapped_app.app
        assert Exception in inner_app.exception_handlers

    def test_mounted_sync_unhandled_exception_is_logged(self):
        inner_app = fastapi.FastAPI()

        @inner_app.get("/boom")
        async def boom():
            raise RuntimeError("sync boom")

        parent_app = fastapi.FastAPI()
        parent_app.mount("/sync", sync_app.SignedPathMiddleware(inner_app))

        mock_logger = mock.Mock()
        with mock.patch(
            "octobot_commons.logging.fastapi_unhandled_exception_handlers.logging_util.get_logger",
            return_value=mock_logger,
        ):
            octobot_commons_logging.register_unhandled_exception_handler(inner_app, "OctoBot-Sync")
            with TestClient(parent_app, raise_server_exceptions=False) as client:
                response = client.get("/sync/boom")

        assert response.status_code == 500
        assert response.json() == {"detail": "Internal Server Error"}
        mock_logger.exception.assert_called_once()
        log_message = mock_logger.exception.call_args[0][2]
        assert "GET" in log_message
        assert "boom" in log_message
