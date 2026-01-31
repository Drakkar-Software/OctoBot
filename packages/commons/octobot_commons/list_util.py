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
import functools


def flatten_list(list_to_flatten):
    """
    Flatten the list :list_to_flatten:
    :param list_to_flatten: the list to flatten
    :return: the flattened list
    """
    return functools.reduce(
        lambda first_level, second_level: first_level + second_level, list_to_flatten
    )


def deduplicate(elements: list) -> list:
    """
    remove duplicated values from a list while preserving order
    """
    # from https://stackoverflow.com/questions/480214/how-do-i-remove-duplicates-from-a-list-while-preserving-order
    seen = set()
    seen_add = seen.add
    return [x for x in elements if not (x in seen or seen_add(x))]
