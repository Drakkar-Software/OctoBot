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
import re

import octobot_trading.modes.script_keywords.dsl.values as dsl_values


# Do not compile regex to use builtin regex cache
# (re always looks into cache 1st and compile regex are not cached)
QUANTITY_REGEX = r"([+-]?(?:0|[1-9]\d*)(?:\.\d*)?(?:[eE][+\-]?\d+)?)"


def parse_quantity(input_offset) -> (dsl_values.QuantityType, decimal.Decimal):
    input_offset = "" if input_offset is None else input_offset
    input_offset = str(input_offset)
    value = None
    try:
        quantity_type, value = dsl_values.QuantityType.parse(re.sub(QUANTITY_REGEX, "", input_offset))
        if input_offset == value:
            offset_value = None
        else:
            # skip fist char before replacement when 1st char is not re quantity_type value to
            # avoid replacing a part of the number ex:
            # "1e+9e" => should only replace the last "e"
            # "e1e+9" => should only replace the first "e"
            if value:
                quantity_type_pattern_index = input_offset.find(value)
                if quantity_type_pattern_index > 0 and quantity_type_pattern_index + len(value) < len(input_offset):
                    # "1e+9e" - like case
                    quantity_type_pattern_index = input_offset.rfind(value)
                if quantity_type_pattern_index >= 0:
                    input_offset = f"{input_offset[:quantity_type_pattern_index]}" \
                                   f"{input_offset[quantity_type_pattern_index + len(value):]}"
            offset_value = decimal.Decimal(input_offset)
        return quantity_type, offset_value
    except decimal.InvalidOperation as e:
        raise RuntimeError(f"Can't parse {input_offset.replace(value, '')} as decimal.Decimal ({e})") from e
    except ValueError:
        return dsl_values.QuantityType.UNKNOWN, None
