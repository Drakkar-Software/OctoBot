#  Drakkar-Software OctoBot
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


def find_nested_value(dict_, field):
    if field in dict_:
        return True, dict_[field]
    else:
        for value in dict_.values():
            if isinstance(value, dict):
                found_value, possible_value = find_nested_value(value, field)
                if found_value:
                    return found_value, possible_value
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        found_value, possible_value = find_nested_value(item, field)
                        if found_value:
                            return found_value, possible_value
    return False, field


def get_value_or_default(dictionary, key, default=None):
    if key in dictionary:
        value = dictionary[key]
        return value if value is not None else default
    return default
