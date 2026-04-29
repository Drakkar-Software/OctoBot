#  Drakkar-Software OctoBot-Commons
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
import dataclasses
import decimal

import pytest

import octobot_commons.dataclasses as commons_dataclasses
import octobot_commons.json_util as json_util


@dataclasses.dataclass
class _SampleFlexibleRecord(commons_dataclasses.FlexibleDataclass):
    label: str = ""
    nested: dict = dataclasses.field(default_factory=dict)


class TestSanitize:
    def test_decimal_in_dict_converts_to_float(self):
        payload = {"amount": decimal.Decimal("3.14")}
        assert json_util.sanitize(payload) is payload
        assert payload["amount"] == 3.14
        assert isinstance(payload["amount"], float)

    def test_nested_list_and_dict(self):
        payload = {
            "items": [
                {"x": decimal.Decimal("1")},
                [decimal.Decimal("2"), 3],
            ]
        }
        json_util.sanitize(payload)
        assert payload["items"][0]["x"] == 1.0
        assert payload["items"][1][0] == 2.0
        assert payload["items"][1][1] == 3

    def test_tuple_preserves_type(self):
        payload = ({"a": decimal.Decimal("5")},)
        result = json_util.sanitize(payload)
        assert isinstance(result, tuple)
        assert result[0]["a"] == 5.0

    def test_flexible_dataclass_mutates_nested_decimal(self):
        record = _SampleFlexibleRecord(
            label="t",
            nested={"v": decimal.Decimal("9.9")},
        )
        json_util.sanitize(record)
        assert record.nested["v"] == 9.9


class TestSanitized:
    @pytest.mark.asyncio
    async def test_wraps_async_result(self):
        @json_util.sanitized
        async def load():
            return {"d": decimal.Decimal("2.5")}

        out = await load()
        assert out == {"d": 2.5}
