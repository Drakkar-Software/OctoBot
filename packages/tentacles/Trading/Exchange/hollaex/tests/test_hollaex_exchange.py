#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import decimal
import mock

import octobot_trading.enums as trading_enums

from ..hollaex_exchange import hollaex as hollaex_exchange_class
from ..hollaex_exchange import hollaexConnector

TICKER_WISE_SYMBOL = "BTC@BTC/USDT@ETH"


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


class TestGetExchangeAvailabilities:
    def test_returns_empty_list(self):
        assert hollaex_exchange_class.get_exchange_availabilities() == []


class TestCalculateFeesNetworkQualified:
    def test_fee_currency_uses_qualified_quote(self):
        fee_details = {
            trading_enums.ExchangeConstantsMarketPropertyColumns.FEE_SIDE.value: (
                trading_enums.ExchangeFeeSides.QUOTE.value
            ),
            trading_enums.ExchangeConstantsMarketPropertyColumns.TAKER.value: 0.001,
            trading_enums.ExchangeConstantsMarketPropertyColumns.MAKER.value: 0.001,
        }
        with mock.patch.object(
            hollaexConnector, "_get_fetched_fees", return_value=fee_details,
        ):
            fees = hollaexConnector._calculate_fetched_fees(
                "hollaex",
                {},
                TICKER_WISE_SYMBOL,
                trading_enums.TraderOrderType.BUY_LIMIT,
                decimal.Decimal("1"),
                decimal.Decimal("10"),
                "taker",
            )
        assert fees[trading_enums.FeePropertyColumns.CURRENCY.value] == "USDT@ETH"

    def test_fee_currency_uses_qualified_base(self):
        fee_details = {
            trading_enums.ExchangeConstantsMarketPropertyColumns.FEE_SIDE.value: (
                trading_enums.ExchangeFeeSides.GET.value
            ),
            trading_enums.ExchangeConstantsMarketPropertyColumns.TAKER.value: 0.001,
            trading_enums.ExchangeConstantsMarketPropertyColumns.MAKER.value: 0.001,
        }
        with mock.patch.object(
            hollaexConnector, "_get_fetched_fees", return_value=fee_details,
        ):
            fees = hollaexConnector._calculate_fetched_fees(
                "hollaex",
                {},
                TICKER_WISE_SYMBOL,
                trading_enums.TraderOrderType.BUY_LIMIT,
                decimal.Decimal("1"),
                decimal.Decimal("10"),
                "taker",
            )
        assert fees[trading_enums.FeePropertyColumns.CURRENCY.value] == "BTC@BTC"
