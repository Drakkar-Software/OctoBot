#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import asgiref.sync as asgiref_sync
import mock

import tentacles.Services.Interfaces.web_interface.asgi.wsgi_to_asgi as wsgi_to_asgi


class TestWsgiToAsgiInstanceRunWsgiApp:
    def test_run_wsgi_app_uses_thread_sensitive_false(self):
        run_wsgi_app_callable = wsgi_to_asgi.WsgiToAsgiInstance.__dict__["run_wsgi_app"]
        assert isinstance(run_wsgi_app_callable, asgiref_sync.SyncToAsync)
        assert run_wsgi_app_callable._thread_sensitive is False
        assert run_wsgi_app_callable._executor is None


class TestRunWsgiAppViaAsgiref:
    def test_stock_asgiref_wrapper_is_sync_to_async(self):
        assert isinstance(wsgi_to_asgi._stock_run_wsgi_app_wrapper(), asgiref_sync.SyncToAsync)

    def test_delegates_to_stock_asgiref_sync_function(self):
        wsgi_instance = mock.Mock()
        request_body = mock.Mock()
        stock_wrapper = wsgi_to_asgi._stock_run_wsgi_app_wrapper()
        with mock.patch.object(
            stock_wrapper,
            "func",
            mock.Mock(return_value=None),
        ) as stock_run_wsgi_app_sync:
            wsgi_to_asgi._run_wsgi_app_via_asgiref(wsgi_instance, request_body)
            stock_run_wsgi_app_sync.assert_called_once_with(wsgi_instance, request_body)
