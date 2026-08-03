#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_commons.profiles.profile_data as profile_data_module
import octobot_trading.exchanges.util.exchange_data as exchange_data_module

import octobot_flow.entities.accounts.exchange_account_details as exchange_account_details_module
import octobot_flow.logic.configuration.profile_data_factory as profile_data_factory_module


class TestCreateProfileDataHollaexUrl:
    def test_builds_hollaex_tentacle_config_from_exchange_url(self):
        earn_curve_api_url = "https://www.earncurve.com.au/api"
        exchange_account_details = exchange_account_details_module.ExchangeAccountDetails(
            exchange_details=profile_data_module.ExchangeData(
                internal_name="hollaex",
                url=earn_curve_api_url,
            ),
            auth_details=exchange_data_module.ExchangeAuthDetails(),
        )
        profile_data = profile_data_factory_module.create_profile_data(
            exchange_account_details,
            automation_id="automation-hollaex-earncurve",
            symbols={"BTC/USDC"},
            as_simulator=True,
        )
        tentacle_config_by_name = profile_data.get_config_by_tentacle()
        assert "hollaex" in tentacle_config_by_name
        assert tentacle_config_by_name["hollaex"]["rest"] == earn_curve_api_url
        assert tentacle_config_by_name["hollaex"]["has_websockets"] is False

    def test_omits_hollaex_tentacle_when_url_missing(self):
        exchange_account_details = exchange_account_details_module.ExchangeAccountDetails(
            exchange_details=profile_data_module.ExchangeData(
                internal_name="hollaex",
            ),
            auth_details=exchange_data_module.ExchangeAuthDetails(),
        )
        profile_data = profile_data_factory_module.create_profile_data(
            exchange_account_details,
            automation_id="automation-hollaex-no-url",
            symbols={"BTC/USDC"},
            as_simulator=True,
        )
        assert profile_data.get_config_by_tentacle() == {}
