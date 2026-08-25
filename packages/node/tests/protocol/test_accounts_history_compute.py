import datetime
import decimal
import json
import os
import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants

import octobot_node.protocol.accounts_history as accounts_history_module


def _make_account(
    account_id: str,
    assets: dict[str, float],
    exchange: str = "binance",
    sandboxed: bool = False,
) -> protocol_models.Account:
    detailed_assets = [
        protocol_models.DetailedAsset(symbol=symbol, total=amount, available=amount)
        for symbol, amount in assets.items()
    ]
    exchange_config = protocol_models.ExchangeConfig(
        id="cfg1", name="test", exchange=exchange, sandboxed=sandboxed,
        historical_trade_symbols=["BTC/USDT"],
    )
    exchange_account = protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id="remote1",
        exchange_config_ids=["cfg1"],
    )
    return protocol_models.Account(
        id=account_id,
        name="Test",
        is_simulated=False,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        specifics=protocol_models.AccountSpecifics(actual_instance=exchange_account),
        assets=[
            protocol_models.DetailedAssetsForTradingType(
                trading_type=protocol_models.TradingType.SPOT,
                assets=detailed_assets,
            )
        ],
    )


class TestPortfolioFromAccountAssets:
    def test_converts_assets_to_portfolio_dict(self):
        account = _make_account("a1", {"BTC": 1.5, "USDT": 10000.0})
        portfolio = accounts_history_module._portfolio_from_account_assets(account)
        assert portfolio["BTC"][commons_constants.PORTFOLIO_TOTAL] == decimal.Decimal("1.5")
        assert portfolio["USDT"][commons_constants.PORTFOLIO_TOTAL] == decimal.Decimal("10000.0")

    def test_empty_assets(self):
        account = mock.MagicMock(spec=protocol_models.Account)
        account.assets = None
        portfolio = accounts_history_module._portfolio_from_account_assets(account)
        assert portfolio == {}


class TestComputePortfolioHistoricalValues:
    @pytest.mark.asyncio
    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    @mock.patch("octobot_sync.sync.collection_providers.AccountTradingProvider")
    async def test_empty_trading_returns_empty_history(self, mock_trading_provider, mock_account_provider, tmp_path):
        account = _make_account("a1", {"BTC": 1.0})
        mock_account_provider.instance.return_value.get_account.return_value = account
        mock_account_provider.instance.return_value.get_exchange_config.return_value = protocol_models.ExchangeConfig(
            id="cfg1", name="test", exchange="binance", sandboxed=False,
            historical_trade_symbols=["BTC/USDT"],
        )

        trading_state = mock.MagicMock()
        trading_state.account_trading.trades = []
        trading_state.account_trading.transactions = []
        mock_trading_provider.instance.return_value.load_state.return_value = trading_state

        result = await accounts_history_module.compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
            "user1", "a1",
        )
        assert result.version == sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION
        # No trades/transactions → no history values.
        if result.history is not None:
            assert result.history.values is None or len(result.history.values) == 0


class TestBuildPortfolioHistoricalValues:
    @pytest.mark.asyncio
    @mock.patch(
        "octobot_flow.logic.portfolio_history.portfolio_value_history.compute_daily_portfolio_values",
    )
    @mock.patch("octobot_trading.api.load_latest_tickers", new_callable=mock.AsyncMock)
    @mock.patch("octobot_trading.api.load_daily_prices", new_callable=mock.AsyncMock)
    @mock.patch(
        "octobot_trading.api.compute_portfolio_historical_holdings_from_latest_portfolio_trades_and_transations",
    )
    @mock.patch("octobot_sync.sync.collection_providers.AccountTradingProvider")
    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    async def test_maps_day_assets_to_protocol_models(
        self,
        mock_account_provider,
        mock_trading_provider,
        mock_daily_holdings,
        mock_load_daily_prices,
        mock_load_latest_tickers,
        mock_compute_daily_values,
    ):
        account = _make_account("a1", {"BTC": 1.0, "USDT": 100.0})
        mock_account_provider.instance.return_value.get_account.return_value = account
        mock_account_provider.instance.return_value.get_exchange_config.return_value = protocol_models.ExchangeConfig(
            id="cfg1", name="test", exchange="binance", sandboxed=False,
            historical_trade_symbols=["BTC/USDT"],
        )
        trading_state = mock.MagicMock()
        trading_state.account_trading.trades = [mock.MagicMock()]
        trading_state.account_trading.transactions = []
        mock_trading_provider.instance.return_value.load_state.return_value = trading_state
        mock_daily_holdings.return_value = {86400.0: {"BTC": {"total": decimal.Decimal("1")}}}
        mock_load_daily_prices.return_value = {}
        mock_load_latest_tickers.return_value = {}
        mock_compute_daily_values.return_value = [
            protocol_models.PortfolioHistoricalValue(
                timestamp=datetime.datetime.fromtimestamp(86400.0, tz=datetime.timezone.utc),
                total=41000.0,
                assets=[
                    protocol_models.HistoricalAssetsForTradingType(
                        trading_type=protocol_models.TradingType.SPOT,
                        assets=[
                            protocol_models.HistoricalAssetValue(
                                symbol="BTC", holdings=1.0, value=40000.0,
                            ),
                            protocol_models.HistoricalAssetValue(
                                symbol="USDT", holdings=1000.0, value=1000.0,
                            ),
                        ],
                    )
                ],
            )
        ]

        result = await accounts_history_module.compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
            "user1", "a1",
        )

        history_value = result.history.values[0]
        assert history_value.assets is not None
        spot_assets = history_value.assets[0]
        assert spot_assets.trading_type == protocol_models.TradingType.SPOT
        assets_by_symbol = {asset.symbol: asset for asset in spot_assets.assets}
        assert assets_by_symbol["BTC"].holdings == pytest.approx(1.0)
        assert assets_by_symbol["BTC"].value == pytest.approx(40000.0)
        assert assets_by_symbol["USDT"].holdings == pytest.approx(1000.0)
        assert assets_by_symbol["USDT"].value == pytest.approx(1000.0)


