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
import mock
import pytest

import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
import octobot_trading.exchanges.connectors.simulator.ccxt_client_simulation as ccxt_client_simulation_module


class TestTempClient:
    def test_returns_client_with_merged_config(self):
        exchange_instance = mock.Mock()
        exchange_class = mock.Mock(return_value=exchange_instance)
        custom_domain_config = {"hostname": "custom"}
        with (
            mock.patch.object(
                ccxt_client_util,
                "ccxt_exchange_class_factory",
                return_value=exchange_class,
            ) as factory_mock,
            mock.patch.object(
                ccxt_client_util,
                "get_custom_domain_config",
                return_value=custom_domain_config,
            ) as domain_config_mock,
        ):
            client = ccxt_client_simulation_module._temp_client(
                "binance",
                additional_client_config={"apiKey": "k"},
            )
        factory_mock.assert_called_once_with("binance")
        domain_config_mock.assert_called_once_with(exchange_class)
        exchange_class.assert_called_once_with({"apiKey": "k", "hostname": "custom"})
        assert client is exchange_instance

    def test_uses_empty_config_when_additional_client_config_is_none(self):
        exchange_instance = mock.Mock()
        exchange_class = mock.Mock(return_value=exchange_instance)
        custom_domain_config = {"hostname": "custom"}
        with (
            mock.patch.object(
                ccxt_client_util,
                "ccxt_exchange_class_factory",
                return_value=exchange_class,
            ),
            mock.patch.object(
                ccxt_client_util,
                "get_custom_domain_config",
                return_value=custom_domain_config,
            ),
        ):
            client = ccxt_client_simulation_module._temp_client("binance")
        exchange_class.assert_called_once_with(custom_domain_config)
        assert client is exchange_instance

    def test_raises_attribute_error_when_factory_fails_without_fallback(self):
        with mock.patch.object(
            ccxt_client_util,
            "ccxt_exchange_class_factory",
            side_effect=AttributeError("unknown exchange"),
        ):
            with pytest.raises(AttributeError, match="unknown exchange"):
                ccxt_client_simulation_module._temp_client(
                    "unknown_exchange",
                    allow_fallback=False,
                )

    def test_returns_generic_exchange_when_factory_fails_with_allow_fallback(self):
        fallback_exchange = mock.Mock()
        logger_mock = mock.Mock()
        simulation_module_path = "octobot_trading.exchanges.connectors.simulator.ccxt_client_simulation"
        with (
            mock.patch.object(
                ccxt_client_util,
                "ccxt_exchange_class_factory",
                side_effect=AttributeError("unknown exchange"),
            ),
            mock.patch(
                f"{simulation_module_path}.async_ccxt.Exchange",
                return_value=fallback_exchange,
            ) as exchange_ctor,
            mock.patch(
                f"{simulation_module_path}.commons_logging.get_logger",
                return_value=logger_mock,
            ),
        ):
            client = ccxt_client_simulation_module._temp_client(
                "unknown_exchange",
                allow_fallback=True,
            )
        exchange_ctor.assert_called_once_with()
        logger_mock.warning.assert_called_once()
        error_message = logger_mock.warning.call_args[0][0]
        assert "unknown_exchange" in error_message
        assert "fallback generic exchange" in error_message
        assert client is fallback_exchange
