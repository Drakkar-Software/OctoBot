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

import octobot_commons.dsl_interpreter
import octobot_commons.tentacles_management
import octobot_commons.constants


@functools.lru_cache(maxsize=16)
def get_all_operators(
    *libraries: str,
) -> list["octobot_commons.dsl_interpreter.Operator"]:
    """
    Get all operators from the DSL interpreter.
    This function is cached and will return the same list of operators every time.
    All operators must be subclasses of octobot_commons.dsl_interpreter.Operator
    All operators must have been imported before calling this function for the first time.
    :param libraries: List of libraries to filter operators by. If None, all operators will be returned.
    By default, operators are in the octobot_commons.constants.BASE_OPERATORS_LIBRARY library.
    """
    libraries_filter = set(libraries) if libraries else None
    all_with_abstracts = (
        operator
        for operator in octobot_commons.tentacles_management.get_all_classes_from_parent(
            octobot_commons.dsl_interpreter.Operator
        )
        if (
            libraries_filter is None
            or operator.get_library()
            in libraries_filter  # pylint: disable=unsupported-membership-test
        )
        # contextual operators should not be included by default
        and operator.get_library()
        != octobot_commons.constants.CONTEXTUAL_OPERATORS_LIBRARY
    )
    non_abstract_operators = []
    for operator in all_with_abstracts:
        try:
            operator.get_name()
            non_abstract_operators.append(operator)
        except NotImplementedError:
            # this is an abstract operator
            pass
    return non_abstract_operators


def clear_get_all_operators_cache():
    """
    Clear the cache of the get_all_operators function.
    """
    get_all_operators.cache_clear()
