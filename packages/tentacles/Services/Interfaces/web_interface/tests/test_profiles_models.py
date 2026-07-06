#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import mock
import pytest

import octobot_commons.errors as commons_errors
import octobot_tentacles_manager.constants as tentacles_manager_constants
import tentacles.Services.Interfaces.web_interface.models.profiles as profiles_model


class TestResolveProfileTentaclesSetupConfig:
    def test_profile_data_backed_calls_init_tentacles_setup_config_when_uninitialized(self):
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        initialized_setup = mock.Mock()

        def init_side_effect():
            profile.tentacles_setup_config = initialized_setup

        profile.tentacles_setup_config = None
        profile.init_tentacles_setup_config.side_effect = init_side_effect

        def bind_side_effect(setup):
            setup.profile = profile
            return setup

        profile.bind_tentacles_setup_config.side_effect = bind_side_effect

        result = profiles_model._resolve_profile_tentacles_setup_config(profile)

        profile.init_tentacles_setup_config.assert_called_once_with()
        profile.bind_tentacles_setup_config.assert_called_once_with(initialized_setup)
        profile.get_tentacles_config_path.assert_not_called()
        assert result is initialized_setup
        assert result.profile is profile

    def test_profile_data_backed_reuses_existing_setup_config(self):
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        profile.tentacles_setup_config = mock.Mock()

        def bind_side_effect(setup):
            setup.profile = profile
            return setup

        profile.bind_tentacles_setup_config.side_effect = bind_side_effect

        result = profiles_model._resolve_profile_tentacles_setup_config(profile)

        profile.init_tentacles_setup_config.assert_not_called()
        profile.bind_tentacles_setup_config.assert_called_once_with(profile.tentacles_setup_config)
        assert result is profile.tentacles_setup_config
        assert result.profile is profile

    def test_filesystem_profile_uses_tentacles_config_path(self):
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = False
        profile.get_tentacles_config_path.return_value = "/profiles/test/tentacles_config.json"
        setup_config = mock.Mock()
        with mock.patch.object(
            profiles_model.tentacles_manager_api,
            "get_tentacles_setup_config",
            mock.Mock(return_value=setup_config),
        ) as get_setup_config_mock:
            result = profiles_model._resolve_profile_tentacles_setup_config(profile)
        get_setup_config_mock.assert_called_once_with(
            "/profiles/test/tentacles_config.json",
            profile=profile,
        )
        assert result is setup_config


class TestUpdateEditedTentaclesConfig:
    def test_profile_data_backed_uses_resolve_not_filesystem_path(self):
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        config = mock.Mock()
        config.profile = profile
        resolved_setup = mock.Mock()

        with mock.patch.object(
            profiles_model,
            "_resolve_profile_tentacles_setup_config",
            mock.Mock(return_value=resolved_setup),
        ) as resolve_mock, mock.patch.object(
            profiles_model.interfaces_util,
            "set_edited_tentacles_config",
            mock.Mock(),
        ) as set_edited_mock, mock.patch.object(
            profiles_model.tentacles_manager_api,
            "get_tentacles_setup_config",
            mock.Mock(),
        ) as get_setup_config_mock:
            profiles_model._update_edited_tentacles_config(config)

        resolve_mock.assert_called_once_with(profile, force_reload=False)
        set_edited_mock.assert_called_once_with(resolved_setup)
        config.get_tentacles_config_path.assert_not_called()
        get_setup_config_mock.assert_not_called()