def _spot_assets(
    *assets: tuple[str, float, float],
) -> list[protocol_models.HistoricalAssetsForTradingType]:
    return [
        protocol_models.HistoricalAssetsForTradingType(
            trading_type=protocol_models.TradingType.SPOT,
            assets=[
                protocol_models.HistoricalAssetValue(
                    symbol=symbol,
                    holdings=holdings,
                    value=value,
                )
                for symbol, holdings, value in assets
            ],
        )
    ]


def _spot_assets_by_symbol(
    history_value: protocol_models.PortfolioHistoricalValue,
) -> dict[str, protocol_models.HistoricalAssetValue]:
    assert history_value.assets is not None
    spot_assets = history_value.assets[0]
    return {asset.symbol: asset for asset in spot_assets.assets}


class TestAggregatePortfolioHistoricalValues:
    def test_sums_totals_for_overlapping_and_non_overlapping_days(self):
        day_one = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        day_two = datetime.datetime(2024, 1, 2, tzinfo=datetime.timezone.utc)
        day_three = datetime.datetime(2024, 1, 3, tzinfo=datetime.timezone.utc)
        account_a_history = [
            protocol_models.PortfolioHistoricalValue(timestamp=day_one, total=100.0),
            protocol_models.PortfolioHistoricalValue(timestamp=day_two, total=200.0),
        ]
        account_b_history = [
            protocol_models.PortfolioHistoricalValue(timestamp=day_two, total=50.0),
            protocol_models.PortfolioHistoricalValue(timestamp=day_three, total=75.0),
        ]

        aggregated = accounts_history_module._aggregate_portfolio_historical_values(
            [account_a_history, account_b_history],
        )

        assert len(aggregated) == 3
        assert aggregated[0].total == pytest.approx(100.0)
        assert aggregated[1].total == pytest.approx(250.0)
        assert aggregated[2].total == pytest.approx(75.0)
        assert aggregated[0].assets is None

    def test_sums_accounts_on_same_utc_day_with_misaligned_timestamps(self):
        day_midnight = datetime.datetime(2026, 2, 26, 0, 0, tzinfo=datetime.timezone.utc)
        day_sixteen_hundred = datetime.datetime(2026, 2, 26, 16, 0, tzinfo=datetime.timezone.utc)
        account_a_history = [
            protocol_models.PortfolioHistoricalValue(timestamp=day_midnight, total=425.60),
        ]
        account_b_history = [
            protocol_models.PortfolioHistoricalValue(timestamp=day_sixteen_hundred, total=-237.20),
        ]

        aggregated = accounts_history_module._aggregate_portfolio_historical_values(
            [account_a_history, account_b_history],
        )

        assert len(aggregated) == 1
        assert aggregated[0].timestamp == day_midnight
        assert aggregated[0].total == pytest.approx(188.4)

    def test_sums_assets_by_symbol_across_accounts(self):
        day_one = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        account_a_history = [
            protocol_models.PortfolioHistoricalValue(
                timestamp=day_one,
                total=40100.0,
                assets=_spot_assets(("BTC", 1.0, 40000.0), ("USDT", 100.0, 100.0)),
            ),
        ]
        account_b_history = [
            protocol_models.PortfolioHistoricalValue(
                timestamp=day_one,
                total=23000.0,
                assets=_spot_assets(("BTC", 0.5, 20000.0), ("ETH", 2.0, 3000.0)),
            ),
        ]

        aggregated = accounts_history_module._aggregate_portfolio_historical_values(
            [account_a_history, account_b_history],
        )

        assert len(aggregated) == 1
        assert aggregated[0].total == pytest.approx(63100.0)
        assets_by_symbol = _spot_assets_by_symbol(aggregated[0])
        assert assets_by_symbol["BTC"].holdings == pytest.approx(1.5)
        assert assets_by_symbol["BTC"].value == pytest.approx(60000.0)
        assert assets_by_symbol["ETH"].holdings == pytest.approx(2.0)
        assert assets_by_symbol["ETH"].value == pytest.approx(3000.0)
        assert assets_by_symbol["USDT"].holdings == pytest.approx(100.0)
        assert assets_by_symbol["USDT"].value == pytest.approx(100.0)

    def test_buckets_misaligned_timestamps_and_assets_on_same_utc_day(self):
        day_midnight = datetime.datetime(2026, 2, 26, 0, 0, tzinfo=datetime.timezone.utc)
        day_sixteen_hundred = datetime.datetime(2026, 2, 26, 16, 0, tzinfo=datetime.timezone.utc)
        account_a_history = [
            protocol_models.PortfolioHistoricalValue(
                timestamp=day_midnight,
                total=40000.0,
                assets=_spot_assets(("BTC", 1.0, 40000.0)),
            ),
        ]
        account_b_history = [
            protocol_models.PortfolioHistoricalValue(
                timestamp=day_sixteen_hundred,
                total=20000.0,
                assets=_spot_assets(("BTC", 0.5, 20000.0)),
            ),
        ]

        aggregated = accounts_history_module._aggregate_portfolio_historical_values(
            [account_a_history, account_b_history],
        )

        assert len(aggregated) == 1
        assets_by_symbol = _spot_assets_by_symbol(aggregated[0])
        assert assets_by_symbol["BTC"].holdings == pytest.approx(1.5)
        assert assets_by_symbol["BTC"].value == pytest.approx(60000.0)

    def test_keeps_assets_from_accounts_that_have_breakdown_when_other_has_none(self):
        day_one = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        account_a_history = [
            protocol_models.PortfolioHistoricalValue(timestamp=day_one, total=100.0, assets=None),
        ]
        account_b_history = [
            protocol_models.PortfolioHistoricalValue(
                timestamp=day_one,
                total=50.0,
                assets=_spot_assets(("USDT", 50.0, 50.0)),
            ),
        ]

        aggregated = accounts_history_module._aggregate_portfolio_historical_values(
            [account_a_history, account_b_history],
        )

        assert aggregated[0].total == pytest.approx(150.0)
        assets_by_symbol = _spot_assets_by_symbol(aggregated[0])
        assert assets_by_symbol["USDT"].holdings == pytest.approx(50.0)
        assert assets_by_symbol["USDT"].value == pytest.approx(50.0)


