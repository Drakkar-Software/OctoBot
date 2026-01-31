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
import pytest
import mock

import trading_backend.exchanges
import octobot_commons.constants as commons_constants
import octobot_commons.configuration as commons_configuration
import octobot_trading.enums as enums
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.util.exchange_util as exchange_util

from tests import event_loop
from tests.exchanges import MockedRestExchange, MockedAutoFillRestExchange
import octobot_tentacles_manager.api as api


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
    with mock.patch.object(trading_backend.exchanges.Huobi, "is_valid_account",
                           mock.AsyncMock(return_value=(True, None))) as is_valid_account_mock:
        compatible, auth, error = await exchanges.is_compatible_account("huobi", exchange_config,
                                                                        tentacles_setup_config, False)
        assert compatible is True
        assert auth is True
        assert error is None
        is_valid_account_mock.assert_called_once()
    with mock.patch.object(trading_backend.exchanges.Huobi, "is_valid_account",
                           mock.AsyncMock(return_value=(False, "plop"))) as is_valid_account_mock:
        compatible, auth, error = await exchanges.is_compatible_account("huobi", exchange_config,
                                                                        tentacles_setup_config, False)
        # still True as on spot trading
        assert compatible is True
        assert auth is True
        assert error is None
        is_valid_account_mock.assert_called_once()
    exchange_config[commons_constants.CONFIG_EXCHANGE_TYPE] = commons_constants.CONFIG_EXCHANGE_FUTURE
    with mock.patch.object(trading_backend.exchanges.Huobi, "is_valid_account",
                           mock.AsyncMock(return_value=(False, "plop"))) as is_valid_account_mock:
        compatible, auth, error = await exchanges.is_compatible_account("huobi", exchange_config,
                                                                        tentacles_setup_config, False)
        assert compatible is False
        assert auth is True
        assert "plop" in error and len(error) > len("plop")
        is_valid_account_mock.assert_called_once()


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
    compatible, auth, error = await exchanges.is_compatible_account("hitbtc", exchange_config, tentacles_setup_config,
                                                                    False)
    assert compatible is False
    assert auth is False
    assert isinstance(error, str)
    exchange_config[commons_constants.CONFIG_EXCHANGE_TYPE] = commons_constants.CONFIG_EXCHANGE_FUTURE
    with mock.patch.object(trading_backend.exchanges.Exchange, "is_valid_account",
                           mock.AsyncMock(return_value=(True, "plop"))) as is_valid_account_mock:
        compatible, auth, error = await exchanges.is_compatible_account("hitbtc", exchange_config,
                                                                        tentacles_setup_config, False)
        assert compatible is True
        assert auth is True
        assert "plop" in error and len(error) > len("plop")
        is_valid_account_mock.assert_called_once()
    with mock.patch.object(trading_backend.exchanges.Exchange, "is_valid_account",
                           mock.AsyncMock(side_effect=trading_backend.ExchangeAuthError)) as is_valid_account_mock:
        compatible, auth, error = await exchanges.is_compatible_account("hitbtc", exchange_config,
                                                                        tentacles_setup_config, False)
        assert compatible is False
        assert auth is False
        assert "authentication" in error and len(error) > len("authentication")
        is_valid_account_mock.assert_called_once()


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
        assert details.id == "binance"
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
