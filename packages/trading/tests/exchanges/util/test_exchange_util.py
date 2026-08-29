#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import contextlib

import pytest
import mock

import octobot_commons.constants as commons_constants
import octobot_commons.configuration as commons_configuration
import octobot_commons.enums as commons_enums
import octobot_commons.profiles as commons_profiles
import octobot_protocol.models as protocol_models
import octobot_trading.enums as enums
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.util.exchange_util as exchange_util

from tests import event_loop
from tests.exchanges import MockedRestExchange, MockedAutoFillRestExchange
import octobot_tentacles_manager.api as api
import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration


def _mocked_exchange_builder(exchange_manager):
    builder = mock.Mock()
    for method_name in (
        "use_tentacles_setup_config",
        "is_checking_credentials",
        "disable_unauth_retry",
        "is_sandboxed",
        "is_using_exchange_type",
        "use_exchange_config_by_exchange",
        "is_exchange_only",
        "is_rest_only",
        "is_broker_enabled",
        "use_cached_markets",
        "use_market_filter",
        "is_ignoring_config",
        "disable_trading_mode",
    ):
        getattr(builder, method_name).return_value = builder
    builder.build = mock.AsyncMock(return_value=exchange_manager)
    builder.clear = mock.Mock()
    return builder


def _mocked_local_exchange_manager():
    exchange_manager = mock.Mock()
    exchange_manager.exchange.connector.logger = mock.Mock()
    exchange_manager.stop = mock.AsyncMock()
    return exchange_manager


@pytest.fixture
def tentacles_setup_config():
    setup_config = mock.Mock()
    setup_config.is_tentacle_activated = mock.Mock(return_value=True)
    return setup_config


@pytest.fixture()
def exchange_config():
    return {
        commons_constants.CONFIG_EXCHANGE_KEY: commons_configuration.encrypt("01234").decode(),
        commons_constants.CONFIG_EXCHANGE_SECRET: commons_configuration.encrypt("012345").decode()
    }


@pytest.fixture()
def supported_exchanges():
    return {
        "plop.exchange": exchanges.ExchangeDetails("id_plop", "name_plop", "url_plop", "api_plop", "logo_plop", True),
        "blip": exchanges.ExchangeDetails("id_blip", "name_blip", "url_blip", "api_blip", "logo_blip", True)
    }


@pytest.mark.asyncio
async def test_is_compatible_account_with_checked_exchange(exchange_config, tentacles_setup_config):
    local_exchange_manager = mock.Mock()
    local_exchange_manager.exchange = mock.Mock()
    local_exchange_manager.exchange.connector = mock.Mock()
    local_exchange_manager.exchange.request_exchange_to_ensure_authentication = mock.AsyncMock(return_value=None)
    local_exchange_manager.exchange.ensure_api_key_permissions = mock.AsyncMock(return_value=None)

    @contextlib.asynccontextmanager
    async def mocked_local_exchange_manager(*args, **kwargs):
        yield local_exchange_manager

    with mock.patch.object(exchange_util, "get_local_exchange_manager", mocked_local_exchange_manager):
        compatible, auth, error = await exchanges.is_compatible_account("huobi", exchange_config,
                                                                        tentacles_setup_config, False)
        assert compatible is True
        assert auth is True
        assert error is None
        local_exchange_manager.exchange.request_exchange_to_ensure_authentication.assert_called_once()
        local_exchange_manager.exchange.ensure_api_key_permissions.assert_called_once()

    local_exchange_manager.exchange.request_exchange_to_ensure_authentication = mock.AsyncMock(
        side_effect=trading_errors.AuthenticationError("invalid keys")
    )
    with mock.patch.object(exchange_util, "get_local_exchange_manager", mocked_local_exchange_manager):
        compatible, auth, error = await exchanges.is_compatible_account("huobi", exchange_config,
                                                                        tentacles_setup_config, False)
        assert compatible is False
        assert auth is False
        assert "Invalid Huobi authentication details" in error
        local_exchange_manager.exchange.request_exchange_to_ensure_authentication.assert_called_once()

    exchange_config[commons_constants.CONFIG_EXCHANGE_TYPE] = commons_constants.CONFIG_EXCHANGE_FUTURE
    local_exchange_manager.exchange.request_exchange_to_ensure_authentication = mock.AsyncMock(
        side_effect=Exception("plop")
    )
    with mock.patch.object(exchange_util, "get_local_exchange_manager", mocked_local_exchange_manager):
        compatible, auth, error = await exchanges.is_compatible_account("huobi", exchange_config,
                                                                        tentacles_setup_config, False)
        assert compatible is True
        assert auth is False
        assert "Error when loading exchange account: plop" == error
        local_exchange_manager.exchange.request_exchange_to_ensure_authentication.assert_called_once()


