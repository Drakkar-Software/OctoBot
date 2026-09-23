#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  CI (from OctoBot/, PYTHONPATH from .vscode/settings.json):
# venv13\Scripts\python.exe -m pytest tentacles/Services/Interfaces/web_interface/tests/websockets/socket_namespaces/test_dashboard.py -q

import mock

import tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.dashboard as dashboard_module


class TestDashboardNamespaceGetProfitability:
    def test_returns_empty_payload_when_bot_not_ready(self):
        with mock.patch.object(
            dashboard_module.services_interfaces.AbstractInterface,
            "is_bot_ready",
            mock.Mock(return_value=False),
        ):
            payload = dashboard_module.DashboardNamespace._get_profitability()
        assert payload == dashboard_module.DashboardNamespace._empty_profitability_payload()
        assert "market_average_profitability" in payload
        assert "bot_real_profitability" not in payload

    def test_returns_empty_payload_when_global_profitability_raises_key_error(self):
        with mock.patch.object(
            dashboard_module.services_interfaces.AbstractInterface,
            "is_bot_ready",
            mock.Mock(return_value=True),
        ), mock.patch.object(
            dashboard_module.services_interfaces,
            "get_global_profitability",
            mock.Mock(side_effect=KeyError("missing exchange manager")),
        ):
            payload = dashboard_module.DashboardNamespace._get_profitability()
        assert payload == dashboard_module.DashboardNamespace._empty_profitability_payload()


class TestDashboardNamespaceFormatNewData:
    def test_returns_empty_payload_when_exchange_manager_missing(self):
        with mock.patch.object(
            dashboard_module.octobot_trading_api,
            "get_exchange_manager_from_exchange_id",
            mock.Mock(side_effect=KeyError("missing exchange manager")),
        ):
            payload = dashboard_module.DashboardNamespace._format_new_data(
                exchange_id="stale-id",
                symbol="BTC/USDT",
            )
        assert payload == dashboard_module.DashboardNamespace._empty_new_data_payload(
            exchange_id="stale-id",
            symbol="BTC/USDT",
        )