class TestRefreshSyncProfilesForDisplay:
    def test_refreshes_sync_profiles_rebinds_setup_and_clears_cache(self):
        sync_profile = mock.Mock()
        sync_profile.profile_id = "sync-profile-id"
        sync_profile.is_sync_backed.return_value = True
        config = mock.Mock()
        config.profile = sync_profile
        resolved_setup = mock.Mock()

        with mock.patch.object(
            profiles_model.interfaces_util,
            "get_edited_config",
            mock.Mock(return_value=config),
        ), mock.patch.object(
            profiles_model,
            "_update_edited_tentacles_config",
            mock.Mock(),
        ) as update_edited_mock, mock.patch(
            "tentacles.Services.Interfaces.web_interface.models.configuration.clear_tentacle_config_cache",
            mock.Mock(),
        ) as clear_cache_mock, mock.patch.object(
            profiles_model,
            "_resolve_profile_tentacles_setup_config",
            mock.Mock(return_value=resolved_setup),
        ):
            result = profiles_model.refresh_sync_profiles_for_display()

        config.refresh_sync_profiles.assert_called_once_with()
        update_edited_mock.assert_called_once_with(config, force_reload=True)
        clear_cache_mock.assert_called_once_with()
        assert result is config
        assert "sync-profile-id" not in profiles_model._PROFILE_TENTACLES_CONFIG_CACHE

    def test_skips_profile_cache_pop_for_filesystem_profile(self):
        filesystem_profile = mock.Mock()
        filesystem_profile.profile_id = "filesystem-profile-id"
        filesystem_profile.is_sync_backed.return_value = False
        config = mock.Mock()
        config.profile = filesystem_profile
        profiles_model._PROFILE_TENTACLES_CONFIG_CACHE["filesystem-profile-id"] = mock.Mock()

        with mock.patch.object(
            profiles_model,
            "_update_edited_tentacles_config",
            mock.Mock(),
        ) as update_edited_mock, mock.patch(
            "tentacles.Services.Interfaces.web_interface.models.configuration.clear_tentacle_config_cache",
            mock.Mock(),
        ):
            profiles_model.refresh_sync_profiles_for_display(config)

        update_edited_mock.assert_called_once_with(config, force_reload=False)
        assert "filesystem-profile-id" in profiles_model._PROFILE_TENTACLES_CONFIG_CACHE


class TestGetProfiles:
    def test_calls_refresh_sync_profiles_before_filtering(self):
        live_profile = mock.Mock()
        live_profile.profile_type = profiles_model.commons_enums.ProfileType.LIVE
        simulator_profile = mock.Mock()
        simulator_profile.profile_type = profiles_model.commons_enums.ProfileType.BACKTESTING
        config = mock.Mock()
        config.profile_by_id = {
            "live-profile-id": live_profile,
            "simulator-profile-id": simulator_profile,
        }

        with mock.patch.object(
            profiles_model,
            "refresh_sync_profiles_for_display",
            mock.Mock(return_value=config),
        ) as refresh_mock:
            result = profiles_model.get_profiles(profiles_model.commons_enums.ProfileType.LIVE)

        refresh_mock.assert_called_once_with()
        assert result == {"live-profile-id": live_profile}


class TestEnsureProfileInConfig:
    def test_returns_cached_profile_without_reload(self):
        cached_profile = mock.Mock()
        config = mock.Mock()
        config.profile_by_id = {"cached-profile-id": cached_profile}

        result = profiles_model._ensure_profile_in_config(config, "cached-profile-id")

        assert result is cached_profile
        config.load_profiles.assert_not_called()
        config.profile_storage.load_profile_by_id.assert_not_called()

    def test_loads_from_profile_storage_when_missing_from_cache(self):
        config = mock.Mock()
        config.profile_by_id = {}
        loaded_profile = mock.Mock()
        config.profile_storage.load_profile_by_id.return_value = loaded_profile

        result = profiles_model._ensure_profile_in_config(config, "storage-profile-id")

        config.load_profiles.assert_called_once_with()
        config.profile_storage.load_profile_by_id.assert_called_once_with("storage-profile-id")
        assert config.profile_by_id["storage-profile-id"] is loaded_profile
        assert result is loaded_profile

    def test_raises_no_profile_error_when_unknown(self):
        config = mock.Mock()
        config.profile_by_id = {}
        config.profile_storage.load_profile_by_id.side_effect = commons_errors.NoProfileError(
            "No profile with id: missing-profile-id"
        )

        with pytest.raises(commons_errors.NoProfileError):
            profiles_model._ensure_profile_in_config(config, "missing-profile-id")


