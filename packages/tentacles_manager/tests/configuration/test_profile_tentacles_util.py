#  Drakkar-Software OctoBot-Tentacles-Manager
#  Copyright (c) Drakkar-Software, All rights reserved.

import json
import os

import mock

import octobot_commons.constants as commons_constants
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_tentacles_manager.constants as tentacles_manager_constants


class TestBuildSetupConfigFromProfileData:
    def test_builds_setup_config_from_profile_data_tentacles(self):
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(name="MyEvaluator", config={}),
        ]
        tentacle_class = mock.Mock()
        tentacle_class.__name__ = "MyEvaluator"
        setup_config = mock.Mock()
        setup_config.registered_tentacles = {"pkg": "url"}

        with mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "get_tentacle_class_from_string",
            mock.Mock(return_value=tentacle_class),
        ), mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "create_tentacles_setup_config_with_tentacles",
            mock.Mock(return_value=setup_config),
        ) as create_setup_mock, mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "fill_with_installed_tentacles",
        ) as fill_mock:
            result = profile_tentacles_util.build_setup_config_from_profile_data(
                profile_data, "/output", import_registered_tentacles=True
            )

        assert result is setup_config
        create_setup_mock.assert_called_once_with(
            "MyEvaluator",
            config_path=os.path.join("/output", commons_constants.CONFIG_TENTACLES_FILE),
        )
        fill_mock.assert_called_once_with(
            setup_config,
            import_registered_tentacles=True,
            use_reference_registered_tentacles=False,
        )

    def test_builds_setup_config_without_output_path(self):
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(name="MyEvaluator", config={}),
        ]
        tentacle_class = mock.Mock()
        tentacle_class.__name__ = "MyEvaluator"
        setup_config = mock.Mock()
        setup_config.registered_tentacles = {"pkg": "url"}

        with mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "get_tentacle_class_from_string",
            mock.Mock(return_value=tentacle_class),
        ), mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "create_tentacles_setup_config_with_tentacles",
            mock.Mock(return_value=setup_config),
        ) as create_setup_mock, mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "fill_with_installed_tentacles",
        ):
            result = profile_tentacles_util.build_setup_config_from_profile_data(
                profile_data, import_registered_tentacles=False
            )

        assert result is setup_config
        create_setup_mock.assert_called_once_with("MyEvaluator", config_path=None)

    def test_skips_missing_tentacle_names(self):
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(name="MyEvaluator", config={}),
            profile_data_module.TentaclesData(name="upbit", config={}),
        ]
        my_evaluator_class = mock.Mock()
        my_evaluator_class.__name__ = "MyEvaluator"
        setup_config = mock.Mock()
        setup_config.registered_tentacles = {"pkg": "url"}

        def get_tentacle_class_side_effect(tentacle_name):
            if tentacle_name == "MyEvaluator":
                return my_evaluator_class
            raise RuntimeError(f"Can't find tentacle: {tentacle_name}")

        with mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "get_tentacle_class_from_string",
            mock.Mock(side_effect=get_tentacle_class_side_effect),
        ), mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "create_tentacles_setup_config_with_tentacles",
            mock.Mock(return_value=setup_config),
        ) as create_setup_mock, mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "fill_with_installed_tentacles",
        ):
            result = profile_tentacles_util.build_setup_config_from_profile_data(
                profile_data, import_registered_tentacles=False
            )

        assert result is setup_config
        create_setup_mock.assert_called_once_with("MyEvaluator", config_path=None)

    def test_all_missing_still_returns_setup_config(self):
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(name="upbit", config={}),
        ]
        setup_config = mock.Mock()
        setup_config.registered_tentacles = {"pkg": "url"}

        with mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "get_tentacle_class_from_string",
            mock.Mock(side_effect=RuntimeError("Can't find tentacle: upbit")),
        ), mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "create_tentacles_setup_config_with_tentacles",
            mock.Mock(return_value=setup_config),
        ) as create_setup_mock, mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "fill_with_installed_tentacles",
        ) as fill_mock:
            result = profile_tentacles_util.build_setup_config_from_profile_data(
                profile_data, import_registered_tentacles=False
            )

        assert result is setup_config
        create_setup_mock.assert_called_once_with(config_path=None)
        fill_mock.assert_called_once_with(
            setup_config,
            import_registered_tentacles=False,
            use_reference_registered_tentacles=False,
        )