def test_get_partners_explanation_message():
    assert ".cloud/en/guides" in exchanges.get_partners_explanation_message()


def test_log_time_sync_error():
    logger = mock.Mock()
    exchanges.log_time_sync_error(logger, "exchange_name", "error", "hello call")
    args = logger.error.call_args[0][0]
    assert "exchange_name".capitalize() in args
    assert "error" in args
    assert "hello call" in args
    assert ".cloud/en/guides" in args


@pytest.mark.asyncio
async def test_is_compatible_account_with_unchecked_exchange(exchange_config, tentacles_setup_config):
    local_exchange_manager = mock.Mock()
    local_exchange_manager.exchange = mock.Mock()
    local_exchange_manager.exchange.connector = mock.Mock()
    local_exchange_manager.exchange.request_exchange_to_ensure_authentication = mock.AsyncMock(
        side_effect=trading_errors.FailedRequest("network")
    )

    @contextlib.asynccontextmanager
    async def mocked_local_exchange_manager(*args, **kwargs):
        yield local_exchange_manager

    with mock.patch.object(exchange_util, "get_local_exchange_manager", mocked_local_exchange_manager):
        compatible, auth, error = await exchanges.is_compatible_account("hitbtc", exchange_config, tentacles_setup_config,
                                                                        False)
    assert compatible is False
    assert auth is False
    assert error == "network"
    local_exchange_manager.exchange.request_exchange_to_ensure_authentication.assert_called_once()

    exchange_config[commons_constants.CONFIG_EXCHANGE_TYPE] = commons_constants.CONFIG_EXCHANGE_FUTURE
    local_exchange_manager.exchange.request_exchange_to_ensure_authentication = mock.AsyncMock(return_value=None)
    local_exchange_manager.exchange.ensure_api_key_permissions = mock.AsyncMock(return_value=None)
    with mock.patch.object(exchange_util, "get_local_exchange_manager", mocked_local_exchange_manager):
        compatible, auth, error = await exchanges.is_compatible_account("hitbtc", exchange_config,
                                                                        tentacles_setup_config, False)
        assert compatible is True
        assert auth is True
        assert error is None
        local_exchange_manager.exchange.request_exchange_to_ensure_authentication.assert_called_once()
        local_exchange_manager.exchange.ensure_api_key_permissions.assert_called_once()

    local_exchange_manager.exchange.request_exchange_to_ensure_authentication = mock.AsyncMock(
        side_effect=trading_errors.AuthenticationError("bad key")
    )
    with mock.patch.object(exchange_util, "get_local_exchange_manager", mocked_local_exchange_manager):
        compatible, auth, error = await exchanges.is_compatible_account("hitbtc", exchange_config,
                                                                        tentacles_setup_config, False)
        assert compatible is False
        assert auth is False
        assert "Invalid Hitbtc authentication details" in error
        local_exchange_manager.exchange.request_exchange_to_ensure_authentication.assert_called_once()


def test_get_auto_filled_exchange_names(tentacles_setup_config, supported_exchanges):
    with mock.patch.object(api, "get_tentacle_config", mock.Mock()) as get_tentacle_config_mock:
        # no auto filled exchanges
        assert exchanges.get_auto_filled_exchange_names(tentacles_setup_config) == []
        get_tentacle_config_mock.assert_called_once_with(tentacles_setup_config, MockedAutoFillRestExchange)
        get_tentacle_config_mock.reset_mock()

        with MockedAutoFillRestExchange.patched_supported_exchanges(supported_exchanges):
            auto_filled_exchanges = exchanges.get_auto_filled_exchange_names(tentacles_setup_config)
            assert auto_filled_exchanges == list(supported_exchanges)
            assert "blip" in auto_filled_exchanges
            get_tentacle_config_mock.assert_called_once_with(tentacles_setup_config, MockedAutoFillRestExchange)


