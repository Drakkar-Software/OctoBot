# pylint: disable=C0116,C0415,W0212,W0603,W0718,R0913,W0613,C0412
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

import datetime
import os
import shutil
import typing
import uuid

import octobot_commons.constants as constants
import octobot_commons.errors as errors
import octobot_commons.enums as enums
import octobot_commons.logging as logging
import octobot_commons.profiles.backends.abstract_profile_backend as abstract_profile_backend_module
import octobot_commons.profiles.profile_types.profile as profile_module
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_types.sync_profile as sync_profile_module


_LOGGER = None


def _get_logger():
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = logging.get_logger("SyncProfileBackend")
    return _LOGGER


class SyncProfileBackend(abstract_profile_backend_module.AbstractProfileBackend):
    @property
    def source(self) -> enums.ProfileSource:
        return enums.ProfileSource.SYNC

    def list_profiles(
        self,
        schema_path: str = None,
    ) -> dict[str, profile_module.Profile]:
        if not self._is_sync_available():
            return {}
        resolved_schema_path = self._resolve_schema_path(schema_path)
        profiles = {}
        try:
            for strategy in self._list_profile_strategies():
                profile = self._strategy_to_profile(strategy, resolved_schema_path)
                if profile is not None:
                    profiles[profile.profile_id] = profile
        except Exception as err:
            _get_logger().exception(
                "Failed to list sync profiles for user %r: %s",
                self._sync_user_id,
                err,
            )
            return {}
        return profiles

    def get_profile(
        self,
        profile_id: str,
        schema_path: str = None,
    ) -> typing.Optional[profile_module.Profile]:
        if not self._is_sync_available():
            return None
        strategy = self._get_strategy(profile_id)
        if strategy is None:
            return None
        return self._strategy_to_profile(strategy, self._resolve_schema_path(schema_path))

    def save_profile(
        self,
        profile: profile_module.Profile,
        global_config: dict,
    ) -> None:
        if not self._is_sync_available():
            raise errors.ProfileDataError(
                "Sync profile save requires a configured wallet user id"
            )
        if not profile.is_sync_backed():
            raise errors.ProfileDataError(
                "SyncProfileBackend cannot save filesystem profiles"
            )
        profile_data = self._profile_to_profile_data(profile, global_config)
        self._validate_profile_data(profile_data)
        strategy = self._profile_data_to_strategy(profile_data, profile)
        strategy_provider = self._get_strategy_provider()
        import octobot_sync.sync.collection_backend.errors as collection_errors

        try:
            strategy_provider.update_item(self._sync_user_id, strategy)
        except collection_errors.ItemNotFoundError:
            strategy_provider.create_item(self._sync_user_id, strategy)
        sync_profile = typing.cast(sync_profile_module.SyncProfile, profile)
        sync_profile.set_profile_data(profile_data)

    def delete_profile(
        self,
        profile_id: str,
        profile: typing.Optional[profile_module.Profile] = None,
    ) -> None:
        if not self._is_sync_available():
            raise errors.ProfileDataError(
                "Sync profile delete requires a configured wallet user id"
            )
        self._get_strategy_provider().delete_item(self._sync_user_id, profile_id)
        runtime_path = self._runtime_profile_path(profile_id)
        if os.path.isdir(runtime_path):
            shutil.rmtree(runtime_path)

    def list_profile_ids(
        self,
        ignore: str = None,
        schema_path: str = None,
    ) -> list[str]:
        if not self._is_sync_available():
            return []
        return [strategy.id for strategy in self._list_profile_strategies()]

    def duplicate_profile(
        self,
        profile: profile_module.Profile,
        name: str = None,
        description: str = None,
        schema_path: str = None,
    ) -> sync_profile_module.SyncProfile:
        if not self._is_sync_available():
            raise errors.ProfileDataError(
                "Sync profile duplicate requires a configured wallet user id"
            )
        if profile.is_sync_backed():
            profile_data = self._profile_to_profile_data(
                profile, profile._global_config_from_profile()
            )
        else:
            profile_data = profile_data_module.ProfileData.from_filesystem_profile(profile)
        profile_data.profile_details.id = uuid.uuid4().hex
        duplicated_name = name or profile.name
        duplicated_description = description if description is not None else profile.description
        duplicate = self.import_profile_data(
            profile_data,
            schema_path=schema_path,
            name=duplicated_name,
            description=duplicated_description,
            risk=profile.risk,
            auto_update=False,
            slug=profile.slug,
        )
        duplicate.read_only = False
        duplicate.imported = False
        duplicate.origin_url = None
        duplicate.description = duplicated_description
        return duplicate

    def import_profile_data(
        self,
        profile_data: profile_data_module.ProfileData,
        schema_path: str = None,
        name: str = None,
        description: str = None,
        risk=None,
        auto_update: bool = False,
        slug: str = None,
        force_simulator: bool = False,
    ) -> sync_profile_module.SyncProfile:
        if not self._is_sync_available():
            raise errors.ProfileDataError(
                "Sync profile import requires a configured wallet user id"
            )
        resolved_schema_path = self._resolve_schema_path(schema_path)
        if profile_data.profile_details.id is None:
            profile_data.profile_details.id = uuid.uuid4().hex
        if name:
            profile_data.profile_details.name = name
        profile = self._profile_data_to_runtime_profile(
            profile_data, resolved_schema_path
        )
        if description is not None:
            profile.description = description
        if risk is not None:
            profile.risk = risk
        if slug is not None:
            profile.slug = slug
        profile.auto_update = auto_update
        if force_simulator:
            profile.config[constants.CONFIG_TRADER][
                constants.CONFIG_ENABLED_OPTION
            ] = False
            profile.config[constants.CONFIG_SIMULATOR][
                constants.CONFIG_ENABLED_OPTION
            ] = True
        self.save_profile(profile, profile._global_config_from_profile())
        return profile

    def _get_strategy_provider(self):
        import octobot_sync.sync.collection_providers as collection_providers

        return collection_providers.StrategyProvider.instance()

    def _list_profile_strategies(self):
        import octobot_sync.sync.collection_backend.errors as collection_errors

        try:
            strategies = self._get_strategy_provider().list_items(self._sync_user_id)
        except collection_errors.CollectionNoDataError:
            return []
        return [
            strategy
            for strategy in strategies
            if self._is_profile_strategy(strategy)
        ]

    def _get_strategy(self, profile_id: str):
        try:
            strategy = self._get_strategy_provider().get_item(
                self._sync_user_id, profile_id
            )
        except Exception:
            return None
        if not self._is_profile_strategy(strategy):
            return None
        return strategy

    def _is_profile_strategy(self, strategy) -> bool:
        configuration = strategy.configuration
        if configuration is None or configuration.actual_instance is None:
            return False
        import octobot_protocol.models.generic_process_configuration as generic_process_configuration

        return isinstance(
            configuration.actual_instance,
            generic_process_configuration.GenericProcessConfiguration,
        ) and configuration.actual_instance.profile_data is not None

    def _strategy_to_profile(
        self,
        strategy,
        schema_path: str,
    ) -> typing.Optional[sync_profile_module.SyncProfile]:
        configuration = strategy.configuration.actual_instance
        profile_data_dict = configuration.profile_data
        if profile_data_dict is None:
            return None
        profile_data = profile_data_module.ProfileData.from_dict(profile_data_dict)
        if profile_data.profile_details.id != strategy.id:
            profile_data.profile_details.id = strategy.id
        runtime_path = self._runtime_profile_path(strategy.id)
        profile = sync_profile_module.SyncProfile(
            profile_data,
            runtime_path,
            schema_path=schema_path,
            strategy_version=strategy.version,
        )
        if strategy.name:
            profile.name = strategy.name
        if strategy.description:
            profile.description = strategy.description
        return profile

    def _profile_data_to_runtime_profile(
        self,
        profile_data: profile_data_module.ProfileData,
        schema_path: str,
    ) -> sync_profile_module.SyncProfile:
        runtime_path = self._runtime_profile_path(
            profile_data.profile_details.id
        )
        return sync_profile_module.SyncProfile(
            profile_data, runtime_path, schema_path=schema_path
        )

    def _profile_data_to_strategy(
        self,
        profile_data: profile_data_module.ProfileData,
        profile: profile_module.Profile,
    ):
        import octobot_protocol.models as protocol_models
        import octobot_protocol.models.action_configuration_type as action_configuration_type
        import octobot_protocol.models.generic_process_configuration as generic_process_configuration
        import octobot_protocol.models.strategy_configuration as strategy_configuration

        strategy_version = "1"
        if isinstance(profile, sync_profile_module.SyncProfile):
            strategy_version = profile.get_strategy_version()
        generic_configuration = generic_process_configuration.GenericProcessConfiguration(
            configuration_type=action_configuration_type.ActionConfigurationType.GENERIC_PROCESS,
            profile_data=profile_data.to_dict(),
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        return protocol_models.Strategy(
            id=profile_data.profile_details.id,
            version=strategy_version,
            name=profile.name or profile_data.profile_details.name,
            description=profile.description,
            created_at=now,
            updated_at=now,
            reference_market=profile_data.trading.reference_market
            or constants.DEFAULT_REFERENCE_MARKET,
            configuration=strategy_configuration.StrategyConfiguration(
                actual_instance=generic_configuration
            ),
        )

    def _profile_to_profile_data(
        self,
        profile: profile_module.Profile,
        global_config: dict,
    ) -> profile_data_module.ProfileData:
        profile_data = profile_data_module.ProfileData.from_profile(profile)
        profile_data.profile_details.id = profile.profile_id
        profile_data.profile_details.name = profile.name
        tentacles_data = profile.get_tentacles_data()
        if tentacles_data is not None:
            profile_data.tentacles = tentacles_data
        elif profile.is_sync_backed():
            sync_profile = typing.cast(sync_profile_module.SyncProfile, profile)
            profile_data.tentacles = list(sync_profile.get_profile_data().tentacles)
        return profile_data

    def _validate_profile_data(
        self, profile_data: profile_data_module.ProfileData
    ) -> None:
        if not profile_data.profile_details.id:
            raise errors.ProfileDataError("profile_data.profile_details.id is required")
        if (
            profile_data.profile_details.name is None
            or profile_data.profile_details.name == ""
        ):
            raise errors.ProfileDataError("profile_data.profile_details.name is required")

    def _runtime_profile_path(self, profile_id: str) -> str:
        import octobot_commons.user_root_folder_provider as user_root_folder_provider

        user_root = user_root_folder_provider.get_sync_data_root()
        return os.path.join(
            user_root,
            constants.SYNC_PROFILE_RUNTIME_FOLDER,
            profile_id,
        )
