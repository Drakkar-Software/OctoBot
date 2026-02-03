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
import decimal
import mock

import octobot_commons.constants
import octobot_commons.logging
import octobot_trading.personal_data as personal_data


def test_get_content_after_deltas():
    base_content = _content_with_available({
        "BTC": (0.019998, 0.1), "ETH": (0.019998, 0.1), "USDT": (10.019998, 10.1), "SOL": (0.5, 1), "USDC": (2, 2)
    })
    sub_pf = _sub_pf(
        0,
        _content_with_available({
            "BTC": (0.019998, 0.1), "ETH": (0.019998, 0.1), "USDT": (10.019998, 10.1), "SOL": (0.5, 1), "USDC": (2, 2)
        })
    )
    # no delta
    assert sub_pf.get_content_after_deltas() == base_content

    # with delta
    sub_pf.funds_deltas = _content_with_available({
        "BTC": (0.5, 0.1), "USDC": (2, 2), "ETH": (0, -0.05)
    })
    assert sub_pf.get_content_after_deltas() == _content_with_available({
        "BTC": (0.519998, 0.2), "ETH": (0.019998, 0.05), "USDT": (10.019998, 10.1), "SOL": (0.5, 1), "USDC": (4, 4)
    })


def test_get_content_from_total_deltas_and_locked_funds():
    warning_log = mock.Mock()
    error_log = mock.Mock()
    with mock.patch.object(octobot_commons.logging, "get_logger", mock.Mock(return_value=mock.Mock(warning=warning_log, error=error_log))):
        sub_pf = _sub_pf(
            0,
            _content_with_available({
                "BTC": (0.019998, 0.1), "ETH": (0.019998, 0.1), "USDT": (10.019998, 10.1), "SOL": (0.5, 1), "USDC": (2, 2)
            })
        )
        # no delta, no locked funds: only consider total holdings
        assert sub_pf.get_content_from_total_deltas_and_locked_funds() == _content_with_available({
            "BTC": (0.1, 0.1), "ETH": (0.1, 0.1), "USDT": (10.1, 10.1), "SOL": (1, 1), "USDC": (2, 2)
        })
        warning_log.assert_not_called()
        error_log.assert_not_called()

        # with delta, no locked funds: only consider total holdings
        sub_pf.funds_deltas = _content_with_available({
            "BTC": (0.5, 0.1), "USDC": (2, 2), "ETH": (0, -0.05)
        })
        assert sub_pf.get_content_from_total_deltas_and_locked_funds() == _content_with_available({
            "BTC": (0.2, 0.2), "ETH": (0.05, 0.05), "USDT": (10.1, 10.1), "SOL": (1, 1), "USDC": (4, 4)
        })
        warning_log.assert_not_called()
        error_log.assert_not_called()

        # with delta, and locked funds: consider total holdings and lock available
        sub_pf.locked_funds_by_asset = _locked_amounts_by_asset({
            "BTC": 0.1, "USDT": 10.1
        })
        assert sub_pf.get_content_from_total_deltas_and_locked_funds() == _content_with_available({
            "BTC": (0.1, 0.2), "ETH": (0.05, 0.05), "USDT": (0, 10.1), "SOL": (1, 1), "USDC": (4, 4)
        })
        warning_log.assert_not_called()
        error_log.assert_not_called()

        # no delta but locked funds are set: updated available when lock funds are set
        sub_pf.funds_deltas = {}
        assert sub_pf.get_content_from_total_deltas_and_locked_funds() == _content_with_available({
            "BTC": (0, 0.1), "ETH": (0.1, 0.1), "USDT": (0, 10.1), "SOL": (1, 1), "USDC": (2, 2)
        })
        warning_log.assert_not_called()
        error_log.assert_not_called()

        # large invalid locked funds: log error
        sub_pf.locked_funds_by_asset = _locked_amounts_by_asset({
            "BTC": 1, # will make BTC available a negative value that will be replaced with 0
            "USDT": 10.1
        })
        assert sub_pf.get_content_from_total_deltas_and_locked_funds() == _content_with_available({
            "BTC": (-0.9, 0.1), "ETH": (0.1, 0.1), "USDT": (0, 10.1), "SOL": (1, 1), "USDC": (2, 2)
        })
        warning_log.assert_not_called()
        error_log.assert_called_once()
        error_log.reset_mock()

        # small invalid locked funds: log error
        sub_pf.locked_funds_by_asset = _locked_amounts_by_asset({
            "BTC": 0.1001, # will make BTC available a negative value that will be replaced with 0
            "USDT": 10.1
        })
        assert sub_pf.get_content_from_total_deltas_and_locked_funds() == _content_with_available({
            "BTC": (-0.0001, 0.1), "ETH": (0.1, 0.1), "USDT": (0, 10.1), "SOL": (1, 1), "USDC": (2, 2)
        })
        warning_log.assert_called_once()
        warning_log.reset_mock()
        error_log.assert_not_called()


def _sub_pf(
    priority_key: float,
    content: dict[str, dict[str, decimal.Decimal]],
    funds_deltas: dict[str, dict[str, decimal.Decimal]] = None,
    missing_funds: dict[str, decimal.Decimal] = None,
    locked_funds_by_asset: dict[str, decimal.Decimal] = None,
) -> personal_data.SubPortfolioData:
    return personal_data.SubPortfolioData(
        "", "", priority_key, content, "",
        funds_deltas=funds_deltas or {},
        missing_funds=missing_funds or {},
        locked_funds_by_asset=locked_funds_by_asset or {}
    )


def _content_with_available(content: dict[str, (float, float)]) -> dict[str, dict[str, decimal.Decimal]]:
    return {
        key: {
            octobot_commons.constants.PORTFOLIO_TOTAL: decimal.Decimal(str(total)),
            octobot_commons.constants.PORTFOLIO_AVAILABLE: decimal.Decimal(str(available)),
        }
        for key, (available, total) in content.items()
    }


def _locked_amounts_by_asset(amount_by_asset: dict[str, float]) -> dict[str, decimal.Decimal]:
    return {
        asset: decimal.Decimal(str(amount))
        for asset, amount in amount_by_asset.items()
    }
