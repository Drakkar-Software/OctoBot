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
import dataclasses
import hashlib
import os

import octobot_commons.configuration as configuration

import octobot.constants as constants


@dataclasses.dataclass(frozen=True)
class PathBoundValueResolution:
    value: str
    bound_path: str
    was_regenerated: bool


def get_bound_config_path(config_path: str) -> str:
    return os.path.normpath(os.path.abspath(config_path))


def path_binding_is_stale(stored_bound_path: str | None, config_path: str) -> bool:
    if not stored_bound_path:
        return True
    return stored_bound_path != get_bound_config_path(config_path)


def fingerprint_config_path(config_path: str) -> str:
    bound_path = get_bound_config_path(config_path)
    return hashlib.sha256(bound_path.encode()).hexdigest()


def _get_community_section(config: configuration.Configuration) -> dict:
    community_section = config.config.setdefault(constants.CONFIG_COMMUNITY, {})
    if not isinstance(community_section, dict):
        raise ValueError(f"{constants.CONFIG_COMMUNITY} must be a mapping in config")
    return community_section


def ensure_config_path_fingerprint(
    config: configuration.Configuration,
    *,
    persist: bool = True,
) -> PathBoundValueResolution:
    bound_path = get_bound_config_path(config.config_path)
    current_fingerprint = fingerprint_config_path(config.config_path)
    community_section = _get_community_section(config)
    stored_fingerprint = community_section.get(constants.CONFIG_COMMUNITY_LOCAL_DATA_IDENTIFIER)
    if stored_fingerprint == current_fingerprint:
        return PathBoundValueResolution(
            value=current_fingerprint,
            bound_path=bound_path,
            was_regenerated=False,
        )
    community_section[constants.CONFIG_COMMUNITY_LOCAL_DATA_IDENTIFIER] = current_fingerprint
    if persist:
        config.save()
    return PathBoundValueResolution(
        value=current_fingerprint,
        bound_path=bound_path,
        was_regenerated=True,
    )
