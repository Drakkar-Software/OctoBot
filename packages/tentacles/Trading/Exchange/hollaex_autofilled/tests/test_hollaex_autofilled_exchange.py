#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import mock
import pytest

import octobot_protocol.models as protocol_models
import octobot_trading.errors as trading_errors

from ...hollaex.hollaex_exchange import hollaex as hollaex_exchange_class
from ..hollaex_autofilled_exchange import HollaexAutofilled as hollaex_autofilled_exchange_class
from ..hollaex_exchanges import CustomExchangeAvailability
from ..hollaex_exchanges import _CUSTOM_EXCHANGE_AVAILABILITIES


def _autofilled_tentacle_config(exchange_name: str, kit_url: str) -> dict:
    return {
        hollaex_autofilled_exchange_class.AUTO_FILLED_KEY: {
            exchange_name: {hollaex_autofilled_exchange_class.URL_KEY: kit_url},
        },
    }


def _autofilled_exchange_with_rest(rest_url: str):
    exchange = object.__new__(hollaex_autofilled_exchange_class)
    exchange.tentacle_config = {hollaex_autofilled_exchange_class.REST_KEY: rest_url}
    return exchange


class TestGetKitUrl:
    def test_allows_arbitrary_kit_url_when_whitelist_disabled(self):
        kit_url = "https://www.cne.kg/api/"
        tentacle_config = _autofilled_tentacle_config("cne", kit_url)
        with mock.patch.object(hollaex_autofilled_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=False):
            assert hollaex_autofilled_exchange_class._get_kit_url(tentacle_config, "cne") == (
                "https://www.cne.kg/api/v2/kit"
            )

    def test_allows_earn_curve_kit_url_when_whitelist_enabled(self):
        kit_url = "https://www.earncurve.com.au/api/"
        tentacle_config = _autofilled_tentacle_config("earncurve", kit_url)
        with mock.patch.object(hollaex_autofilled_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=True):
            assert hollaex_autofilled_exchange_class._get_kit_url(tentacle_config, "earncurve") == (
                "https://www.earncurve.com.au/api/v2/kit"
            )

    def test_raises_before_building_kit_path_when_kit_url_not_allowed(self):
        tentacle_config = _autofilled_tentacle_config("cne", "https://www.cne.kg/api/")
        with mock.patch.object(hollaex_autofilled_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=True):
            with pytest.raises(trading_errors.ExchangeConfigurationError):
                hollaex_autofilled_exchange_class._get_kit_url(tentacle_config, "cne")


class TestHollaexAutofilledGetApiUrl:
    def test_returns_resolved_rest_without_whitelist_check(self):
        resolved_rest_url = "https://api.cne.kg"
        exchange = _autofilled_exchange_with_rest(resolved_rest_url)
        with mock.patch.object(hollaex_autofilled_exchange_class, "IS_URL_WHITE_LIST_ENABLED", new=True):
            assert exchange.get_api_url() == resolved_rest_url


class TestCustomExchangeAvailabilityToExchangeAvailability:
    def test_maps_dataclass_fields_to_protocol_model(self):
        custom_availability = CustomExchangeAvailability(
            internal_name="custom",
            name="Custom",
            api_url="https://example.com/api/",
            logo="https://example.com/logo.png",
            register_url="https://example.com/register",
            sandboxable=True,
            broker_enabled=True,
        )
        availability = custom_availability.to_exchange_availability()
        assert availability.internal_name == "custom"
        assert availability.name == "Custom"
        assert availability.api_url == "https://example.com/api/"
        assert availability.logo == "https://example.com/logo.png"
        assert availability.register_url == "https://example.com/register"
        assert availability.available_trading_types == [protocol_models.TradingType.SPOT]
        assert availability.support_type == protocol_models.ExchangeSupportStatus.OFFICIALLY_SUPPORTED
        assert availability.sandboxable is True
        assert availability.broker_enabled is True

    def test_defaults_internal_name_to_hollaex_get_name(self):
        custom_availability = CustomExchangeAvailability(
            name="Custom",
            api_url="https://example.com/api/",
        )
        assert custom_availability.internal_name == hollaex_exchange_class.get_name()


