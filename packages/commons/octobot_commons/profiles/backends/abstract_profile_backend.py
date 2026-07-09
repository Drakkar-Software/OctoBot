# pylint: disable=C0116,R0801
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

import abc
import typing

import octobot_commons.enums as enums
import octobot_commons.profiles.profile_types.profile as profile_module


class AbstractProfileBackend(abc.ABC):
    def __init__(
        self,
        profiles_path: str = None,
        profile_schema_path: str = None,
        sync_user_id: str = None,
    ) -> None:
        self._profiles_path = profiles_path
        self._profile_schema_path = profile_schema_path
        self._sync_user_id = sync_user_id

    def _is_sync_available(self) -> bool:
        return bool(self._sync_user_id and str(self._sync_user_id).strip())

    def _resolve_schema_path(self, schema_path: str = None) -> str:
        return schema_path if schema_path is not None else self._profile_schema_path

    @property
    @abc.abstractmethod
    def source(self) -> enums.ProfileSource:
        raise NotImplementedError

    @abc.abstractmethod
    def list_profiles(
        self,
        schema_path: str = None,
    ) -> dict[str, profile_module.Profile]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_profile(
        self,
        profile_id: str,
        schema_path: str = None,
    ) -> typing.Optional[profile_module.Profile]:
        raise NotImplementedError

    @abc.abstractmethod
    def save_profile(
        self,
        profile: profile_module.Profile,
        global_config: dict,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def delete_profile(
        self,
        profile_id: str,
        profile: typing.Optional[profile_module.Profile] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def list_profile_ids(
        self,
        ignore: str = None,
        schema_path: str = None,
    ) -> list[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def duplicate_profile(
        self,
        profile: profile_module.Profile,
        name: str = None,
        description: str = None,
        schema_path: str = None,
    ) -> profile_module.Profile:
        raise NotImplementedError
