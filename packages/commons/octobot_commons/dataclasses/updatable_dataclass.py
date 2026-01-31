# pylint: disable=W0212
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


@dataclasses.dataclass
class UpdatableDataclass:
    _updated_fields: list[str] = dataclasses.field(default_factory=list, kw_only=True)

    def update(self, other) -> None:
        """
        update self using another UpdatableDataclass
        :param other: the other UpdatableDataclass to update self from
        """
        for field_name in other._updated_fields:
            self_val = getattr(self, field_name)
            other_val = getattr(other, field_name)
            if isinstance(self_val, UpdatableDataclass) and other_val:
                self_val.update(other_val)
            elif (
                isinstance(self_val, list)
                and self_val
                and isinstance(self_val[0], UpdatableDataclass)
            ):
                updated_list = []
                for i, other_element in enumerate(other_val):
                    if i < len(self_val):
                        self_element = self_val[i]
                        self_element.update(other_element)
                        updated_list.append(self_element)
                    else:
                        updated_list.append(other_element)
                setattr(self, field_name, updated_list)
            elif _should_be_changed(self_val, other_val):
                setattr(self, field_name, other_val)

    def get_update(self, other):
        """
        Creates a new instance of self.__class__ which fields will be set only if they changed between self and other
        Requires a default constructor
        :param other: the other UpdatableDataclass create the update from
        :return: the UpdatableDataclass update containing differences between self and other
        (unset values in other are ignored)
        """
        update_content = self.__class__()
        for field in dataclasses.fields(self):
            field_name = field.name
            self_val = getattr(self, field_name)
            other_val = getattr(other, field_name)
            if isinstance(self_val, UpdatableDataclass) and other_val:
                update = self_val.get_update(other_val)
                setattr(update_content, field_name, update)
                if update._updated_fields:
                    update_content._updated_fields.append(field_name)
            elif (
                isinstance(self_val, list)
                and self_val
                and isinstance(self_val[0], UpdatableDataclass)
            ):
                update_list = []
                has_updates = False
                if self_val != other_val:
                    for i, other_element in enumerate(other_val):
                        if i < len(self_val):
                            self_element = self_val[i]
                            update = self_element.get_update(other_element)
                            update_list.append(update)
                            has_updates = has_updates or bool(update._updated_fields)
                        else:
                            update_list.append(other_element)
                            has_updates = True
                setattr(update_content, field_name, update_list)
                if has_updates or len(other_val) != len(self_val):
                    update_content._updated_fields.append(field_name)
            elif _should_be_changed(self_val, other_val):
                update_content._updated_fields.append(field_name)
                setattr(update_content, field_name, other_val)
        return update_content

    def to_dict_without_updated_fields(self) -> dict:
        """
        :return: same as dataclasses.asdict(self) but without the
        "_updated_fields" internal field added by this class
        """
        dict_repr = dataclasses.asdict(self)
        dict_repr.pop("_updated_fields", None)
        return dict_repr


def _should_be_changed(current_value, new_value):
    return (
        not current_value and new_value != current_value
    ) or new_value != current_value
