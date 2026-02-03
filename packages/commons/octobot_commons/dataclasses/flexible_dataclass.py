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
import typing


@dataclasses.dataclass
class FlexibleDataclass:
    _class_field_cache: typing.ClassVar[dict] = {}
    """
    Implements from_dict which can be called to instantiate a new instance of this class from a dict. Using from_dict 
    ignores any additional key from the given dict that is not defined as a dataclass field.
    Nested dataclasses to be parsed inside a list or other container should be calling .from_dict in __post_init__
    """

    @classmethod
    def from_dict(cls, dict_value: dict):
        """
        Creates a new instance of cls from the given dict, ignoring additional dict values
        """
        if isinstance(dict_value, dict):
            fields_values = {
                k: _get_nested_class(v, cls._class_field_cache[k])
                for k, v in dict_value.items()
                if k in cls.get_field_names()
            }
            try:
                return cls(**fields_values)
            except TypeError as e:
                raise TypeError(
                    f"Invalid {cls.__name__} input in from_dict(): {e}"
                ) from e
        return dict_value

    @classmethod
    def get_field_names(cls):
        """
        :return a generator over the given FlexibleDataclass field names
        """
        if not cls._class_field_cache:
            cls._class_field_cache = {
                f.name: f.type for f in dataclasses.fields(cls) if f.init
            }
        return cls._class_field_cache.keys()


def _get_nested_class(value, target_type):
    # does not support lists or dicts
    if isinstance(target_type, type) and issubclass(target_type, FlexibleDataclass):
        return target_type.from_dict(value)
    return value