def test_get_exchange_class_from_name(tentacles_setup_config, supported_exchanges):
    # not found exchange
    assert exchanges.get_exchange_class_from_name(
        exchanges.RestExchange, "plop", tentacles_setup_config, None, True,
        strict_name_matching=False
    ) == exchanges.DefaultRestExchange
    with mock.patch.object(api, "get_tentacle_config", mock.Mock()) as get_tentacle_config_mock:
        assert exchanges.get_exchange_class_from_name(
            exchanges.RestExchange, "plop", tentacles_setup_config, None, False,
            strict_name_matching=False
        ) == MockedRestExchange
        get_tentacle_config_mock.assert_not_called()
        assert exchanges.get_exchange_class_from_name(
            exchanges.RestExchange, "plop", tentacles_setup_config, None, True,
            strict_name_matching=True
        ) is None
        get_tentacle_config_mock.assert_called_once()
        get_tentacle_config_mock.reset_mock()

    # regular exchange
    assert exchanges.get_exchange_class_from_name(
        exchanges.RestExchange, MockedRestExchange.get_name(), tentacles_setup_config, None,True,
        strict_name_matching=False
    ) == exchanges.DefaultRestExchange
    assert exchanges.get_exchange_class_from_name(
        exchanges.RestExchange, MockedRestExchange.get_name(), tentacles_setup_config, None,False,
        strict_name_matching=False
    ) == MockedRestExchange
    assert exchanges.get_exchange_class_from_name(
        exchanges.RestExchange, MockedRestExchange.get_name(), tentacles_setup_config, None,True,
        strict_name_matching=True
    ) == MockedRestExchange

    with mock.patch.object(api, "get_tentacle_config", mock.Mock()) as get_tentacle_config_mock:
        # auto-filled exchange
        with MockedAutoFillRestExchange.patched_supported_exchanges(supported_exchanges):
            assert exchanges.get_exchange_class_from_name(
                exchanges.RestExchange, MockedRestExchange.get_name(), tentacles_setup_config, None,True,
                strict_name_matching=False
            ) == exchanges.DefaultRestExchange
            assert exchanges.get_exchange_class_from_name(
                exchanges.RestExchange, MockedRestExchange.get_name(), tentacles_setup_config, None,False,
                strict_name_matching=False
            ) == MockedRestExchange
            assert exchanges.get_exchange_class_from_name(
                exchanges.RestExchange, MockedRestExchange.get_name(), tentacles_setup_config, None,True,
                strict_name_matching=True
            ) == MockedRestExchange

            get_tentacle_config_mock.assert_not_called()

            assert exchanges.get_exchange_class_from_name(
                exchanges.RestExchange, "blip", tentacles_setup_config, None,True,
                strict_name_matching=False
            ) == exchanges.DefaultRestExchange
            assert exchanges.get_exchange_class_from_name(
                exchanges.RestExchange, "blip", tentacles_setup_config, None,False,
                strict_name_matching=False
            ) == MockedRestExchange
            get_tentacle_config_mock.assert_not_called()
            assert exchanges.get_exchange_class_from_name(
                exchanges.RestExchange, "blip", tentacles_setup_config, None, True,
                strict_name_matching=True
            ) == MockedAutoFillRestExchange
            get_tentacle_config_mock.assert_called_once()


