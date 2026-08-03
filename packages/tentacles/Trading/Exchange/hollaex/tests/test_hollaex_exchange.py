#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

from ..hollaex_exchange import hollaex as hollaex_exchange_class


class TestGetTentaclesDataExchangeConfig:
    def test_builds_direct_hollaex_rest_config_for_hollaex_internal_name(self):
        earn_curve_api_url = "https://www.earncurve.com.au/api"
        tentacles_data = hollaex_exchange_class.get_tentacles_data_exchange_config(
            "hollaex",
            earn_curve_api_url,
        )
        assert tentacles_data.name == "hollaex"
        assert tentacles_data.config["rest"] == earn_curve_api_url
        assert tentacles_data.config["has_websockets"] is False

    def test_builds_hollaex_autofilled_tentacles_data_for_custom_internal_name(self):
        cne_api_url = "https://www.cne.kg/api/"
        tentacles_data = hollaex_exchange_class.get_tentacles_data_exchange_config(
            "cne",
            cne_api_url,
        )
        assert tentacles_data.name == "HollaexAutofilled"
        assert tentacles_data.config["auto_filled"]["cne"]["url"] == cne_api_url

    def test_passes_through_custom_config_override(self):
        custom_config = {"auto_filled": {"cne": {"url": "https://www.cne.kg/api/"}}}
        tentacles_data = hollaex_exchange_class.get_tentacles_data_exchange_config(
            "cne",
            "https://www.cne.kg/api/",
            custom_config,
        )
        assert tentacles_data.name == "HollaexAutofilled"
        assert tentacles_data.config == custom_config
