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
import octobot_commons.tentacles_management as tentacles_management
import octobot_commons.display.display_translator as display_translator


def display_translator_factory(**kwargs):
    """
    Returns a new instance of the available display_translator.DisplayTranslator implementation
    :param kwargs: kwargs to pass to the construction
    :return: the created instance
    """
    return tentacles_management.get_single_deepest_child_class(
        display_translator.DisplayTranslator
    )(**kwargs)
