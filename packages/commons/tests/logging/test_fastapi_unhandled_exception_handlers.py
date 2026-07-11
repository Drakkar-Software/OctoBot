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

import mock
import pydantic
import pytest
import fastapi
from fastapi import HTTPException
from starlette.testclient import TestClient

import octobot_commons.logging.fastapi_unhandled_exception_handlers as fastapi_unhandled_exception_handlers


class _ValidatedBody(pydantic.BaseModel):
    name: str


@pytest.fixture
def routes_app():
    app = fastapi.FastAPI()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    @app.get("/not-found")
    async def not_found():
        raise HTTPException(status_code=404, detail="missing")

    @app.post("/validated")
    async def validated(body: _ValidatedBody):
        return body

    return app


def _register_handler(app: fastapi.FastAPI) -> None:
    fastapi_unhandled_exception_handlers.register_unhandled_exception_handler(app, "test-api-logger")


class TestRegisterUnhandledExceptionHandler:
    def test_logs_unhandled_exception(self, routes_app):
        mock_logger = mock.Mock()
        with mock.patch(
            "octobot_commons.logging.fastapi_unhandled_exception_handlers.logging_util.get_logger",
            return_value=mock_logger,
        ):
            _register_handler(routes_app)
            with TestClient(routes_app, raise_server_exceptions=False) as client:
                client.get("/boom")

        mock_logger.exception.assert_called_once()
        call_args = mock_logger.exception.call_args
        assert call_args[0][0].__class__ is RuntimeError
        assert "GET /boom" in call_args[0][2]

    def test_returns_500_json(self, routes_app):
        with mock.patch(
            "octobot_commons.logging.fastapi_unhandled_exception_handlers.logging_util.get_logger",
            return_value=mock.Mock(),
        ):
            _register_handler(routes_app)
            with TestClient(routes_app, raise_server_exceptions=False) as client:
                response = client.get("/boom")

        assert response.status_code == 500
        assert response.json() == {"detail": "Internal Server Error"}

    def test_http_exception_not_logged(self, routes_app):
        mock_logger = mock.Mock()
        with mock.patch(
            "octobot_commons.logging.fastapi_unhandled_exception_handlers.logging_util.get_logger",
            return_value=mock_logger,
        ):
            _register_handler(routes_app)
            with TestClient(routes_app, raise_server_exceptions=False) as client:
                response = client.get("/not-found")

        mock_logger.exception.assert_not_called()
        assert response.status_code == 404
        assert response.json() == {"detail": "missing"}

    def test_validation_error_not_logged(self, routes_app):
        mock_logger = mock.Mock()
        with mock.patch(
            "octobot_commons.logging.fastapi_unhandled_exception_handlers.logging_util.get_logger",
            return_value=mock_logger,
        ):
            _register_handler(routes_app)
            with TestClient(routes_app, raise_server_exceptions=False) as client:
                response = client.post("/validated", json={})

        mock_logger.exception.assert_not_called()
        assert response.status_code == 422
