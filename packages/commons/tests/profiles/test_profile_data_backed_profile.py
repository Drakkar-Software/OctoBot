#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import mock

import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_types.profile_data_backed_profile as profile_data_backed_profile_module


class TestProfileDataBackedProfileGetTentaclesData:
    def test_merges_inactive_tentacle_configs_on_save(self):
        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(
                name="GridTradingMode",
                config={"flat_spread": 2},
                activated=False,
            ),
        ]
        profile = profile_data_backed_profile_module.ProfileDataBackedProfile(
            profile_data, profile_path="/tmp/profile"
        )
        tentacles_setup_config = mock.Mock()
        profile.tentacles_setup_config = tentacles_setup_config
        collected = [
            profile_data_module.TentaclesData(
                name="IndexTradingMode",
                config={"refresh_interval": 0},
                activated=True,
            ),
        ]

        with mock.patch(
            "octobot_tentacles_manager.configuration.profile_tentacles_util.collect_tentacles_data_from_setup",
            mock.Mock(return_value=collected),
        ), mock.patch(
            "octobot_tentacles_manager.configuration.profile_tentacles_util.merge_inactive_tentacles_data_from_profile",
            mock.Mock(
                return_value=[
                    collected[0],
                    profile_data.tentacles[0],
                ]
            ),
        ) as merge_mock:
            result = profile.get_tentacles_data()

        merge_mock.assert_called_once_with(collected, profile_data)
        assert len(result) == 2
        assert result[1].name == "GridTradingMode"
        assert result[1].activated is False