@pytest.mark.asyncio
async def test_get_exchange_details(tentacles_setup_config, supported_exchanges):
    with mock.patch.object(api, "get_tentacle_config", mock.Mock()) as get_tentacle_config_mock:
        # not found exchange
        with pytest.raises(KeyError):
            await exchanges.get_exchange_details(
                "blip", False, tentacles_setup_config, None
            )
        get_tentacle_config_mock.assert_not_called()
        with pytest.raises(KeyError):
            await exchanges.get_exchange_details(
                "blip", True, tentacles_setup_config, None
            )
        get_tentacle_config_mock.assert_called_once()
        get_tentacle_config_mock.reset_mock()

        # regular exchange
        details = await exchanges.get_exchange_details(
            "binance", False, tentacles_setup_config, None
        )
        assert details.id == "ob_binance"
        assert details.name == "Binance"
        assert details.url == "https://www.binance.com"
        assert len(details.api) > 1
        assert "https://github.com/user-attachments/assets" in details.logo_url
        assert details.has_websocket is False   # default value
        get_tentacle_config_mock.assert_not_called()

        # auto-filled exchange
        with MockedAutoFillRestExchange.patched_supported_exchanges(supported_exchanges):
            with pytest.raises(KeyError):
                await exchanges.get_exchange_details(
                    "blip", False, tentacles_setup_config, None
                )
            get_tentacle_config_mock.assert_not_called()
            details = await exchanges.get_exchange_details(
                "blip", True, tentacles_setup_config, None
            )
            assert details == supported_exchanges["blip"]
            get_tentacle_config_mock.assert_called_once()


def test_is_error_on_this_type():
    errors = [("api", "key", "doesn't exist"),]

    assert exchange_util.is_error_on_this_type(Exception("plop"), errors) is False
    assert exchange_util.is_error_on_this_type(Exception("api key doesn't exist"), errors) is True
    assert exchange_util.is_error_on_this_type(Exception("api"), errors) is False
    assert exchange_util.is_error_on_this_type(Exception("api"), errors) is False


def test_update_raw_order_from_raw_trade():
    required_keys = [
        enums.ExchangeConstantsOrderColumns.INFO,
        enums.ExchangeConstantsOrderColumns.EXCHANGE_ID,
        enums.ExchangeConstantsOrderColumns.SYMBOL,
        enums.ExchangeConstantsOrderColumns.TYPE,
        enums.ExchangeConstantsOrderColumns.AMOUNT,
        enums.ExchangeConstantsOrderColumns.DATETIME,
        enums.ExchangeConstantsOrderColumns.SIDE,
        enums.ExchangeConstantsOrderColumns.TAKER_OR_MAKER,
        enums.ExchangeConstantsOrderColumns.PRICE,
        enums.ExchangeConstantsOrderColumns.TIMESTAMP,
        enums.ExchangeConstantsOrderColumns.STATUS,
        enums.ExchangeConstantsOrderColumns.FILLED,
        enums.ExchangeConstantsOrderColumns.COST,
        enums.ExchangeConstantsOrderColumns.REMAINING,
        enums.ExchangeConstantsOrderColumns.FEE,
        enums.ExchangeConstantsOrderColumns.TAG,
        enums.ExchangeConstantsOrderColumns.REDUCE_ONLY,
    ]
    default_value = exchange_util.update_raw_order_from_raw_trade({}, {})
    assert all(key.value in default_value for key in required_keys)
    with_trade_values = exchange_util.update_raw_order_from_raw_trade(
        {}, {**{k.value: k.name for k in required_keys}, **{
            enums.ExchangeConstantsOrderColumns.ORDER.value: "EXCHANGE_ID",
            enums.ExchangeConstantsOrderColumns.AMOUNT.value: "AMOUNT",
        }}
    )
    for key in required_keys:
        if key == enums.ExchangeConstantsOrderColumns.STATUS:
            assert with_trade_values[key.value] == enums.OrderStatus.FILLED.value
        elif key == enums.ExchangeConstantsOrderColumns.REMAINING:
            assert with_trade_values[key.value] == 0
        elif key == enums.ExchangeConstantsOrderColumns.FILLED:
            assert with_trade_values[key.value] == "AMOUNT"
        elif key == enums.ExchangeConstantsOrderColumns.EXCHANGE_ID:
            assert with_trade_values[key.value] == "EXCHANGE_ID"
        else:
            assert with_trade_values[key.value] == key.name


