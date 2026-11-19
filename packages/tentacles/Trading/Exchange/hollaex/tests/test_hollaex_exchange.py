#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import decimal
import mock
import pytest

import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors

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


def _hollaex_exchange_with_rest(rest_url: str):
    exchange = object.__new__(hollaex_exchange_class)
    exchange.tentacle_config = {hollaex_exchange_class.REST_KEY: rest_url}
    return exchange


class TestNormalizeApiUrl:
    def test_strips_trailing_slash(self):
        assert hollaex_exchange_class._normalize_api_url("https://example.com/api/") == "https://example.com/api"


class TestIsUrlAllowed:
    def test_allows_any_url_when_whitelist_disabled(self):
        with mock.patch.object(hollaex_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=False):
            assert hollaex_exchange_class.is_url_allowed("https://custom.exchange/api/") is True

    def test_allows_stock_api_when_whitelist_enabled(self):
        with mock.patch.object(hollaex_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=True):
            assert hollaex_exchange_class.is_url_allowed(f"https://{hollaex_exchange_class.BASE_REST_API}") is True

    def test_allows_earn_curve_with_or_without_trailing_slash(self):
        with mock.patch.object(hollaex_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=True):
            assert hollaex_exchange_class.is_url_allowed("https://www.earncurve.com.au/api/") is True
            assert hollaex_exchange_class.is_url_allowed("https://www.earncurve.com.au/api") is True

    def test_rejects_unknown_url_when_whitelist_enabled(self):
        with mock.patch.object(hollaex_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=True):
            assert hollaex_exchange_class.is_url_allowed("https://www.cne.kg/api/") is False


class TestEnsureUrlAllowed:
    def test_no_op_when_whitelist_disabled(self):
        with mock.patch.object(hollaex_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=False):
            hollaex_exchange_class.ensure_url_allowed("https://custom.exchange/api/")

    def test_raises_not_supported_when_whitelist_enabled_and_url_unknown(self):
        with mock.patch.object(hollaex_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=True):
            with pytest.raises(trading_errors.ExchangeConfigurationError):
                hollaex_exchange_class.ensure_url_allowed("https://custom.exchange/api/")


class TestGetApiUrl:
    def test_returns_arbitrary_rest_when_whitelist_disabled(self):
        custom_rest_url = "https://custom.exchange/api/"
        exchange = _hollaex_exchange_with_rest(custom_rest_url)
        with mock.patch.object(hollaex_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=False):
            assert exchange.get_api_url() == custom_rest_url

    def test_returns_stock_rest_when_whitelist_enabled(self):
        stock_url = f"https://{hollaex_exchange_class.BASE_REST_API}"
        exchange = _hollaex_exchange_with_rest(stock_url)
        with mock.patch.object(hollaex_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=True):
            assert exchange.get_api_url() == stock_url

    def test_returns_earn_curve_rest_when_whitelist_enabled(self):
        earn_curve_url = "https://www.earncurve.com.au/api"
        exchange = _hollaex_exchange_with_rest(earn_curve_url)
        with mock.patch.object(hollaex_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=True):
            assert exchange.get_api_url() == earn_curve_url

    def test_raises_when_whitelist_enabled_and_rest_not_allowed(self):
        exchange = _hollaex_exchange_with_rest("https://www.cne.kg/api/")
        with mock.patch.object(hollaex_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=True):
            with pytest.raises(trading_errors.ExchangeConfigurationError):
                exchange.get_api_url()


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