class TestGetExchangeAvailabilities:
    def test_returns_one_entry_per_custom_constant(self):
        availabilities = hollaex_autofilled_exchange_class.get_exchange_availabilities()
        assert len(availabilities) == len(_CUSTOM_EXCHANGE_AVAILABILITIES)
        for custom_availability, availability in zip(_CUSTOM_EXCHANGE_AVAILABILITIES, availabilities):
            assert availability.internal_name == custom_availability.internal_name
            assert availability.name == custom_availability.name
            assert availability.logo == custom_availability.logo
            assert availability.available_trading_types == list(custom_availability.available_trading_types)
            assert availability.support_type == custom_availability.support_type
            assert availability.sandboxable == custom_availability.sandboxable
            assert availability.broker_enabled == custom_availability.broker_enabled
            assert availability.api_url == custom_availability.api_url
            assert availability.register_url == custom_availability.register_url

    def test_earn_curve_is_spot_only(self):
        availabilities = hollaex_autofilled_exchange_class.get_exchange_availabilities()
        earn_curve_availability = next(
            availability for availability in availabilities if availability.name == "Earn Curve"
        )
        assert earn_curve_availability.internal_name == hollaex_exchange_class.get_name()
        assert earn_curve_availability.available_trading_types == [protocol_models.TradingType.SPOT]

    def test_at_least_one_entry_has_api_url_set(self):
        availabilities = hollaex_autofilled_exchange_class.get_exchange_availabilities()
        entries_with_api_url = [availability for availability in availabilities if availability.api_url]
        assert len(entries_with_api_url) >= 1
        assert all(availability.api_url for availability in entries_with_api_url)

    def test_support_type_and_trading_types_match_constants(self):
        availabilities = hollaex_autofilled_exchange_class.get_exchange_availabilities()
        for availability in availabilities:
            assert availability.support_type == protocol_models.ExchangeSupportStatus.OFFICIALLY_SUPPORTED
            assert availability.available_trading_types == [protocol_models.TradingType.SPOT]
            assert availability.sandboxable is False
            assert availability.broker_enabled is False


class TestCustomExchangeAvailabilitiesConstant:
    def test_tuple_is_non_empty(self):
        assert len(_CUSTOM_EXCHANGE_AVAILABILITIES) > 0

    def test_earn_curve_uses_default_internal_name_spot_support_and_flags(self):
        earn_curve_availability = _CUSTOM_EXCHANGE_AVAILABILITIES[0]
        assert earn_curve_availability.internal_name == hollaex_exchange_class.get_name()
        assert earn_curve_availability.name == "Earn Curve"
        assert earn_curve_availability.api_url == "https://www.earncurve.com.au/api/"
        assert earn_curve_availability.available_trading_types == (protocol_models.TradingType.SPOT,)
        assert earn_curve_availability.support_type == protocol_models.ExchangeSupportStatus.OFFICIALLY_SUPPORTED
        assert earn_curve_availability.sandboxable is False
        assert earn_curve_availability.broker_enabled is False
        assert earn_curve_availability.logo is None
        assert earn_curve_availability.register_url is None

    def test_each_custom_entry_defines_non_empty_api_url(self):
        for custom_availability in _CUSTOM_EXCHANGE_AVAILABILITIES:
            assert custom_availability.api_url

    def test_enum_fields_use_protocol_enums(self):
        for custom_availability in _CUSTOM_EXCHANGE_AVAILABILITIES:
            for trading_type in custom_availability.available_trading_types:
                assert isinstance(trading_type, protocol_models.TradingType)
            assert isinstance(
                custom_availability.support_type,
                protocol_models.ExchangeSupportStatus,
            )
