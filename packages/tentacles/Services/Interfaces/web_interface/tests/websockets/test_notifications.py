#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  CI (from OctoBot/, PYTHONPATH from .vscode/settings.json):
# venv13\Scripts\python.exe -m pytest tentacles/Services/Interfaces/web_interface/tests/websockets/test_notifications.py -q

import asyncio

import flask
import pytest
from starlette.testclient import TestClient

import octobot_commons.configuration as configuration
import octobot_services.enums as services_enums
import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.login as login_module
import tentacles.Services.Interfaces.web_interface.tests.websockets.websocket_test_util as websocket_test_util
import tentacles.Services.Interfaces.web_interface.login.web_login_manager as web_login_manager
import tentacles.Services.Interfaces.web_interface.websockets as websockets


_PASSWORD = "123"


def _build_test_asgi_app(require_password: bool) -> tuple:
    flask_app = flask.Flask(__name__)
    flask_app.secret_key = "test-web-interface-ws-secret"
    login_module.WebLoginManager(flask_app, configuration.get_password_hash(_PASSWORD))
    login_module.set_is_login_required(require_password)
    asgi_app = websockets.build_composite_asgi_app(flask_app)
    return asgi_app, flask_app


class TestNotificationsWebSocketOnConnect:
    def test_sends_update_on_connect(self):
        asgi_app, _flask_app = _build_test_asgi_app(False)
        with TestClient(asgi_app) as client:
            with client.websocket_connect("/notifications") as websocket:
                frame = websocket_test_util.recv_ws_event(websocket)
                assert frame["event"] == "update"
                assert "notifications" in frame["data"]
                assert "errors_count" in frame["data"]


class TestNotificationsWebSocketReceiveUpdate:
    def test_receives_update_after_add_notification(self):
        asgi_app, _flask_app = _build_test_asgi_app(False)
        with TestClient(asgi_app) as client:
            with client.websocket_connect("/notifications") as websocket:
                websocket_test_util.recv_ws_event(websocket)
                asyncio.run(
                    web_interface.add_notification(
                        services_enums.NotificationLevel.INFO,
                        "Test title",
                        "Test message",
                    )
                )
                web_interface.send_general_notifications()
                frame = websocket_test_util.recv_ws_event(websocket)
                assert frame["event"] == "update"
                assert any(
                    notification.get("Title") == "Test title"
                    for notification in frame["data"]["notifications"]
                )


class TestNotificationsWebSocketServerPush:
    def test_send_general_notifications_delivers_update(self):
        asgi_app, _flask_app = _build_test_asgi_app(False)
        with TestClient(asgi_app) as client:
            with client.websocket_connect("/notifications") as websocket:
                websocket_test_util.recv_ws_event(websocket)
                asyncio.run(
                    web_interface.add_notification(
                        services_enums.NotificationLevel.INFO,
                        "Push title",
                        "Push body",
                    )
                )
                web_interface.send_general_notifications()
                frame = websocket_test_util.recv_ws_event(websocket)
                assert frame["event"] == "update"


class TestNotificationsWebSocketAuth:
    def test_closes_without_session_before_client_send(self):
        asgi_app, _flask_app = _build_test_asgi_app(True)
        with TestClient(asgi_app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect("/notifications"):
                    pass

    def test_accepts_with_login_cookie(self):
        asgi_app, flask_app = _build_test_asgi_app(True)
        flask_client = flask_app.test_client()
        web_login_manager.GENERIC_USER.is_authenticated = True
        with flask_client.session_transaction() as session:
            session["_user_id"] = web_login_manager.GENERIC_USER.get_id()
        session_cookie = flask_client.get_cookie("session")
        assert session_cookie is not None
        with TestClient(asgi_app) as client:
            with client.websocket_connect(
                "/notifications",
                headers={"cookie": f"session={session_cookie.value}"},
            ) as websocket:
                frame = websocket_test_util.recv_ws_event(websocket)
                assert frame["event"] == "update"
