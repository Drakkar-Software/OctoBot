#  Drakkar-Software OctoBot-Backtesting
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
import octobot_backtesting.api as api


def _get_default_config():
    return {
        "crypto-currencies": {
            "Bitcoin": {
                "pairs": [
                    "BTC/USD"
                ]
            }
        },
        "trader-simulator": {
            "enabled": True,
            "fees": {
                "maker": 0.07,
                "taker": 0.07
            },
            "starting-portfolio": {
                "BTC": 0.5,
                "USDT": 5000
            }
        },
        "trading": {
            "reference-market": "BTC",
            "risk": 1
        }
    }


def test_is_backtesting_enabled():
    assert api.is_backtesting_enabled({}) is False
    assert api.is_backtesting_enabled({"backtesting": {}}) is False
    assert api.is_backtesting_enabled({"backtesting": {"enabled": False}}) is False
    assert api.is_backtesting_enabled({"backtesting": {"enabled": True}}) is True


def test_get_backtesting_data_files():
    assert api.get_backtesting_data_files({}) == []
    assert api.get_backtesting_data_files({"backtesting": {}}) == []
    assert api.get_backtesting_data_files({"backtesting": {"files": []}}) == []
    assert api.get_backtesting_data_files({"backtesting": {"files": ["t", "1"]}}) == ["t", "1"]
