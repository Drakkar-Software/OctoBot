# pylint: disable=C0103,W0603
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
import octobot_commons.constants as constants


class OptimizationCampaign:
    def __init__(self, name=None):
        self.name = name or self.get_campaign_name()

    @classmethod
    def get_campaign_name(cls, *args):
        """
        Returns the name of the current optimization campaign
        :param args: arguments passed to the optimization_campaign_name_proxy
        """
        return _optimization_name_proxy(*args)


def _default_optimization_name_proxy(*_):
    return constants.DEFAULT_CAMPAIGN


_name_proxy = _default_optimization_name_proxy


def _optimization_name_proxy(*args):
    return _name_proxy(*args)


def register_optimization_campaign_name_proxy(new_proxy):
    """
    Registers a new campaign name provider as a proxy function
    :param new_proxy: the proxy function to be called by OptimizationCampaign.get_campaign_name
    """
    global _name_proxy
    _name_proxy = new_proxy
