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

import asgiref.sync as asgiref_sync
import asgiref.wsgi as asgiref_wsgi

_stock_run_wsgi_app_wrapper_cached = None


def _stock_run_wsgi_app_wrapper():
    global _stock_run_wsgi_app_wrapper_cached
    if _stock_run_wsgi_app_wrapper_cached is None:
        _stock_run_wsgi_app_wrapper_cached = asgiref_wsgi.WsgiToAsgiInstance.__dict__["run_wsgi_app"]
    return _stock_run_wsgi_app_wrapper_cached


def _run_wsgi_app_via_asgiref(instance, body):
    return _stock_run_wsgi_app_wrapper().func(instance, body)


class WsgiToAsgiInstance(asgiref_wsgi.WsgiToAsgiInstance):
    # thread_sensitive=False: parallel WSGI on the event loop default thread pool (not CurrentThreadExecutor).
    @asgiref_sync.sync_to_async(thread_sensitive=False)
    def run_wsgi_app(self, body):
        return _run_wsgi_app_via_asgiref(self, body)


class WsgiToAsgi(asgiref_wsgi.WsgiToAsgi):
    async def __call__(self, scope, receive, send):
        await WsgiToAsgiInstance(self.wsgi_application, self.duplicate_header_limit)(
            scope,
            receive,
            send,
        )