class TestGetLocalExchangeManager:
    @pytest.mark.asyncio
    async def test_attaches_ephemeral_profile_when_exchange_config_by_exchange_provided(self):
        tentacles_setup_config = mock.Mock()
        tentacles_setup_config.profile = None
        exchange_config_by_exchange = {
            "HollaexAutofilled": {
                "auto_filled": {
                    "cne": {"url": "https://www.cne.kg/api/"},
                }
            }
        }
        exchange_manager = _mocked_local_exchange_manager()
        builder = _mocked_exchange_builder(exchange_manager)

        async with exchange_util.get_local_exchange_manager(
            "cne",
            {},
            tentacles_setup_config,
            False,
            builder=builder,
            exchange_config_by_exchange=exchange_config_by_exchange,
        ):
            pass

        assert isinstance(
            tentacles_setup_config.profile, commons_profiles.EphemeralProfile
        )
        assert tentacles_setup_config.profile.get_profile_data().get_config_by_tentacle() == (
            exchange_config_by_exchange
        )

    @pytest.mark.asyncio
    async def test_leaves_profile_none_when_exchange_config_by_exchange_missing(self):
        tentacles_setup_config = mock.Mock()
        tentacles_setup_config.profile = None
        exchange_manager = _mocked_local_exchange_manager()
        builder = _mocked_exchange_builder(exchange_manager)

        async with exchange_util.get_local_exchange_manager(
            "binance",
            {},
            tentacles_setup_config,
            False,
            builder=builder,
            exchange_config_by_exchange=None,
        ):
            pass

        assert tentacles_setup_config.profile is None

    @pytest.mark.asyncio
    async def test_ephemeral_profile_preserves_auto_filled_in_tentacle_config(self):
        tentacles_setup_config = mock.Mock()
        tentacles_setup_config.profile = None
        exchange_config_by_exchange = {
            "HollaexAutofilled": {
                "auto_filled": {
                    "cne": {"url": "https://www.cne.kg/api/"},
                }
            }
        }
        exchange_manager = _mocked_local_exchange_manager()
        builder = _mocked_exchange_builder(exchange_manager)
        tentacle_klass = type(
            "HollaexAutofilled",
            (),
            {"get_name": staticmethod(lambda: "HollaexAutofilled")},
        )()

        async with exchange_util.get_local_exchange_manager(
            "cne",
            {},
            tentacles_setup_config,
            False,
            builder=builder,
            exchange_config_by_exchange=exchange_config_by_exchange,
        ):
            with mock.patch.object(
                tentacle_configuration,
                "_get_config_from_file_system",
                mock.Mock(return_value={"auto_filled": {}}),
            ):
                tentacle_config = api.get_tentacle_config(
                    tentacles_setup_config, tentacle_klass
                )

        assert tentacle_config["auto_filled"] == {
            "cne": {"url": "https://www.cne.kg/api/"},
        }


class TestGetHistoricalOhlcv:
    @pytest.mark.asyncio
    async def test_stops_when_start_time_does_not_advance(self):
        static_candle = [[86400000, 40000.0, 41000.0, 39000.0, 40500.0, 100.0]]
        exchange = mock.Mock()
        exchange.get_exchange_current_time.return_value = 1_700_000_000
        exchange.get_symbol_prices = mock.AsyncMock(return_value=static_candle)

        async def retry_till_success(_timeout, func, *args, **kwargs):
            return await func(*args, **kwargs)

        exchange.retry_till_success = retry_till_success
        exchange.get_option_value.return_value = None

        exchange_manager = mock.Mock()
        exchange_manager.exchange = exchange

        batches = []
        logger_mock = mock.Mock()
        with mock.patch.object(exchange_util, "_get_logger", return_value=logger_mock):
            async for batch in exchange_util.get_historical_ohlcv(
                exchange_manager,
                "BTC/USDT",
                commons_enums.TimeFrames.ONE_DAY,
                1_000_000_000,
                2_000_000_000_000,
            ):
                batches.append(batch)

        assert len(batches) == 1
        assert batches[0] == static_candle
        logger_mock.warning.assert_called_once()
        assert "start_time did not advance" in logger_mock.warning.call_args[0][0]


