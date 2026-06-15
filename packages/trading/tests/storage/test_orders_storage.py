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

import octobot_trading.personal_data as personal_data
import octobot_trading.enums as enums
import octobot_trading.storage.orders_storage as orders_storage


def _minimal_origin_value(**overrides):
    origin_value = {
        enums.ExchangeConstantsOrderColumns.AMOUNT.value: "10",
        enums.ExchangeConstantsOrderColumns.COST.value: "700",
        enums.ExchangeConstantsOrderColumns.FILLED.value: "0",
        enums.ExchangeConstantsOrderColumns.PRICE.value: "70",
        enums.ExchangeConstantsOrderColumns.FEE.value: {
            enums.FeePropertyColumns.COST.value: "0.1",
        },
    }
    origin_value.update(overrides)
    return origin_value


class TestRestoreOrderStorageOriginValue:
    def test_converts_all_present_numeric_fields(self):
        origin_value = _minimal_origin_value()
        restored_origin_value = orders_storage.restore_order_storage_origin_value(origin_value)
        assert restored_origin_value[enums.ExchangeConstantsOrderColumns.AMOUNT.value] == decimal.Decimal("10")
        assert restored_origin_value[enums.ExchangeConstantsOrderColumns.COST.value] == decimal.Decimal("700")
        assert restored_origin_value[enums.ExchangeConstantsOrderColumns.FILLED.value] == decimal.Decimal("0")
        assert restored_origin_value[enums.ExchangeConstantsOrderColumns.PRICE.value] == decimal.Decimal("70")
        assert restored_origin_value[enums.ExchangeConstantsOrderColumns.FEE.value][
            enums.FeePropertyColumns.COST.value
        ] == decimal.Decimal("0.1")

    def test_skips_missing_numeric_fields(self):
        origin_value = _minimal_origin_value()
        del origin_value[enums.ExchangeConstantsOrderColumns.COST.value]
        del origin_value[enums.ExchangeConstantsOrderColumns.FILLED.value]
        restored_origin_value = orders_storage.restore_order_storage_origin_value(origin_value)
        assert enums.ExchangeConstantsOrderColumns.COST.value not in restored_origin_value
        assert enums.ExchangeConstantsOrderColumns.FILLED.value not in restored_origin_value
        assert restored_origin_value[enums.ExchangeConstantsOrderColumns.AMOUNT.value] == decimal.Decimal("10")
        assert restored_origin_value[enums.ExchangeConstantsOrderColumns.PRICE.value] == decimal.Decimal("70")

    def test_skips_when_fee_key_missing(self):
        origin_value = _minimal_origin_value()
        del origin_value[enums.ExchangeConstantsOrderColumns.FEE.value]
        restored_origin_value = orders_storage.restore_order_storage_origin_value(origin_value)
        assert enums.ExchangeConstantsOrderColumns.FEE.value not in restored_origin_value
        assert restored_origin_value[enums.ExchangeConstantsOrderColumns.AMOUNT.value] == decimal.Decimal("10")

    def test_skips_when_fee_has_no_cost(self):
        origin_value = _minimal_origin_value(
            **{
                enums.ExchangeConstantsOrderColumns.FEE.value: {
                    enums.FeePropertyColumns.CURRENCY.value: "USDT",
                },
            }
        )
        restored_origin_value = orders_storage.restore_order_storage_origin_value(origin_value)
        assert restored_origin_value[enums.ExchangeConstantsOrderColumns.FEE.value] == {
            enums.FeePropertyColumns.CURRENCY.value: "USDT",
        }

    def test_empty_origin_dict(self):
        origin_value = {}
        restored_origin_value = orders_storage.restore_order_storage_origin_value(origin_value)
        assert restored_origin_value == {}
