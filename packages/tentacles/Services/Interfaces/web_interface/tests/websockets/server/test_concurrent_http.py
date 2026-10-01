#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  CI (from OctoBot/, PYTHONPATH from .vscode/settings.json):
# venv13\Scripts\python.exe -m pytest tentacles/Services/Interfaces/web_interface/tests/websockets/server/test_concurrent_http.py -q

import threading

import flask
from starlette.testclient import TestClient

import tentacles.Services.Interfaces.web_interface.websockets as websockets


_CONCURRENT_REQUEST_COUNT = 16
_BURST_COUNT = 8


def _build_ping_asgi_app():
    flask_app = flask.Flask(__name__)

    @flask_app.route("/ping")
    def ping():
        return "ok", 200

    return websockets.build_composite_asgi_app(flask_app)


def _concurrent_get_ping(client: TestClient) -> list[Exception | None]:
    errors: list[Exception | None] = [None] * _CONCURRENT_REQUEST_COUNT
    barrier = threading.Barrier(_CONCURRENT_REQUEST_COUNT)

    def worker(worker_index: int) -> None:
        try:
            barrier.wait(timeout=10)
            response = client.get("/ping")
            if response.status_code != 200:
                errors[worker_index] = AssertionError(
                    f"unexpected status {response.status_code}: {response.text}"
                )
        except Exception as error:
            errors[worker_index] = error

    threads = [
        threading.Thread(target=worker, args=(worker_index,))
        for worker_index in range(_CONCURRENT_REQUEST_COUNT)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return errors


class TestCompositeAsgiConcurrentHttp:
    def test_concurrent_wsgi_mount_requests_succeed(self):
        asgi_app = _build_ping_asgi_app()
        with TestClient(asgi_app, raise_server_exceptions=True) as client:
            for _burst_index in range(_BURST_COUNT):
                errors = _concurrent_get_ping(client)
                for error in errors:
                    if error is not None:
                        raise error
