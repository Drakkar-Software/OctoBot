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
import json
import pydantic

import octobot_commons.dataclasses.flexible_dataclass as flexible_dataclass


class MinimizableDataclass(flexible_dataclass.FlexibleDataclass):
    def to_dict(self, include_default_values=True) -> dict:
        """
        Creates a new dict from self. Recursively processes any MinimizableDataclass instance attribute.
        Pydantic models are converted via json.loads(model.model_dump_json()).
        """
        if include_default_values:
            return {
                f.name: _convert_value_for_dict(getattr(self, f.name), include_default_values)
                for f in dataclasses.fields(self)
            }
        factory = _asdict_without_default_factory(
            (self.__class__,)
            + tuple(
                (
                    getattr(self, attr.name)[0].__class__
                    if isinstance(getattr(self, attr.name), list)
                    and getattr(self, attr.name)
                    else getattr(self, attr.name).__class__
                )
                for attr in dataclasses.fields(self)
            ),
            include_default_values=include_default_values,
        )
        return dataclasses.asdict(self, dict_factory=factory)

def _convert_value_for_dict(val, include_default_values: bool):
    """Convert a value to a dict-serializable form, handling Pydantic models and nested MinimizableDataclass."""
    if isinstance(val, flexible_dataclass.FlexibleDataclass):
        if to_dict_method := getattr(val, "to_dict", None):
            return to_dict_method(include_default_values=include_default_values)
        return {
            f.name: _convert_value_for_dict(getattr(val, f.name), include_default_values)
            for f in dataclasses.fields(val)
        }
    if isinstance(val, list):
        return [_convert_value_for_dict(v, include_default_values) for v in val]
    if isinstance(val, dict):
        return {k: _convert_value_for_dict(v, include_default_values) for k, v in val.items()}
    if isinstance(val, pydantic.BaseModel):
        return json.loads(val.model_dump_json(indent=None, exclude_defaults=True))
    return val


def _asdict_without_default_factory(possible_classes, include_default_values=True):
    def factory(obj) -> dict:
        formatted_dict = {}
        found_class = None
        for possible_class in possible_classes:
            if possible_class in (int, float, str, list, dict):
                continue
            if not dataclasses.is_dataclass(possible_class):
                continue
            if all(key in possible_class.__dataclass_fields__ for key, _ in obj):
                found_class = possible_class
        if found_class is None:
            return dict(obj)
        for key, val in obj:
            field = found_class.__dataclass_fields__[key]
            default_field_value = field.default
            if default_field_value is dataclasses.MISSING:
                default_factory = field.default_factory
                if default_factory is not dataclasses.MISSING:
                    default_field_value = default_factory()
            if default_field_value is dataclasses.MISSING or default_field_value != val:
                formatted_dict[key] = _convert_value_for_dict(val, include_default_values)

        return formatted_dict

    return factory
