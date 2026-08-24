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