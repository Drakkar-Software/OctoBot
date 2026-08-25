#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import datetime
import mock
import pytest

import octobot_node.config
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants

from .conftest import TENANT_USER_ID


def _sample_history_state() -> protocol_models.PortfolioHistoricalValuesState:
    return protocol_models.PortfolioHistoricalValuesState(
        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
        history=protocol_models.PortfolioHistoricalValues(
            unit="USDT",
            values=[
                protocol_models.PortfolioHistoricalValue(
                    timestamp=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
                    total=1000.0,
                    assets=[
                        protocol_models.HistoricalAssetsForTradingType(
                            trading_type=protocol_models.TradingType.SPOT,
                            assets=[
                                protocol_models.HistoricalAssetValue(
                                    symbol="USDT",
                                    holdings=1000.0,
                                    value=1000.0,
                                )
                            ],
                        )
                    ],
                )
            ],
        ),
    )


class TestGetAccountHistoricalValues:
    def test_returns_history_state_for_account(self, tenant_client, mock_auth):
        history_state = _sample_history_state()
        mock_compute = mock.AsyncMock(return_value=history_state)
        with mock.patch(
            "octobot_node.protocol.accounts_history.compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions",
            new=mock_compute,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                response = tenant_client.get("/api/v1/accounts/acc-1/historical-values")
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION
        assert body["history"]["unit"] == "USDT"
        assert body["history"]["values"][0]["total"] == 1000.0
        mock_compute.assert_awaited_once_with(TENANT_USER_ID, "acc-1")

    def test_returns_404_when_debug_routes_disabled(self, tenant_client, mock_auth):
        with mock.patch.object(
            octobot_node.config.settings,
            "is_node_side_encryption_enabled",
            True,
        ):
            response = tenant_client.get("/api/v1/accounts/acc-1/historical-values")
        assert response.status_code == 404

    def test_returns_503_when_scheduler_not_initialized(self, tenant_client, mock_auth):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=False):
            response = tenant_client.get("/api/v1/accounts/acc-1/historical-values")
        assert response.status_code == 503

    def test_returns_401_without_auth(self, client, mock_auth):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = client.get("/api/v1/accounts/acc-1/historical-values")
        assert response.status_code == 401


class TestGetAggregatedAccountHistoricalValues:
    def test_returns_aggregated_history_state(self, tenant_client, mock_auth):
        history_state = _sample_history_state()
        mock_compute = mock.AsyncMock(return_value=history_state)
        with mock.patch(
            "octobot_node.protocol.accounts_history.compute_aggregated_portfolio_historical_values_from_latest_portfolio_trades_and_transactions",
            new=mock_compute,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                response = tenant_client.get(
                    "/api/v1/accounts/aggregated/historical-values",
                    params={"is_simulated": False},
                )
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION
        assert body["history"]["unit"] == "USDT"
        mock_compute.assert_awaited_once_with(TENANT_USER_ID, is_simulated=False)

    def test_returns_404_when_debug_routes_disabled(self, tenant_client, mock_auth):
        with mock.patch.object(
            octobot_node.config.settings,
            "is_node_side_encryption_enabled",
            True,
        ):
            response = tenant_client.get(
                "/api/v1/accounts/aggregated/historical-values",
                params={"is_simulated": True},
            )
        assert response.status_code == 404

    def test_returns_503_when_scheduler_not_initialized(self, tenant_client, mock_auth):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=False):
            response = tenant_client.get(
                "/api/v1/accounts/aggregated/historical-values",
                params={"is_simulated": True},
            )
        assert response.status_code == 503

    def test_returns_401_without_auth(self, client, mock_auth):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = client.get(
                "/api/v1/accounts/aggregated/historical-values",
                params={"is_simulated": False},
            )
        assert response.status_code == 401
