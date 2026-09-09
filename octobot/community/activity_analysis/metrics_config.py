#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import typing

import octobot_commons.configuration as configuration

import octobot.community.authentication as community_authentication


def get_metrics_config() -> typing.Optional[configuration.Configuration]:
    auth = community_authentication.CommunityAuthentication.instance()
    if auth is None:
        return None
    return auth.config


def metrics_enabled(config: typing.Optional[configuration.Configuration]) -> bool:
    return config is not None and config.get_metrics_enabled()


def resolve_enabled_config(
    config: typing.Optional[configuration.Configuration] = None,
) -> typing.Optional[configuration.Configuration]:
    resolved_config = config if config is not None else get_metrics_config()
    if resolved_config is None or not metrics_enabled(resolved_config):
        return None
    return resolved_config
