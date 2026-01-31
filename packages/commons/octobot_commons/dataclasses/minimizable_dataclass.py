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
import octobot_commons.dataclasses.flexible_dataclass as flexible_dataclass


class MinimizableDataclass(flexible_dataclass.FlexibleDataclass):
    def to_dict(self, include_default_values=True) -> dict:
        """
        Creates a new dict from self. Recursively processes any MinimizableDataclass instance attribute
        """
        if include_default_values:
            # use default factory
            return dataclasses.asdict(self)
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
            )
        )
        return dataclasses.asdict(self, dict_factory=factory)


def _asdict_without_default_factory(possible_classes):
    def factory(obj) -> dict:
        formatted_dict = {}
        found_class = None
        for possible_class in possible_classes:
            if possible_class in (int, float, str, list, dict):
                continue
            if all(key in possible_class.__dataclass_fields__ for key, _ in obj):
                found_class = possible_class
        if found_class is None:
            # class not found, include all values
            return dict(obj)
        for key, val in obj:
            default_field_value = found_class.__dataclass_fields__[key].default
            if default_field_value is dataclasses.MISSING and (
                found_class.__dataclass_fields__[key].default_factory
                is not dataclasses.MISSING
            ):
                # try with default factory
                default_field_value = found_class.__dataclass_fields__[
                    key
                ].default_factory()
            if default_field_value is dataclasses.MISSING or default_field_value != val:
                formatted_dict[key] = val

        return formatted_dict

    return factory
