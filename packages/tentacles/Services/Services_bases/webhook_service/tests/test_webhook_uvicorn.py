#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import asyncio
import logging
import socket
import threading
import time

import flask
import mock
import pytest
import requests
import uvicorn
from asgiref.wsgi import WsgiToAsgi

import tentacles.Services.Services_bases.webhook_service.webhook as webhook_module


async def _serve_webhook_server(server, serve_finished):
    try:
        await server.serve()
    finally:
        serve_finished.set()


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestWebhookUvicornServer:
    def test_post_webhook_returns_200(self):
        webhook_app = flask.Flask(__name__)
        service = webhook_module.WebHookService()
        service.webhook_app = webhook_app
        received_messages = []

        def _callback(message):
            received_messages.append(message)

        def _auth(_message):
            return True

        service.subscribe_feed("test_feed", _callback, _auth)
        service._register_webhook_routes(webhook_app)

        port = _get_free_port()
        asgi_app = WsgiToAsgi(webhook_app)
        config = uvicorn.Config(asgi_app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)
        serve_finished = threading.Event()

        def _run_server():
            asyncio.run(_serve_webhook_server(server, serve_finished))

        thread = threading.Thread(target=_run_server)
        thread.start()
        time.sleep(0.5)
        try:
            response = requests.post(
                f"http://127.0.0.1:{port}/webhook/test_feed",
                data="payload",
                timeout=5,
            )
            assert response.status_code == 200
            assert received_messages == ["payload"]
        finally:
            server.should_exit = True
            serve_finished.wait(timeout=webhook_module.WebHookService.WEBHOOK_STOP_TIMEOUT_SECONDS)
            thread.join(timeout=webhook_module.WebHookService.WEBHOOK_STOP_TIMEOUT_SECONDS)

    def test_stop_within_timeout(self):
        service = webhook_module.WebHookService()
        service.ngrok_enabled = False
        service.webhook_host = "127.0.0.1"
        service.webhook_port = _get_free_port()
        service.webhook_app = flask.Flask(__name__)
        service.logger = logging.getLogger("test_webhook_uvicorn")
        service.connected = None

        thread = threading.Thread(target=service._start_server, name="webhook-test")
        thread.start()
        start_time = time.time()
        while service.connected is None and time.time() - start_time < webhook_module.WebHookService.CONNECTION_TIMEOUT:
            time.sleep(0.05)
        assert service.connected is True

        asyncio.run(service.stop())
        thread.join(timeout=webhook_module.WebHookService.WEBHOOK_STOP_TIMEOUT_SECONDS)
        assert not thread.is_alive()