class TestGetDefaultExchangeReferenceMarket:
    @mock.patch.object(
        exchange_util.ccxt_client_util,
        "get_option_value_from_new_ccxt_client",
        return_value="USDC",
    )
    def test_returns_ccxt_default_quote_currency_when_set(self, _mock_get_option):
        assert exchange_util.get_default_exchange_reference_market("binance") == "USDC"

    @mock.patch.object(
        exchange_util.ccxt_client_util,
        "get_option_value_from_new_ccxt_client",
        return_value=None,
    )
    def test_falls_back_to_default_reference_market_when_option_missing(self, _mock_get_option):
        assert (
            exchange_util.get_default_exchange_reference_market("kraken")
            == commons_constants.DEFAULT_REFERENCE_MARKET
        )

    def test_returns_default_reference_market_for_unknown_exchange(self):
        assert (
            exchange_util.get_default_exchange_reference_market("????")
            == commons_constants.DEFAULT_REFERENCE_MARKET
        )

    @mock.patch.object(
        exchange_util,
        "get_default_exchange_reference_market",
        side_effect=lambda exchange_name: "USDC" if exchange_name == "binance" else "USDT",
    )
    def test_get_default_reference_market_per_exchange(self, _mock_get_default):
        assert exchange_util.get_default_reference_market_per_exchange(["binance", "kraken"]) == {
            "binance": "USDC",
            "kraken": "USDT",
        }


def _mock_describe_exchange_class(name, logo=None, referral=None):
    class _Exchange:
        def describe(self):
            return {"name": name, "urls": {"logo": logo, "referral": referral}}
    return _Exchange


class TestGetExchangeSupportStatus:
    def test_tested_exchange_is_officially_supported(self):
        assert (
            exchange_util._get_exchange_support_status("binance")
            == protocol_models.ExchangeSupportStatus.OFFICIALLY_SUPPORTED
        )

    def test_simulator_tested_exchange_is_partially_tested(self):
        assert (
            exchange_util._get_exchange_support_status("bitfinex")
            == protocol_models.ExchangeSupportStatus.PARTIALLY_TESTED
        )

    def test_unknown_exchange_is_untested(self):
        assert (
            exchange_util._get_exchange_support_status("unknown-exchange")
            == protocol_models.ExchangeSupportStatus.UNTESTED
        )

    def test_tested_exchange_takes_precedence_over_simulator_list(self):
        assert "binance" in exchange_util.constants.TESTED_EXCHANGES
        assert (
            exchange_util._get_exchange_support_status("binance")
            == protocol_models.ExchangeSupportStatus.OFFICIALLY_SUPPORTED
        )


class TestGetCcxtExchangeMetadata:
    @mock.patch.object(
        exchange_util.ccxt_client_util,
        "ccxt_exchange_class_factory",
    )
    def test_returns_describe_metadata_without_instantiation(self, factory_mock):
        exchange_class = _mock_describe_exchange_class(
            "Binance",
            logo="https://logo.example/binance",
            referral="https://register.example/binance",
        )
        factory_mock.return_value = exchange_class
        metadata = exchange_util._get_ccxt_exchange_metadata("binance")
        factory_mock.assert_called_once_with("binance")
        assert metadata["name"] == "Binance"
        assert metadata["urls"]["logo"] == "https://logo.example/binance"
        assert metadata["urls"]["referral"] == "https://register.example/binance"


class TestIsExchangeSandboxable:
    def test_returns_true_when_has_sandbox_is_true(self):
        assert exchange_util._is_exchange_sandboxable({"has": {"sandbox": True}}) is True

    def test_returns_false_when_has_sandbox_is_false(self):
        assert exchange_util._is_exchange_sandboxable({"has": {"sandbox": False}}) is False

    def test_returns_false_when_has_or_sandbox_is_missing(self):
        assert exchange_util._is_exchange_sandboxable({}) is False
        assert exchange_util._is_exchange_sandboxable({"has": {}}) is False

    def test_ignores_urls_test_when_has_sandbox_is_absent(self):
        assert exchange_util._is_exchange_sandboxable({
            "urls": {"test": "https://test.example"},
        }) is False