class TestComputeAggregatedPortfolioHistoricalValues:
    @pytest.mark.asyncio
    @mock.patch(
        "octobot_node.protocol.accounts_history.compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions",
        new_callable=mock.AsyncMock,
    )
    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    async def test_filters_accounts_by_is_simulated_and_aggregates(
        self,
        mock_account_provider,
        mock_compute_per_account,
    ):
        real_account = _make_account("real-1", {"USDT": 100.0})
        simulated_account = _make_account("sim-1", {"USDT": 200.0})
        simulated_account.is_simulated = True
        mock_account_provider.instance.return_value.list_accounts.return_value = [
            real_account,
            simulated_account,
        ]
        day_one = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        mock_compute_per_account.side_effect = [
            protocol_models.PortfolioHistoricalValuesState(
                version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
                history=protocol_models.PortfolioHistoricalValues(
                    unit="USDT",
                    values=[protocol_models.PortfolioHistoricalValue(timestamp=day_one, total=100.0)],
                ),
            ),
            protocol_models.PortfolioHistoricalValuesState(
                version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
                history=protocol_models.PortfolioHistoricalValues(
                    unit="USDT",
                    values=[protocol_models.PortfolioHistoricalValue(timestamp=day_one, total=200.0)],
                ),
            ),
        ]

        result = await accounts_history_module.compute_aggregated_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
            "user1",
            is_simulated=False,
        )

        assert mock_compute_per_account.await_count == 1
        mock_compute_per_account.assert_awaited_with("user1", "real-1", data_root=None)
        assert result.history is not None
        assert result.history.values[0].total == pytest.approx(100.0)

    @pytest.mark.asyncio
    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    async def test_returns_empty_state_when_no_matching_accounts(self, mock_account_provider):
        mock_account_provider.instance.return_value.list_accounts.return_value = []

        result = await accounts_history_module.compute_aggregated_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
            "user1",
            is_simulated=True,
        )

        assert result.history is None