class TestSelectProfile:
    def test_select_profile_updates_edited_tentacles_for_sync_profile(self):
        sync_profile = mock.Mock()
        sync_profile.is_profile_data_tentacle_backed.return_value = True
        sync_profile.tentacles_setup_config = mock.Mock()
        config = mock.Mock()
        config.profile = mock.Mock()
        config.profile_by_id = {"sync-profile-id": sync_profile}

        def select_side_effect(profile_id):
            config.profile = sync_profile

        config.select_profile.side_effect = select_side_effect
        resolved_setup = mock.Mock()

        with mock.patch.object(
            profiles_model.interfaces_util,
            "get_edited_config",
            mock.Mock(return_value=config),
        ), mock.patch.object(
            profiles_model,
            "_resolve_profile_tentacles_setup_config",
            mock.Mock(return_value=resolved_setup),
        ) as resolve_mock, mock.patch.object(
            profiles_model.interfaces_util,
            "set_edited_tentacles_config",
            mock.Mock(),
        ) as set_edited_mock:
            profiles_model.select_profile("sync-profile-id")

        config.select_profile.assert_called_once_with("sync-profile-id")
        resolve_mock.assert_called_once_with(sync_profile, force_reload=False)
        set_edited_mock.assert_called_once_with(resolved_setup)
        config.save.assert_called_once_with()
        config.get_tentacles_config_path.assert_not_called()

    def test_select_profile_raises_no_profile_error_for_stale_id(self):
        config = mock.Mock()
        config.profile_by_id = {}
        config.profile_storage.load_profile_by_id.side_effect = commons_errors.NoProfileError(
            "No profile with id: stale-profile-id"
        )

        with mock.patch.object(
            profiles_model.interfaces_util,
            "get_edited_config",
            mock.Mock(return_value=config),
        ), pytest.raises(commons_errors.NoProfileError):
            profiles_model.select_profile("stale-profile-id")

        config.select_profile.assert_not_called()
        config.save.assert_not_called()


class TestGetProfilesTentaclesDetails:
    @pytest.fixture(autouse=True)
    def _clear_setup_config_cache(self):
        profiles_model._PROFILE_TENTACLES_CONFIG_CACHE.clear()
        yield
        profiles_model._PROFILE_TENTACLES_CONFIG_CACHE.clear()

    def test_returns_details_for_filesystem_and_profile_data_backed_profiles(self):
        filesystem_profile = mock.Mock()
        filesystem_profile.profile_id = "filesystem-profile-id"
        filesystem_profile.is_profile_data_tentacle_backed.return_value = False
        filesystem_profile.imported = False
        filesystem_profile.get_tentacles_config_path.return_value = "/profiles/fs/tentacles_config.json"

        sync_profile = mock.Mock()
        sync_profile.profile_id = "sync-profile-id"
        sync_profile.is_profile_data_tentacle_backed.return_value = True
        sync_profile.imported = False
        sync_profile.tentacles_setup_config = None
        initialized_sync_setup = mock.Mock()

        def init_sync_setup():
            sync_profile.tentacles_setup_config = initialized_sync_setup

        sync_profile.init_tentacles_setup_config.side_effect = init_sync_setup

        current_profile = mock.Mock()
        current_profile.profile_id = "filesystem-profile-id"

        filesystem_setup = mock.Mock()
        with mock.patch.object(profiles_model, "get_current_profile", mock.Mock(return_value=current_profile)), mock.patch.object(
            profiles_model.tentacles_manager_api,
            "get_tentacles_setup_config",
            mock.Mock(return_value=filesystem_setup),
        ), mock.patch.object(
            profiles_model.tentacles_manager_api,
            "get_activated_tentacles",
            mock.Mock(side_effect=[["ModeA"], ["ModeB"]]),
        ), mock.patch.object(
            profiles_model.tentacles_manager_api,
            "get_tentacles_installation_version",
            mock.Mock(side_effect=["2.1.1", "2.1.1"]),
        ), mock.patch.object(
            profiles_model.tentacles_manager_api,
            "is_tentacles_setup_config_successfully_loaded",
            mock.Mock(return_value=True),
        ):
            details = profiles_model.get_profiles_tentacles_details(
                {
                    filesystem_profile.profile_id: filesystem_profile,
                    sync_profile.profile_id: sync_profile,
                }
            )

        assert set(details) == {"filesystem-profile-id", "sync-profile-id"}
        assert details["filesystem-profile-id"][profiles_model.ACTIVATION] == ["ModeA"]
        assert details["sync-profile-id"][profiles_model.ACTIVATION] == ["ModeB"]
        sync_profile.init_tentacles_setup_config.assert_called()

    def test_failed_profile_gets_fallback_entry(self):
        broken_profile = mock.Mock()
        broken_profile.profile_id = "broken-profile-id"
        broken_profile.imported = True

        current_profile = mock.Mock()
        current_profile.profile_id = "other-profile-id"

        with mock.patch.object(profiles_model, "get_current_profile", mock.Mock(return_value=current_profile)), mock.patch.object(
            profiles_model,
            "_get_profile_setup_config",
            mock.Mock(side_effect=RuntimeError("load failed")),
        ):
            details = profiles_model.get_profiles_tentacles_details(
                {broken_profile.profile_id: broken_profile}
            )

        assert broken_profile.profile_id in details
        assert details[broken_profile.profile_id][profiles_model.READ_ERROR] is True
        assert details[broken_profile.profile_id][profiles_model.ACTIVATION] == []
        assert details[broken_profile.profile_id][profiles_model.VERSION] == (
            tentacles_manager_constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION_UNKNOWN
        )


