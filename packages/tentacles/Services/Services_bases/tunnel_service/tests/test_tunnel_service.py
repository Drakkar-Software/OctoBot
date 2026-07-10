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
import asyncio
import logging
from unittest import mock

import pytest

from tentacles.Services.Services_bases.tunnel_service import TunnelService, WebHookService
from tentacles.Services.Services_bases.tunnel_service.backends import ngrok_backend, tailscale_backend

import octobot_services.constants as services_constants


def _minimal_tunnel_config(**overrides):
    tunnel_config = {
        services_constants.CONFIG_ENABLE_NGROK: True,
        services_constants.CONFIG_NGROK_TOKEN: "token",
        services_constants.CONFIG_WEBHOOK_SERVER_IP: "127.0.0.1",
        services_constants.CONFIG_WEBHOOK_SERVER_PORT: 9000,
    }
    tunnel_config.update(overrides)
    return {
        services_constants.CONFIG_CATEGORY_SERVICES: {
            services_constants.CONFIG_TUNNEL: tunnel_config,
        }
    }


def _service_with_config(config):
    service = TunnelService()
    service.config = config
    service.logger = logging.getLogger("TunnelService.test")
    return service


def test_webhook_service_is_tunnel_service_alias():
    assert WebHookService is TunnelService


def test_legacy_webhook_config_bucket_is_used_as_fallback():
    legacy_config = {
        services_constants.CONFIG_CATEGORY_SERVICES: {
            services_constants.CONFIG_WEBHOOK: {
                services_constants.CONFIG_ENABLE_NGROK: True,
                services_constants.CONFIG_NGROK_TOKEN: "legacy-token",
            }
        }
    }
    service = _service_with_config(legacy_config)
    assert service.get_tunnel_config()[services_constants.CONFIG_NGROK_TOKEN] == "legacy-token"


def test_new_tunnel_bucket_takes_priority_over_legacy_webhook_bucket():
    config = {
        services_constants.CONFIG_CATEGORY_SERVICES: {
            services_constants.CONFIG_WEBHOOK: {services_constants.CONFIG_NGROK_TOKEN: "legacy-token"},
            services_constants.CONFIG_TUNNEL: {services_constants.CONFIG_NGROK_TOKEN: "new-token"},
        }
    }
    service = _service_with_config(config)
    assert service.get_tunnel_config()[services_constants.CONFIG_NGROK_TOKEN] == "new-token"


def test_get_default_value_includes_tailscale_fields():
    service = TunnelService()
    defaults = service.get_default_value()
    assert services_constants.CONFIG_ENABLE_TAILSCALE in defaults
    assert services_constants.CONFIG_TAILSCALE_AUTH_KEY in defaults
    assert services_constants.CONFIG_ENABLE_TAILSCALE_FUNNEL in defaults
    assert services_constants.CONFIG_TUNNEL_SERVE_UI in defaults


@pytest.mark.asyncio
async def test_prepare_selects_ngrok_backend_by_default():
    service = _service_with_config(_minimal_tunnel_config())
    await service.prepare()
    assert service.ngrok_enabled is True
    assert service.tailscale_enabled is False
    assert service.ngrok_token == "token"


@pytest.mark.asyncio
async def test_prepare_tailscale_takes_priority_over_ngrok():
    config = _minimal_tunnel_config(**{
        services_constants.CONFIG_ENABLE_TAILSCALE: True,
        services_constants.CONFIG_TAILSCALE_AUTH_KEY: "tskey-auth-xxx",
    })
    service = _service_with_config(config)
    await service.prepare()
    assert service.tailscale_enabled is True
    # ngrok gets disabled even though enable-ngrok is still True in config: backends are exclusive
    assert service.ngrok_enabled is False
    assert service.tailscale_auth_key == "tskey-auth-xxx"


def test_check_required_config_tailscale_requires_auth_key():
    service = _service_with_config(_minimal_tunnel_config())
    tailscale_config = {
        services_constants.CONFIG_ENABLE_TAILSCALE: True,
        services_constants.CONFIG_TAILSCALE_AUTH_KEY: "tskey-auth-xxx",
    }
    assert service.check_required_config(tailscale_config)
    assert not service.check_required_config({
        **tailscale_config, services_constants.CONFIG_TAILSCALE_AUTH_KEY: "",
    })


@pytest.mark.asyncio
async def test_ngrok_backend_open_uses_pyngrok(monkeypatch):
    fake_tunnel = mock.Mock(public_url="https://fake.ngrok.io")
    connect_mock = mock.Mock(return_value=fake_tunnel)
    set_auth_token_mock = mock.Mock()
    monkeypatch.setattr(ngrok_backend.ngrok, "connect", connect_mock)
    monkeypatch.setattr(ngrok_backend.ngrok, "set_auth_token", set_auth_token_mock)

    backend = ngrok_backend.NgrokBackend("token", None)
    url = await backend.open("127.0.0.1", 9000)

    set_auth_token_mock.assert_called_once_with("token")
    connect_mock.assert_called_once_with(9000, "http", domain=None)
    assert url == "https://fake.ngrok.io"

    await backend.close()


class _FakeTailscaleListener:
    async def accept(self):
        # never resolves: the accept loop should just idle until cancelled by close()
        await asyncio.sleep(3600)


class _FakeTailscaleDevice:
    async def ipv4_addr(self):
        return "100.64.0.1"

    async def tcp_listen(self, addr):
        return _FakeTailscaleListener()


@pytest.mark.asyncio
async def test_tailscale_backend_open_connects_and_listens(monkeypatch):
    connect_mock = mock.AsyncMock(return_value=_FakeTailscaleDevice())
    monkeypatch.setattr(tailscale_backend.tailscale, "connect", connect_mock)

    backend = tailscale_backend.TailscaleBackend("tskey-auth-xxx", "octobot", "state.json")
    url = await backend.open("127.0.0.1", 9000)

    connect_mock.assert_awaited_once_with("state.json", "tskey-auth-xxx", hostname="octobot")
    assert url == "http://100.64.0.1:9000"

    await backend.close()


@pytest.mark.asyncio
async def test_tailscale_backend_reuses_single_connection_for_multiple_targets(monkeypatch):
    connect_mock = mock.AsyncMock(return_value=_FakeTailscaleDevice())
    monkeypatch.setattr(tailscale_backend.tailscale, "connect", connect_mock)

    backend = tailscale_backend.TailscaleBackend("tskey-auth-xxx", "octobot", "state.json")
    await backend.open("127.0.0.1", 9000)
    await backend.open("127.0.0.1", 5001)

    # a single tailscale.connect() session is shared across both listeners
    connect_mock.assert_awaited_once()

    await backend.close()


@pytest.mark.asyncio
async def test_tailscale_funnel_is_mocked_and_warns(caplog):
    backend = tailscale_backend.TailscaleBackend("tskey-auth-xxx", "octobot", "state.json")
    with caplog.at_level(logging.WARNING):
        url = await backend.open_funnel("127.0.0.1", 9000)

    assert url == "https://octobot.mock-tailnet.ts.net"
    assert any("Funnel is not yet supported" in record.message for record in caplog.records)
