#  Drakkar-Software OctoBot-Tentacles-Manager
#  Copyright (c) Drakkar-Software, All rights reserved.


class TestTentacleConfigurationProfileDispatch:
    def test_local_get_config_proxy_overrides_get_config(self):
        import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration
        import octobot_tentacles_manager.configuration.tentacles_setup_configuration as tentacles_setup_configuration

        called = {}
        setup_config = tentacles_setup_configuration.TentaclesSetupConfiguration()

        def custom_get(tentacles_setup_config, klass):
            called["klass"] = klass
            return {"custom": True}

        with tentacle_configuration.local_get_config_proxy(custom_get):
            result = tentacle_configuration.get_config(setup_config, "TestKlass")
        assert result == {"custom": True}
        assert called["klass"] == "TestKlass"

    def test_sync_backed_profile_reads_config_from_profile_data(self):
        import mock
        import octobot_commons.profiles.profile_data as profile_data_module
        import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration
        import octobot_tentacles_manager.configuration.tentacles_setup_configuration as tentacles_setup_configuration

        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "TestKlass"
        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(
                name="TestKlass", config={"from_profile_data": True}
            )
        ]
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        profile.get_profile_data.return_value = profile_data
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        result = tentacle_configuration.get_config(setup, tentacle_klass)
        assert result == {"from_profile_data": True}

    def test_filesystem_profile_falls_back_to_file_system(self):
        import mock
        import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration
        import octobot_tentacles_manager.configuration.tentacles_setup_configuration as tentacles_setup_configuration

        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = False
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        with mock.patch.object(
            tentacle_configuration,
            "_get_config_from_file_system",
            mock.Mock(return_value={"from_filesystem": True}),
        ) as get_from_filesystem_mock:
            result = tentacle_configuration.get_config(setup, "TestKlass")
        assert result == {"from_filesystem": True}
        get_from_filesystem_mock.assert_called_once_with(setup, "TestKlass")

    def test_sync_backed_update_config_does_not_write_to_filesystem(self):
        import mock
        import octobot_commons.profiles.profile_data as profile_data_module
        import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration
        import octobot_tentacles_manager.configuration.tentacles_setup_configuration as tentacles_setup_configuration

        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "TestKlass"
        profile_data = profile_data_module.ProfileData()
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        profile.get_profile_data.return_value = profile_data
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        with mock.patch.object(
            tentacle_configuration,
            "_update_config_from_file_system",
            mock.Mock(),
        ) as update_filesystem_mock:
            tentacle_configuration.update_config(
                setup, tentacle_klass, {"updated": True}
            )
        update_filesystem_mock.assert_not_called()
        assert profile_data.tentacles[0].name == "TestKlass"
        assert profile_data.tentacles[0].config == {"updated": True}

    def test_ephemeral_profile_reads_config_from_profile_data(self):
        import octobot_commons.profiles.profile_types.ephemeral_profile as ephemeral_profile_module
        import octobot_commons.profiles.profile_data as profile_data_module
        import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration
        import octobot_tentacles_manager.configuration.tentacles_setup_configuration as tentacles_setup_configuration

        tentacle_klass = type("TestKlass", (), {"get_name": staticmethod(lambda: "TestKlass")})()
        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(
                name="TestKlass", config={"from_ephemeral": True}
            )
        ]
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        result = tentacle_configuration.get_config(setup, tentacle_klass)
        assert result == {"from_ephemeral": True}

    def test_ephemeral_profile_update_config_does_not_write_to_filesystem(self):
        import mock
        import octobot_commons.profiles.profile_types.ephemeral_profile as ephemeral_profile_module
        import octobot_commons.profiles.profile_data as profile_data_module
        import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration
        import octobot_tentacles_manager.configuration.tentacles_setup_configuration as tentacles_setup_configuration

        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "TestKlass"
        profile_data = profile_data_module.ProfileData()
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        with mock.patch.object(
            tentacle_configuration,
            "_update_config_from_file_system",
            mock.Mock(),
        ) as update_filesystem_mock:
            tentacle_configuration.update_config(
                setup, tentacle_klass, {"updated": True}
            )
        update_filesystem_mock.assert_not_called()
        assert profile_data.tentacles[0].name == "TestKlass"
        assert profile_data.tentacles[0].config == {"updated": True}

    def test_profile_not_persisted_in_setup_config_dict(self):
        import mock
        import octobot_tentacles_manager.configuration.tentacles_setup_configuration as tentacles_setup_configuration

        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = mock.Mock()
        setup.tentacles_activation = {"t": {"c": True}}
        persisted = setup._to_dict()
        assert "profile" not in persisted
        assert setup.profile is not None


class TestSyncBackedProfileConfigFilesystemFallback:
    def test_sync_backed_empty_config_falls_back_to_filesystem(self):
        import mock
        import octobot_commons.profiles.profile_data as profile_data_module
        import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration
        import octobot_tentacles_manager.configuration.tentacles_setup_configuration as tentacles_setup_configuration

        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "TestKlass"
        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(name="TestKlass", config={}),
        ]
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        profile.get_profile_data.return_value = profile_data
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        factory_config = {"required_evaluators": ["*"]}
        with mock.patch.object(
            tentacle_configuration,
            "_get_config_from_file_system",
            mock.Mock(return_value=factory_config),
        ) as get_from_filesystem_mock:
            result = tentacle_configuration.get_config(setup, tentacle_klass)
        assert result == factory_config
        get_from_filesystem_mock.assert_called_once_with(setup, tentacle_klass)

    def test_sync_backed_missing_tentacle_falls_back_to_filesystem(self):
        import mock
        import octobot_commons.profiles.profile_data as profile_data_module
        import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration
        import octobot_tentacles_manager.configuration.tentacles_setup_configuration as tentacles_setup_configuration

        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "OtherKlass"
        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(
                name="TestKlass", config={"from_profile_data": True}
            ),
        ]
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        profile.get_profile_data.return_value = profile_data
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        factory_config = {"required_evaluators": ["TA"]}
        with mock.patch.object(
            tentacle_configuration,
            "_get_config_from_file_system",
            mock.Mock(return_value=factory_config),
        ) as get_from_filesystem_mock:
            result = tentacle_configuration.get_config(setup, tentacle_klass)
        assert result == factory_config
        get_from_filesystem_mock.assert_called_once_with(setup, tentacle_klass)
