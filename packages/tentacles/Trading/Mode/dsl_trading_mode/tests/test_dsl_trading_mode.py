#  Drakkar-Software OctoBot-Tentacles
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
import logging
import os

import mock
import pytest

import async_channel.util as channel_util
import octobot_backtesting.api as backtesting_api
import octobot_commons.constants as commons_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.tests.test_config as test_config
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.enums as trading_enums
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchanges as exchanges

import tentacles.Trading.Mode.dsl_trading_mode.dsl_trading as dsl_trading
import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges


class TestDSLTradingModeClassMethods:
    def test_get_default_config(self):
        config = dsl_trading.DSLTradingMode.get_default_config()
        assert config == {dsl_trading.DSLTradingMode.DSL_SCRIPT: ""}

    def test_get_is_symbol_wildcard(self):
        assert dsl_trading.DSLTradingMode.get_is_symbol_wildcard() is True

    def test_get_supported_exchange_types(self):
        supported = dsl_trading.DSLTradingMode.get_supported_exchange_types()
        assert trading_enums.ExchangeTypes.SPOT in supported
        assert trading_enums.ExchangeTypes.FUTURE in supported
        assert trading_enums.ExchangeTypes.OPTION in supported
        assert len(supported) == 3


class TestDSLTradingMode:
    def test_init(self):
        config = {}
        exchange_manager = mock.Mock()
        mode = dsl_trading.DSLTradingMode(config, exchange_manager)
        assert mode.dsl_script == ""
        assert mode.interpreter is None
        assert mode.config is config
        assert mode.exchange_manager is exchange_manager

    def test_create_interpreter(self):
        config = test_config.load_test_config()
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        mode = dsl_trading.DSLTradingMode(config, exchange_manager)

        interpreter = mode._create_interpreter(None)

        assert isinstance(interpreter, dsl_interpreter.Interpreter)
        assert len(interpreter.operators_by_name) > 0
        assert "close" in interpreter.operators_by_name # create_ohlcv_operators
        assert "total" in interpreter.operators_by_name # create_portfolio_operators
        assert "market" in interpreter.operators_by_name # create_create_order_operators
        assert "cancel_order" in interpreter.operators_by_name # create_cancel_order_operators
        assert "blockchain_wallet_balance" in interpreter.operators_by_name # create_blockchain_wallet_operators

    @pytest.mark.asyncio
    async def test_initialize(self):
        tentacles_manager_api.reload_tentacle_info()
        config = test_config.load_test_config()
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 2000
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        exchange_manager.tentacles_setup_config = test_utils_config.load_test_tentacles_config()
        exchange_manager.is_simulated = True
        exchange_manager.is_backtesting = True
        exchange_manager.use_cached_markets = False
        try:
            backtesting = await backtesting_api.initialize_backtesting(
                config,
                exchange_ids=[exchange_manager.id],
                matrix_id=None,
                data_files=[
                    os.path.join(
                        test_config.TEST_CONFIG_FOLDER,
                        "AbstractExchangeHistoryCollector_1586017993.616272.data",
                    )
                ],
            )
            exchange_manager.exchange = exchanges.ExchangeSimulator(
                exchange_manager.config, exchange_manager, backtesting
            )
            await exchange_manager.exchange.initialize()
            for exchange_channel_class_type in [
                exchanges_channel.ExchangeChannel,
                exchanges_channel.TimeFrameExchangeChannel,
            ]:
                await channel_util.create_all_subclasses_channel(
                    exchange_channel_class_type,
                    exchanges_channel.set_chan,
                    exchange_manager=exchange_manager,
                )
            trader = exchanges.TraderSimulator(config, exchange_manager)
            await trader.initialize()

            mode = dsl_trading.DSLTradingMode(config, exchange_manager)
            mode.symbol = None if mode.get_is_symbol_wildcard() else "BTC/USDT"

            await mode.initialize()

            assert len(mode.producers) == 1
            assert isinstance(mode.producers[0], dsl_trading.DSLTradingModeProducer)
            assert len(mode.consumers) == 1
            assert isinstance(mode.consumers[0], dsl_trading.DSLTradingModeConsumer)
            assert mode.trading_config is not None
        finally:
            for importer in backtesting_api.get_importers(exchange_manager.exchange.backtesting):
                await backtesting_api.stop_importer(importer)
            await exchange_manager.exchange.backtesting.stop()
            await exchange_manager.stop()

    def test_init_user_inputs_same_script(self):
        config = {}
        exchange_manager = mock.Mock()
        mode = dsl_trading.DSLTradingMode(config, exchange_manager)
        mode.UI = mock.Mock()
        mode.UI.user_input = mock.Mock(return_value="1 + 1")
        mode.dsl_script = "1 + 1"
        mode.on_new_dsl_script = mock.Mock()
        mock_interpreter = mock.Mock()
        with mock.patch.object(
            dsl_trading.DSLTradingMode, "_create_interpreter",
            mock.Mock(return_value=mock_interpreter)
        ):
            mode.init_user_inputs({})

        mode.UI.user_input.assert_called_once_with(
            dsl_trading.DSLTradingMode.DSL_SCRIPT,
            commons_enums.UserInputTypes.TEXT,
            "",
            {},
            other_schema_values={"minLength": 0},
            title="DSL script: The DSL script to use for the trading mode. Example: limit('buy', 'BTC/USDT', 0.01, price='-1%')"
        )
        mode.on_new_dsl_script.assert_not_called()

    def test_init_user_inputs_new_script(self):
        config = {}
        exchange_manager = mock.Mock()
        mode = dsl_trading.DSLTradingMode(config, exchange_manager)
        mode.UI = mock.Mock()
        mode.UI.user_input = mock.Mock(return_value="close[-1]")
        mode.dsl_script = ""
        mode.on_new_dsl_script = mock.Mock()
        mock_interpreter = mock.Mock()
        with mock.patch.object(
            dsl_trading.DSLTradingMode, "_create_interpreter",
            mock.Mock(return_value=mock_interpreter)
        ):
            mode.init_user_inputs({})

        assert mode.dsl_script == "close[-1]"
        mode.on_new_dsl_script.assert_called_once()

    def test_on_new_dsl_script_success(self, caplog):
        config = test_config.load_test_config()
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        mode = dsl_trading.DSLTradingMode(config, exchange_manager)

        with caplog.at_level(logging.INFO):
            mode.set_dsl_script("1 + 1")

        assert "DSL script successfully loaded" in caplog.text
        assert isinstance(mode.interpreter.get_dependencies(), list)

    def test_on_new_dsl_script_dsl_interpreter_error(self, caplog):
        config = test_config.load_test_config()
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        mode = dsl_trading.DSLTradingMode(config, exchange_manager)

        with caplog.at_level(logging.ERROR):
            mode.set_dsl_script("undefined_operator_xyz()", raise_on_error=False)

        assert "Error when parsing DSL script" in caplog.text

    def test_on_new_dsl_script_dsl_interpreter_error_raises_when_raise_on_error_true(
        self, caplog
    ):
        config = test_config.load_test_config()
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        mode = dsl_trading.DSLTradingMode(config, exchange_manager)

        with caplog.at_level(logging.ERROR), pytest.raises(commons_errors.DSLInterpreterError):
            mode.set_dsl_script("undefined_operator_xyz()", raise_on_error=True)

        assert "Error when parsing DSL script" in caplog.text

    def test_on_new_dsl_script_unexpected_error(self, caplog):
        config = test_config.load_test_config()
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        mode = dsl_trading.DSLTradingMode(config, exchange_manager)

        with caplog.at_level(logging.ERROR):
            mode.set_dsl_script("syntax error {", raise_on_error=False)

        assert "Unexpected error when parsing DSL script" in caplog.text

    def test_on_new_dsl_script_unexpected_error_raises_when_raise_on_error_true(
        self, caplog
    ):
        config = test_config.load_test_config()
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        mode = dsl_trading.DSLTradingMode(config, exchange_manager)

        with caplog.at_level(logging.ERROR), pytest.raises(SyntaxError):
            mode.set_dsl_script("syntax error {", raise_on_error=True)

        assert "Unexpected error when parsing DSL script" in caplog.text

    @pytest.mark.asyncio
    async def test_stop(self):
        config = {}
        exchange_manager = mock.Mock()
        mode = dsl_trading.DSLTradingMode(config, exchange_manager)
        mode.interpreter = mock.Mock()
        with mock.patch.object(
            dsl_trading.trading_modes.AbstractTradingMode, "stop", mock.AsyncMock()
        ) as super_stop_mock:
            await mode.stop()
            super_stop_mock.assert_awaited_once()
            assert mode.interpreter is None