class TestWriteSpecificConfigsToProfileFolder:
    def test_skips_unchanged_configs_when_updating(self, tmp_path):
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(name="MyEvaluator", config={"a": 1}),
        ]
        specific_config_dir = os.path.join(
            tmp_path, tentacles_manager_constants.TENTACLES_SPECIFIC_CONFIG_FOLDER
        )
        os.makedirs(specific_config_dir)
        file_path = os.path.join(
            specific_config_dir,
            f"MyEvaluator{tentacles_manager_constants.CONFIG_EXT}",
        )
        with open(file_path, "w", encoding="utf-8") as config_file:
            json.dump({"a": 1}, config_file)

        changed = profile_tentacles_util.write_specific_configs_to_profile_folder(
            profile_data, str(tmp_path), is_config_update=True
        )

        assert changed is False

    def test_writes_new_specific_configs(self, tmp_path):
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(name="MyEvaluator", config={"enabled": True}),
        ]

        changed = profile_tentacles_util.write_specific_configs_to_profile_folder(
            profile_data, str(tmp_path), is_config_update=False
        )

        assert changed is True
        file_path = os.path.join(
            tmp_path,
            tentacles_manager_constants.TENTACLES_SPECIFIC_CONFIG_FOLDER,
            f"MyEvaluator{tentacles_manager_constants.CONFIG_EXT}",
        )
        assert os.path.isfile(file_path)
        with open(file_path, encoding="utf-8") as config_file:
            assert json.load(config_file) == {"enabled": True}


class TestLoadSetupConfigFromProfilePath:
    def test_delegates_to_api(self):
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        setup_config = mock.Mock()
        with mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "get_tentacles_setup_config",
            mock.Mock(return_value=setup_config),
        ) as get_setup_mock:
            result = profile_tentacles_util.load_setup_config_from_profile_path(
                "/profiles/default/tentacles_config.json"
            )

        assert result is setup_config
        get_setup_mock.assert_called_once_with(
            "/profiles/default/tentacles_config.json"
        )


class TestReadSpecificConfigsByTentacleName:
    def test_reads_specific_config_json_files(self, tmp_path):
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        specific_config_dir = os.path.join(
            tmp_path, tentacles_manager_constants.TENTACLES_SPECIFIC_CONFIG_FOLDER
        )
        os.makedirs(specific_config_dir)
        file_path = os.path.join(
            specific_config_dir,
            f"MyEvaluator{tentacles_manager_constants.CONFIG_EXT}",
        )
        with open(file_path, "w", encoding="utf-8") as config_file:
            json.dump({"key": "value"}, config_file)

        configs = profile_tentacles_util.read_specific_configs_by_tentacle_name(
            str(tmp_path)
        )

        assert configs == {"MyEvaluator": {"key": "value"}}


class TestCollectTentaclesDataFromSetup:
    def test_uses_preloaded_specific_config_before_get_config(self):
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        tentacles_setup_config = mock.Mock()
        tentacles_setup_config.tentacles_activation = {
            "evaluators": {"MyEvaluator": True},
        }
        tentacle_class = mock.Mock()
        tentacle_class.get_name.return_value = "MyEvaluator"

        with mock.patch.object(
            profile_tentacles_util.tentacles_manager_api,
            "get_tentacle_class_from_string",
            mock.Mock(return_value=tentacle_class),
        ), mock.patch.object(
            profile_tentacles_util.tentacle_configuration,
            "get_config",
            mock.Mock(side_effect=AssertionError("get_config should not be called")),
        ):
            tentacles_data = profile_tentacles_util.collect_tentacles_data_from_setup(
                tentacles_setup_config,
                specific_configs_by_tentacle_name={"MyEvaluator": {"from_file": True}},
            )

        assert len(tentacles_data) == 1
        assert tentacles_data[0].name == "MyEvaluator"
        assert tentacles_data[0].config == {"from_file": True}


class TestCollectTentaclesDataFromFilesystemProfile:
    def test_returns_none_when_tentacles_config_file_missing(self, tmp_path):
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util
        import octobot_commons.profiles.profile_types.profile as profile_module

        profile = profile_module.Profile(str(tmp_path))

        result = profile_tentacles_util.collect_tentacles_data_from_filesystem_profile(
            profile
        )

        assert result is None