class TestDuplicateProfile:
    def test_sync_duplicate_skips_filesystem_refresh_and_inits_tentacles_setup(self):
        source_profile = mock.Mock()
        source_profile.name = "Source"
        source_profile.description = "desc"
        duplicated_profile = mock.Mock()
        duplicated_profile.profile_id = "new-sync-profile-id"
        duplicated_profile.is_profile_data_tentacle_backed.return_value = True
        source_profile.duplicate.return_value = duplicated_profile

        config = mock.Mock()
        reloaded_profile = mock.Mock()
        reloaded_profile.profile_id = "new-sync-profile-id"
        reloaded_profile.is_profile_data_tentacle_backed.return_value = True

        with mock.patch.object(profiles_model, "get_profile", mock.Mock(side_effect=[source_profile, reloaded_profile])), mock.patch.object(
            profiles_model.interfaces_util,
            "get_edited_config",
            mock.Mock(return_value=config),
        ), mock.patch.object(
            profiles_model.tentacles_manager_api,
            "refresh_profile_tentacles_setup_config",
            mock.Mock(),
        ) as refresh_mock:
            result = profiles_model.duplicate_profile("source-profile-id")

        source_profile.duplicate.assert_called_once_with(name="Source_(copy)", description="desc")
        refresh_mock.assert_not_called()
        config.load_profiles.assert_called_once_with()
        reloaded_profile.init_tentacles_setup_config.assert_called_once_with()
        assert result is reloaded_profile

    def test_filesystem_duplicate_refreshes_tentacles_on_disk(self):
        source_profile = mock.Mock()
        source_profile.name = "Source"
        source_profile.description = "desc"
        duplicated_profile = mock.Mock()
        duplicated_profile.profile_id = "new-filesystem-profile-id"
        duplicated_profile.path = "/profiles/new"
        duplicated_profile.is_profile_data_tentacle_backed.return_value = False
        source_profile.duplicate.return_value = duplicated_profile

        config = mock.Mock()
        reloaded_profile = mock.Mock()
        reloaded_profile.profile_id = "new-filesystem-profile-id"
        reloaded_profile.is_profile_data_tentacle_backed.return_value = False

        with mock.patch.object(profiles_model, "get_profile", mock.Mock(side_effect=[source_profile, reloaded_profile])), mock.patch.object(
            profiles_model.interfaces_util,
            "get_edited_config",
            mock.Mock(return_value=config),
        ), mock.patch.object(
            profiles_model.tentacles_manager_api,
            "refresh_profile_tentacles_setup_config",
            mock.Mock(),
        ) as refresh_mock:
            result = profiles_model.duplicate_profile("source-profile-id")

        refresh_mock.assert_called_once_with("/profiles/new")
        reloaded_profile.init_tentacles_setup_config.assert_not_called()
        assert result is reloaded_profile


class TestUpdateProfile:
    def test_rename_updates_name_without_rename_folder(self):
        profile = mock.Mock()
        profile.profile_id = "profile-id"
        profile.name = "old-name"
        profile.description = "desc"
        profile.avatar = "avatar.png"
        profile.complexity = profiles_model.commons_enums.ProfileComplexity.MEDIUM
        profile.risk = profiles_model.commons_enums.ProfileRisk.MODERATE
        profile.is_sync_backed.return_value = False

        current_profile = mock.Mock()
        current_profile.profile_id = "other-profile-id"

        with mock.patch.object(profiles_model, "get_profile", mock.Mock(return_value=profile)), mock.patch.object(
            profiles_model,
            "get_current_profile",
            mock.Mock(return_value=current_profile),
        ):
            success, message = profiles_model.update_profile(
                "profile-id",
                {"name": "new-name"},
            )

        assert success is True
        assert message == "Profile updated"
        assert profile.name == "new-name"
        profile.validate_and_save_config.assert_called_once_with()
