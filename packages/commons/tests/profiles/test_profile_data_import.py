#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_commons.constants as constants
import octobot_commons.enums as enums
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_data_import as profile_data_import_module


class TestGetProfile:
    def test_none_risk_defaults_to_moderate(self):
        profile_data = profile_data_module.ProfileData.from_dict(
            {
                "profile_details": {"name": "fetched_config", "id": "profile-id"},
                "trading": {"reference_market": constants.DEFAULT_REFERENCE_MARKET},
            }
        )
        profile = profile_data_import_module._get_profile(
            profile_data,
            description=None,
            risk=None,
            output_path="/tmp/fetched_config",
            auto_update=False,
            slug="fetched_config",
            force_simulator=False,
        )
        assert profile.risk == enums.ProfileRisk.MODERATE
