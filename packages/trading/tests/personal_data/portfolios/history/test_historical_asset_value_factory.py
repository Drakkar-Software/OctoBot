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
import pytest
import tinydb.table

import octobot_trading.personal_data as personal_data


def test_create_historical_asset_value_from_dict_invalid_input():
    input_1 = {
        personal_data.HistoricalAssetValue.TIMESTAMP_KEY: 11,
        f"{personal_data.HistoricalAssetValue.VALUES_KEY}_invalid": {
            "BTC": 1,
            "USD": 222
        },
    }
    with pytest.raises(KeyError):
        personal_data.create_historical_asset_value_from_dict_like_object(personal_data.HistoricalAssetValue, input_1)
    input_2 = {
        f"{personal_data.HistoricalAssetValue.VALUES_KEY}_invalid": {
            "BTC": 1,
            "USD": 222
        },
    }
    with pytest.raises(KeyError):
        personal_data.create_historical_asset_value_from_dict_like_object(personal_data.HistoricalAssetValue, input_2)


def test_create_historical_asset_value_from_dict_valid_input():
    input_1 = {
        personal_data.HistoricalAssetValue.TIMESTAMP_KEY: 11,
        personal_data.HistoricalAssetValue.VALUES_KEY: {
            "BTC": 1,
            "USD": 222
        },
    }
    historical_asset = personal_data.create_historical_asset_value_from_dict_like_object(personal_data.HistoricalAssetValue,
                                                                                         input_1)
    assert historical_asset.get_timestamp() == 11
    assert list(historical_asset.get_currencies()) == ["BTC", "USD"]
    assert historical_asset.get("BTC") == decimal.Decimal(1)
    assert historical_asset.get("USD") == decimal.Decimal(222)
    assert historical_asset.to_dict() == input_1

    input_2 = {
        personal_data.HistoricalAssetValue.TIMESTAMP_KEY: 1111111111111.222,
        personal_data.HistoricalAssetValue.VALUES_KEY: {},
    }
    assert personal_data.create_historical_asset_value_from_dict_like_object(
        personal_data.HistoricalAssetValue,
        input_2
    ).to_dict() == input_2

    # input can be a tinydb.table.Document
    assert personal_data.create_historical_asset_value_from_dict_like_object(
        personal_data.HistoricalAssetValue,
        tinydb.table.Document(input_2, 1)
    ).to_dict() == input_2

    input_3 = {
        personal_data.HistoricalAssetValue.TIMESTAMP_KEY: 0,
        personal_data.HistoricalAssetValue.VALUES_KEY: {
            "BTC": 1.7777777777777,
            "XXXXX": 0
        },
    }
    assert personal_data.create_historical_asset_value_from_dict_like_object(
        personal_data.HistoricalAssetValue,
        input_3
    ).to_dict() == input_3