class TestBuildCcxtExchangeAvailability:
    @mock.patch.object(exchange_util, "is_broker_enabled_on_exchange", return_value=False)
    @mock.patch.object(exchange_util, "get_supported_exchange_types")
    @mock.patch.object(exchange_util, "_get_ccxt_exchange_metadata")
    def test_builds_exchange_availability_from_metadata(
        self,
        metadata_mock,
        supported_types_mock,
        _broker_enabled_mock,
    ):
        metadata_mock.return_value = {
            "name": "Binance",
            "urls": {
                "logo": "https://logo.example/binance",
                "referral": {
                    "url": "https://register.example/binance",
                    "discount": 0.1,
                },
            },
        }
        supported_types_mock.return_value = [enums.ExchangeTypes.SPOT, enums.ExchangeTypes.FUTURE]
        availability = exchange_util._build_ccxt_exchange_availability("binance")
        assert availability.internal_name == "binance"
        assert availability.name == "Binance"
        assert availability.logo == "https://logo.example/binance"
        assert availability.register_url == "https://register.example/binance"
        assert availability.api_url is None
        assert availability.sandboxable is False
        assert availability.broker_enabled is False
        assert availability.available_trading_types == [
            protocol_models.TradingType.SPOT,
            protocol_models.TradingType.FUTURES,
        ]

    @mock.patch.object(exchange_util, "is_broker_enabled_on_exchange", return_value=False)
    @mock.patch.object(exchange_util, "get_supported_exchange_types")
    @mock.patch.object(exchange_util, "_get_ccxt_exchange_metadata")
    def test_sets_sandboxable_when_has_sandbox_true(
        self,
        metadata_mock,
        supported_types_mock,
        _broker_enabled_mock,
    ):
        metadata_mock.return_value = {
            "name": "Binance",
            "has": {"sandbox": True},
            "urls": {},
        }
        supported_types_mock.return_value = [enums.ExchangeTypes.SPOT]
        availability = exchange_util._build_ccxt_exchange_availability("binance")
        assert availability.sandboxable is True
        assert availability.broker_enabled is False

    @mock.patch.object(exchange_util, "is_broker_enabled_on_exchange", return_value=True)
    @mock.patch.object(exchange_util, "get_supported_exchange_types")
    @mock.patch.object(exchange_util, "_get_ccxt_exchange_metadata")
    def test_sets_broker_enabled_from_octobot_has_broker(
        self,
        metadata_mock,
        supported_types_mock,
        broker_enabled_mock,
    ):
        metadata_mock.return_value = {
            "name": "Binance",
            "urls": {},
        }
        supported_types_mock.return_value = [enums.ExchangeTypes.SPOT]
        availability = exchange_util._build_ccxt_exchange_availability("binance")
        broker_enabled_mock.assert_called_once_with("binance")
        assert availability.broker_enabled is True
        assert availability.sandboxable is False

    @mock.patch.object(exchange_util, "get_supported_exchange_types")
    @mock.patch.object(exchange_util, "_get_ccxt_exchange_metadata")
    def test_lists_ob_subclass_metadata_under_normal_internal_name(
        self,
        metadata_mock,
        supported_types_mock,
    ):
        partner_register_url = "https://accounts.binance.com/en/register?ref=528112221"
        metadata_mock.return_value = {
            "name": "Binance",
            "urls": {
                "logo": "https://logo.example/binance",
                "referral": {
                    "url": partner_register_url,
                },
            },
        }
        supported_types_mock.return_value = [enums.ExchangeTypes.SPOT]
        availability = exchange_util._build_ccxt_exchange_availability("binance")
        metadata_mock.assert_called_once_with("binance")
        assert availability.internal_name == "binance"
        assert availability.register_url == partner_register_url


class TestIterCcxtAvailabilityInternalNames:
    @mock.patch.object(exchange_util.ccxt, "exchanges", new=["binance", "ob_binance", "kraken"])
    def test_prefers_ob_variant_base_name_and_skips_duplicate_base_row(self):
        assert exchange_util._iter_ccxt_availability_internal_names() == ["binance", "kraken"]

    @mock.patch.object(exchange_util.ccxt, "exchanges", new=["ob_weex"])
    def test_lists_ob_only_exchange_under_normal_internal_name(self):
        assert exchange_util._iter_ccxt_availability_internal_names() == ["weex"]

    @mock.patch.object(exchange_util.ccxt, "exchanges", new=["kraken"])
    def test_lists_exchange_without_ob_variant(self):
        assert exchange_util._iter_ccxt_availability_internal_names() == ["kraken"]


