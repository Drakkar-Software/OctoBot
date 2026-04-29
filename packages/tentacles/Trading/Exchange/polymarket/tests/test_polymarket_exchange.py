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
import datetime
import decimal
import unittest.mock as mock

import pytest

import octobot_trading.constants as trading_constants
import tentacles.Trading.Exchange.polymarket.polymarket_exchange as polymarket_exchange
from tentacles.Trading.Exchange.polymarket.ccxt.polymarket_async import polymarket as PolymarketCCXT


def test_parse_end_date_returns_none_for_invalid_input():
    assert polymarket_exchange._parse_end_date(None) is None
    assert polymarket_exchange._parse_end_date("not-a-date") is None
    assert polymarket_exchange._parse_end_date("") is None


def test_parse_end_date_parses_explicit_datetime_strings():
    assert polymarket_exchange._parse_end_date("2026-02-19T18:45:00Z") == datetime.datetime(2026, 2, 19, 18, 45, 0)
    assert polymarket_exchange._parse_end_date("2026-02-19T18:45:00+00:00") == datetime.datetime(2026, 2, 19, 18, 45, 0)


def test_parse_end_date_date_only_string_is_end_of_day():
    # Bug: "2026-02-19" was parsed as midnight (00:00:00), making positions appear
    # expired all day even when the market was still active. Fix: treat as 23:59:59.
    result = polymarket_exchange._parse_end_date("2026-02-19")
    assert result == datetime.datetime(2026, 2, 19, 23, 59, 59)


def test_is_position_expired_no_end_date():
    assert polymarket_exchange._is_position_expired({"info": {}}) is False
    assert polymarket_exchange._is_position_expired({}) is False


def test_is_position_expired_explicit_past_datetime():
    assert polymarket_exchange._is_position_expired({"info": {"endDate": "2020-01-01T12:00:00Z"}}) is True


def test_is_position_expired_explicit_future_datetime():
    assert polymarket_exchange._is_position_expired({"info": {"endDate": "2099-01-01T12:00:00Z"}}) is False


def test_is_position_expired_date_only_yesterday():
    yesterday = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    assert polymarket_exchange._is_position_expired({"info": {"endDate": yesterday}}) is True


def test_is_position_expired_date_only_tomorrow():
    tomorrow = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    assert polymarket_exchange._is_position_expired({"info": {"endDate": tomorrow}}) is False


def test_is_position_expired_date_only_today():
    # Regression: a position with endDate = today's date must NOT be expired during the day.
    # Celtic FC vs Stuttgart (2026-02-19) was filtered at 20:12 UTC because "2026-02-19"
    # was treated as midnight, silently dropping the position and giving Tiafoe the full
    # 50% portfolio allocation instead of a proportional ~22%.
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    assert polymarket_exchange._is_position_expired({"info": {"endDate": today}}) is False


def test_is_position_expired_celtic_fc_regression():
    # Simulate 20:12 UTC on 2026-02-19: end-of-day (23:59:59) must be after that time.
    simulated_now = datetime.datetime(2026, 2, 19, 20, 12, 21)
    parsed = polymarket_exchange._parse_end_date("2026-02-19")
    assert parsed is not None
    assert parsed >= simulated_now


def test_convert_portfolio_assets_aliases_polygon_usdc_e_to_usdc():
    portfolio = {
        "USDC.e": {
            trading_constants.CONFIG_PORTFOLIO_FREE: decimal.Decimal("42"),
            trading_constants.CONFIG_PORTFOLIO_USED: decimal.Decimal("0"),
            trading_constants.CONFIG_PORTFOLIO_TOTAL: decimal.Decimal("42"),
        }
    }

    converted = polymarket_exchange._convert_portfolio_assets(portfolio)

    assert "USDC.e" not in converted
    assert converted["USDC"] == portfolio["USDC.e"]


def test_convert_portfolio_assets_merges_alias_into_existing_usdc():
    portfolio = {
        "USDC": {
            trading_constants.CONFIG_PORTFOLIO_FREE: decimal.Decimal("3"),
            trading_constants.CONFIG_PORTFOLIO_USED: decimal.Decimal("1"),
            trading_constants.CONFIG_PORTFOLIO_TOTAL: decimal.Decimal("4"),
        },
        "USDC.e": {
            trading_constants.CONFIG_PORTFOLIO_FREE: decimal.Decimal("2"),
            trading_constants.CONFIG_PORTFOLIO_USED: decimal.Decimal("4"),
            trading_constants.CONFIG_PORTFOLIO_TOTAL: decimal.Decimal("6"),
        },
        "DAI": {
            trading_constants.CONFIG_PORTFOLIO_FREE: decimal.Decimal("10"),
            trading_constants.CONFIG_PORTFOLIO_USED: decimal.Decimal("0"),
            trading_constants.CONFIG_PORTFOLIO_TOTAL: decimal.Decimal("10"),
        },
    }

    converted = polymarket_exchange._convert_portfolio_assets(portfolio)

    assert "USDC.e" not in converted
    assert converted["USDC"][trading_constants.CONFIG_PORTFOLIO_FREE] == decimal.Decimal("5")
    assert converted["USDC"][trading_constants.CONFIG_PORTFOLIO_USED] == decimal.Decimal("5")
    assert converted["USDC"][trading_constants.CONFIG_PORTFOLIO_TOTAL] == decimal.Decimal("10")
    assert converted["DAI"] == portfolio["DAI"]


def test_convert_portfolio_assets_none_portfolio():
    assert polymarket_exchange._convert_portfolio_assets(None) is None


@pytest.mark.asyncio
async def test_fetch_tickers_with_symbols_only_posts_specified_token_ids():
    exchange = PolymarketCCXT({})
    exchange.markets = {
        "SYM_A/USDC": {"id": "token_id_A", "symbol": "SYM_A/USDC", "type": "option"},
        "SYM_B/USDC": {"id": "token_id_B", "symbol": "SYM_B/USDC", "type": "option"},
    }
    exchange.symbols = ["SYM_A/USDC", "SYM_B/USDC"]
    prices_response = {"token_id_A": {"BUY": "0.95", "SELL": "0.94"}}

    with (
        mock.patch.object(exchange, "load_markets", new=mock.AsyncMock()),
        mock.patch.object(exchange, "clob_public_post_prices",
                          new=mock.AsyncMock(return_value=prices_response)) as mock_prices,
        mock.patch.object(exchange, "parse_ticker", return_value={"symbol": "SYM_A/USDC", "close": 0.95}),
    ):
        tickers = await exchange.fetch_tickers(symbols=["SYM_A/USDC"])

    assert mock_prices.call_count >= 1
    for call_args in mock_prices.call_args_list:
        token_ids_in_batch = {r["token_id"] for r in call_args.args[0]["requests"]}
        assert "token_id_B" not in token_ids_in_batch
    assert "SYM_A/USDC" in tickers
    assert "SYM_B/USDC" not in tickers
