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

import tentacles.Trading.Exchange.polymarket.polymarket_exchange as polymarket_exchange


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