class TestCollectTentacleExchangeAvailabilities:
    @mock.patch.object(exchange_util.tentacles_management, "get_all_classes_from_parent")
    def test_collects_only_non_simulated_non_default_extras(self, get_classes_mock):
        tentacle_extra = protocol_models.ExchangeAvailability(
            internal_name="custom",
            name="Custom",
            available_trading_types=[protocol_models.TradingType.SPOT],
            api_url="https://example.com/api/",
        )

        class _SimulatedExchange:
            @classmethod
            def is_simulated_exchange(cls):
                return True

            @classmethod
            def is_default_exchange(cls):
                return False

            @classmethod
            def get_exchange_availabilities(cls):
                return [tentacle_extra]

        class _CustomExchange:
            @classmethod
            def is_simulated_exchange(cls):
                return False

            @classmethod
            def is_default_exchange(cls):
                return False

            @classmethod
            def get_exchange_availabilities(cls):
                return [tentacle_extra]

        get_classes_mock.return_value = [_SimulatedExchange, _CustomExchange]
        collected_availabilities = exchange_util._collect_tentacle_exchange_availabilities()
        assert collected_availabilities == [tentacle_extra]


class TestGetExchangesAvailability:
    def setup_method(self):
        exchange_util.get_exchanges_availability.cache.clear()

    def teardown_method(self):
        exchange_util.get_exchanges_availability.cache.clear()

    @mock.patch.object(exchange_util, "_collect_tentacle_exchange_availabilities")
    @mock.patch.object(exchange_util, "_build_ccxt_exchange_availability")
    @mock.patch.object(exchange_util.ccxt, "exchanges", new=["binance", "ob_binance", "broken"])
    def test_merges_ccxt_and_tentacle_entries_sorted_by_internal_name(
        self,
        build_ccxt_mock,
        collect_tentacle_mock,
    ):
        ccxt_availability = protocol_models.ExchangeAvailability(
            internal_name="binance",
            name="Binance",
            available_trading_types=[protocol_models.TradingType.SPOT],
            api_url=None,
        )
        tentacle_availability = protocol_models.ExchangeAvailability(
            internal_name="custom",
            name="Custom",
            available_trading_types=[protocol_models.TradingType.SPOT],
            api_url="https://example.com/api/",
        )

        def build_side_effect(exchange_name):
            if exchange_name == "broken":
                raise AttributeError("broken exchange")
            return ccxt_availability

        build_ccxt_mock.side_effect = build_side_effect
        collect_tentacle_mock.return_value = [tentacle_availability]
        availabilities = exchange_util.get_exchanges_availability()
        assert availabilities == [ccxt_availability, tentacle_availability]
        called_exchange_names = [call.args[0] for call in build_ccxt_mock.call_args_list]
        assert called_exchange_names == ["binance", "broken"]
        entries_with_api_url = [availability for availability in availabilities if availability.api_url]
        assert len(entries_with_api_url) == 1
        assert entries_with_api_url[0].api_url == "https://example.com/api/"


class TestGetExchangesAvailabilityCaching:
    def setup_method(self):
        exchange_util.get_exchanges_availability.cache.clear()

    def teardown_method(self):
        exchange_util.get_exchanges_availability.cache.clear()

    @mock.patch.object(exchange_util, "_build_exchanges_availability")
    def test_caches_full_list_between_calls(self, build_mock):
        expected_availabilities = [
            protocol_models.ExchangeAvailability(
                internal_name="binance",
                name="Binance",
                available_trading_types=[protocol_models.TradingType.SPOT],
            )
        ]
        build_mock.return_value = expected_availabilities
        first_call = exchange_util.get_exchanges_availability()
        second_call = exchange_util.get_exchanges_availability()
        assert first_call is second_call
        build_mock.assert_called_once()