class TestDSLTradingModeProducer:
    @pytest.mark.asyncio
    async def test_set_final_eval(self):
        config = {}
        exchange_manager = mock.Mock()
        exchange_manager.exchange_config.traded_symbol_pairs = ["BTC/USDT"]
        trading_mode = dsl_trading.DSLTradingMode(config, exchange_manager)
        trading_mode.interpreter = mock.Mock()
        dsl_result = mock.Mock(result=42)
        trading_mode.interpreter.compute_expression_with_result = mock.AsyncMock(
            return_value=dsl_result
        )

        producer = dsl_trading.DSLTradingModeProducer(
            channel=mock.Mock(),
            config=config,
            trading_mode=trading_mode,
            exchange_manager=exchange_manager
        )
        producer.logger = mock.Mock()

        await producer.set_final_eval(
            matrix_id="matrix_1",
            cryptocurrency="Bitcoin",
            symbol="BTC/USDT",
            time_frame="1h",
            trigger_source="ohlcv"
        )

        assert producer.logger.info.call_count == 2
        assert "matrix_1" in producer.logger.info.call_args_list[0][0][0]
        assert "Bitcoin" in producer.logger.info.call_args_list[0][0][0]
        assert "BTC/USDT" in producer.logger.info.call_args_list[0][0][0]
        trading_mode.interpreter.compute_expression_with_result.assert_awaited_once()
