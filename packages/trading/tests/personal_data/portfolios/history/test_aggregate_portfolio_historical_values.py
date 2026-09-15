#  Drakkar-Software OctoBot-Trading
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

import datetime

import pytest

import octobot_protocol.models as protocol_models

import octobot_trading.personal_data.portfolios.history.aggregate_portfolio_historical_values as aggregate_portfolio_historical_values_module


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

        aggregated = aggregate_portfolio_historical_values_module.aggregate_portfolio_historical_values(
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

        aggregated = aggregate_portfolio_historical_values_module.aggregate_portfolio_historical_values(
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

        aggregated = aggregate_portfolio_historical_values_module.aggregate_portfolio_historical_values(
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

        aggregated = aggregate_portfolio_historical_values_module.aggregate_portfolio_historical_values(
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

        aggregated = aggregate_portfolio_historical_values_module.aggregate_portfolio_historical_values(
            [account_a_history, account_b_history],
        )

        assert aggregated[0].total == pytest.approx(150.0)
        assets_by_symbol = _spot_assets_by_symbol(aggregated[0])
        assert assets_by_symbol["USDT"].holdings == pytest.approx(50.0)
        assert assets_by_symbol["USDT"].value == pytest.approx(50.0)
