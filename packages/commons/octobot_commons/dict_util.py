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


def find_nested_value(dict_, field, list_indexes=None):
    """
    Find a nested value in a dict
    :param dict_: the dict
    :param field: the field to search
    :param list_indexes: indexes to go to on list elements. If not provided, each element of each list is explored
    :return: a tuple : True if found else False, the dict at field value else the field
    """
    if field in dict_:
        return True, dict_[field]
    for value in dict_.values():
        found_value = False
        possible_value = None
        if isinstance(value, dict):
            found_value, possible_value = find_nested_value(
                value, field, list_indexes=list_indexes
            )
        elif isinstance(value, list):
            found_value, possible_value = _find_nested_value_in_list(
                value, field, list_indexes
            )
        if found_value:
            return found_value, possible_value
    return False, field


def _find_nested_value_in_list(list_value, field, list_indexes):
    if list_indexes:
        # list_indexes is provided: only look at the given index
        try:
            item = list_value[list_indexes[0]]
            if isinstance(item, dict):
                found_value, possible_value = find_nested_value(
                    item, field, list_indexes=list_indexes[1:]
                )
                if found_value:
                    return found_value, possible_value
        except IndexError:
            pass
    else:
        for item in list_value:
            if isinstance(item, dict):
                found_value, possible_value = find_nested_value(
                    item, field, list_indexes=list_indexes
                )
                if found_value:
                    return found_value, possible_value
    return False, field


def nested_update_dict(
    base_dict: dict, updated_dict: dict, list_indexes=None, ignore_lists=False
):
    """
     Updates a dict with values from another but keeps the 1st dict values when not specified
     in the update dict. Handle nested values unlike the default dict.update().
     If a list is found in the dict, elements of the list are all updated
    :param base_dict: the dict to be updated
    :param updated_dict: the dict to take updated values from
    :param list_indexes: indexes to go to on list elements. If not provided, each element of each list is explored
    :param ignore_lists: when True, lists are not updated
    """
    if isinstance(base_dict, list):
        if ignore_lists:
            return base_dict
        if list_indexes:
            nested_update_dict(
                base_dict[list_indexes[0]],
                updated_dict,
                list_indexes=list_indexes[1:],
                ignore_lists=ignore_lists,
            )
        else:
            for element in base_dict:
                nested_update_dict(element, updated_dict)
        return base_dict
    for key, val in updated_dict.items():
        if isinstance(val, dict):
            if key in base_dict:
                nested_update_dict(
                    base_dict[key],
                    val,
                    list_indexes=list_indexes,
                    ignore_lists=ignore_lists,
                )
            else:
                base_dict[key] = val
        elif ignore_lists and key in base_dict and isinstance(base_dict[key], list):
            # list should be ignored
            pass
        else:
            base_dict[key] = val
    return base_dict


def check_and_merge_values_from_reference(
    current_dict, reference_dict, exception_list, logger=None
):
    """
     Check and merge dicts
    :param current_dict: the dict to be merged
    :param reference_dict: the reference dict
    :param exception_list: the merge exception list
    :param logger: the logger
    """
    for key, val in reference_dict.items():
        if key not in current_dict:
            current_dict[key] = val
            if logger is not None:
                logger.warning(
                    f"Missing {key} in configuration, added default value: {val}"
                )
        elif isinstance(val, dict) and key not in exception_list:
            check_and_merge_values_from_reference(
                current_dict[key], val, exception_list, logger=logger
            )


def contains_each_element(element, val_by_keys_to_find):
    """
     Check if each element in val_by_keys_to_find is in element
    :param element: the dict to look into
    :param val_by_keys_to_find: the dict of elements to find
    """
    try:
        for key, val in val_by_keys_to_find.items():
            if element[key] != val:
                return False
        return True
    except KeyError:
        return False
