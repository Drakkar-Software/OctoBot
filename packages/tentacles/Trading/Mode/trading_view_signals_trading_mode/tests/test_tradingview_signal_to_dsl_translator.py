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
import mock
import pytest

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors
import tentacles.Trading.Mode.trading_view_signals_trading_mode.tradingview_signal_to_dsl_translator as tradingview_signal_to_dsl_translator
import tentacles.Trading.Mode.trading_view_signals_trading_mode.trading_view_signals_trading as trading_view_signals_trading


@pytest.fixture
def exchange_manager():
    return mock.Mock()


@pytest.fixture
def translator_cls():
    return tradingview_signal_to_dsl_translator.TradingViewSignalToDSLTranslator


def _make_operator_param(name, required=True):
    return dsl_interpreter.OperatorParameter(
        name=name, description=f"{name} param", required=required, type=str
    )


class TestMapOtherParamsToDsl:
    def test_maps_known_tradingview_keys_to_dsl(self, translator_cls):
        param_symbol = _make_operator_param("symbol")
        param_amount = _make_operator_param("amount")
        operator_params = [param_symbol, param_amount]
        other_params = {
            trading_view_signals_trading.TradingViewSignalsTradingMode.SYMBOL_KEY: "BTC/USDT",
            trading_view_signals_trading.TradingViewSignalsTradingMode.VOLUME_KEY: 0.01,
        }
        result = translator_cls._map_other_params_to_dsl(other_params, operator_params)
        assert result == {"symbol": "BTC/USDT", "amount": 0.01}

    def test_skips_non_string_keys(self, translator_cls):
        param_symbol = _make_operator_param("symbol")
        operator_params = [param_symbol]
        other_params = {123: "value", trading_view_signals_trading.TradingViewSignalsTradingMode.SYMBOL_KEY: "BTC/USDT"}
        result = translator_cls._map_other_params_to_dsl(other_params, operator_params)
        assert result == {"symbol": "BTC/USDT"}

    def test_uses_lowercase_for_unknown_keys_matching_operator_param(self, translator_cls):
        param_unknown = _make_operator_param("custom_param")
        operator_params = [param_unknown]
        other_params = {"CUSTOM_PARAM": "value"}
        result = translator_cls._map_other_params_to_dsl(other_params, operator_params)
        assert result == {"custom_param": "value"}

    def test_collects_param_prefixed_keys_into_params_dict(self, translator_cls):
        param_symbol = _make_operator_param("symbol")
        param_params = _make_operator_param("params", required=False)
        operator_params = [param_symbol, param_params]
        prefix = trading_view_signals_trading.TradingViewSignalsTradingMode.PARAM_PREFIX_KEY
        other_params = {
            f"{prefix}custom_key": "custom_value",
            f"{prefix}another": 42,
        }
        result = translator_cls._map_other_params_to_dsl(other_params, operator_params)
        assert result == {"params": {"custom_key": "custom_value", "another": 42}}

    def test_ignores_param_prefixed_when_params_not_in_operator(self, translator_cls):
        param_symbol = _make_operator_param("symbol")
        operator_params = [param_symbol]
        prefix = trading_view_signals_trading.TradingViewSignalsTradingMode.PARAM_PREFIX_KEY
        other_params = {f"{prefix}custom_key": "custom_value"}
        result = translator_cls._map_other_params_to_dsl(other_params, operator_params)
        assert result == {}


class TestGetDslSignalKeywordAndParams:
    mode = trading_view_signals_trading.TradingViewSignalsTradingMode

    def test_raises_when_signal_key_missing(self, translator_cls):
        parsed_data = {}
        with pytest.raises(trading_errors.InvalidArgumentError) as exc_info:
            translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert self.mode.SIGNAL_KEY in str(exc_info.value)

    def test_buy_signal_returns_market_keyword_with_side_buy(self, translator_cls):
        parsed_data = {self.mode.SIGNAL_KEY: "buy"}
        keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword == "market"
        assert params["side"] == "buy"

    def test_buy_signal_with_explicit_order_type(self, translator_cls):
        parsed_data = {
            self.mode.SIGNAL_KEY: "buy",
            self.mode.ORDER_TYPE_SIGNAL: "limit",
        }
        keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword == "limit"
        assert params["side"] == "buy"

    def test_sell_signal_returns_market_keyword_with_side_sell(self, translator_cls):
        parsed_data = {self.mode.SIGNAL_KEY: "sell"}
        keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword == "market"
        assert params["side"] == "sell"

    def test_sell_signal_with_explicit_order_type(self, translator_cls):
        parsed_data = {
            self.mode.SIGNAL_KEY: "sell",
            self.mode.ORDER_TYPE_SIGNAL: "limit",
        }
        keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword == "limit"
        assert params["side"] == "sell"

    def test_stop_order_type_maps_to_stop_loss(self, translator_cls):
        parsed_data = {
            self.mode.SIGNAL_KEY: "buy",
            self.mode.ORDER_TYPE_SIGNAL: "stop",
        }
        keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword == "stop_loss"
        assert params["side"] == "buy"

    def test_default_order_type_is_limit_when_price_present(self, translator_cls):
        parsed_data = {
            self.mode.SIGNAL_KEY: "buy",
            self.mode.PRICE_KEY: 50000.0,
        }
        keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword == "limit"
        assert params["side"] == "buy"

    def test_cancel_signal_returns_cancel_order_keyword(self, translator_cls):
        parsed_data = {self.mode.SIGNAL_KEY: "cancel"}
        keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword == "cancel_order"
        assert params == {}

    def test_unknown_signal_returns_none_keyword(self, translator_cls):
        parsed_data = {self.mode.SIGNAL_KEY: "unknown_signal"}
        keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword is None
        assert params == {}

    def test_signal_case_insensitive(self, translator_cls):
        parsed_data = {self.mode.SIGNAL_KEY: "BUY"}
        keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword == "market"
        assert params["side"] == "buy"

        parsed_data = {self.mode.SIGNAL_KEY: "SelL"}
        keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword == "market"
        assert params["side"] == "sell"

    def test_withdraw_funds_raises_when_disabled(self, translator_cls):
        parsed_data = {self.mode.SIGNAL_KEY: self.mode.WITHDRAW_FUNDS_SIGNAL}
        with mock.patch.object(trading_constants, "ALLOW_FUNDS_TRANSFER", False):
            with pytest.raises(trading_errors.DisabledFundsTransferError):
                translator_cls._get_dsl_signal_keyword_and_params(parsed_data)

    def test_withdraw_funds_returns_withdraw_when_enabled(self, translator_cls):
        parsed_data = {self.mode.SIGNAL_KEY: self.mode.WITHDRAW_FUNDS_SIGNAL}
        with mock.patch.object(trading_constants, "ALLOW_FUNDS_TRANSFER", True):
            keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword == "withdraw"
        assert params == {}

    def test_transfer_funds_raises_when_disabled(self, translator_cls):
        parsed_data = {self.mode.SIGNAL_KEY: self.mode.TRANSFER_FUNDS_SIGNAL}
        with mock.patch.object(trading_constants, "ALLOW_FUNDS_TRANSFER", False):
            with pytest.raises(trading_errors.DisabledFundsTransferError):
                translator_cls._get_dsl_signal_keyword_and_params(parsed_data)

    def test_transfer_funds_returns_blockchain_wallet_transfer_when_enabled(self, translator_cls):
        parsed_data = {self.mode.SIGNAL_KEY: self.mode.TRANSFER_FUNDS_SIGNAL}
        with mock.patch.object(trading_constants, "ALLOW_FUNDS_TRANSFER", True):
            keyword, params = translator_cls._get_dsl_signal_keyword_and_params(parsed_data)
        assert keyword == "blockchain_wallet_transfer"
        assert params == {}


class TestAdaptSpecialFormatValuesForParam:
    def test_take_profit_prices_list_unchanged(self, translator_cls):
        dsl_param = trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM[
            trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY
        ]
        value = [100.0, 101.0]
        assert translator_cls._adapt_special_format_values_for_param(dsl_param, value) == value

    def test_take_profit_prices_scalar_to_list(self, translator_cls):
        dsl_param = trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM[
            trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY
        ]
        assert translator_cls._adapt_special_format_values_for_param(dsl_param, 100.0) == [100.0]
        assert translator_cls._adapt_special_format_values_for_param(dsl_param, "101") == ["101"]

    def test_take_profit_prices_empty_scalar_to_empty_list(self, translator_cls):
        dsl_param = trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM[
            trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY
        ]
        assert translator_cls._adapt_special_format_values_for_param(dsl_param, "") == []
        assert translator_cls._adapt_special_format_values_for_param(dsl_param, 0) == []

    def test_take_profit_volume_percents_list_to_float_list(self, translator_cls):
        dsl_param = trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM[
            trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_VOLUME_RATIO_KEY
        ]
        result = translator_cls._adapt_special_format_values_for_param(dsl_param, ["50", "50"])
        assert result == [50.0, 50.0]

    def test_take_profit_volume_percents_scalar_to_list(self, translator_cls):
        dsl_param = trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM[
            trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_VOLUME_RATIO_KEY
        ]
        result = translator_cls._adapt_special_format_values_for_param(dsl_param, "100")
        assert result == [100.0]

    def test_exchange_order_ids_string_to_list(self, translator_cls):
        dsl_param = trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM[
            trading_view_signals_trading.TradingViewSignalsTradingMode.EXCHANGE_ORDER_IDS
        ]
        result = translator_cls._adapt_special_format_values_for_param(dsl_param, "id1, id2 , id3")
        assert result == ["id1", "id2", "id3"]

    def test_other_param_unchanged(self, translator_cls):
        result = translator_cls._adapt_special_format_values_for_param("other_param", "value")
        assert result == "value"


class TestGetOperatorClass:
    def test_returns_operator_when_keyword_matches(self, translator_cls):
        mock_op = mock.Mock()
        mock_op.get_name.return_value = "market"
        with mock.patch.object(translator_cls, "_get_allowed_keywords", return_value=[mock_op]):
            result = translator_cls._get_operator_class("market")
        assert result is mock_op

    def test_returns_none_when_keyword_not_found(self, translator_cls):
        mock_op = mock.Mock()
        mock_op.get_name.return_value = "market"
        with mock.patch.object(translator_cls, "_get_allowed_keywords", return_value=[mock_op]):
            result = translator_cls._get_operator_class("unknown")
        assert result is None


class TestCollectNumberedListParamValues:
    def test_collects_numbered_keys_in_order(self, translator_cls):
        params = {
            "TAKE_PROFIT_PRICE_2": 102.0,
            "TAKE_PROFIT_PRICE_1": 101.0,
            "TAKE_PROFIT_PRICE_3": 103.0,
        }
        result = translator_cls._collect_numbered_list_param_values(
            params, trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY
        )
        assert result == [101.0, 102.0, 103.0]

    def test_standalone_takes_precedence_with_numbered(self, translator_cls):
        params = {
            "TAKE_PROFIT_PRICE": 99.0,
            "TAKE_PROFIT_PRICE_1": 101.0,
        }
        result = translator_cls._collect_numbered_list_param_values(
            params, trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY
        )
        assert result == [99.0, 101.0]

    def test_skips_invalid_suffix(self, translator_cls):
        params = {
            "TAKE_PROFIT_PRICE_1": 101.0,
            "TAKE_PROFIT_PRICE_abc": 999.0,
        }
        result = translator_cls._collect_numbered_list_param_values(
            params, trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY
        )
        assert result == [101.0]

    def test_standalone_empty_returns_numbered_only(self, translator_cls):
        params = {
            "TAKE_PROFIT_PRICE": "",
            "TAKE_PROFIT_PRICE_1": 101.0,
        }
        result = translator_cls._collect_numbered_list_param_values(
            params, trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY
        )
        assert result == [101.0]


class TestPreProcessSpecialParams:
    def test_removes_numbered_take_profit_keys_from_result(self, translator_cls):
        operator_class = mock.Mock()
        operator_class.get_name.return_value = "limit"
        params = {
            trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY: 100.0,
            f"{trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY}_1": 101.0,
        }
        result = translator_cls._pre_process_special_params(operator_class, params)
        assert result == {
            trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY: [100.0, 101.0]
        }

    def test_stop_loss_maps_stop_price_to_price(self, translator_cls):
        operator_class = mock.Mock()
        operator_class.get_name.return_value = "stop_loss"
        params = {
            trading_view_signals_trading.TradingViewSignalsTradingMode.STOP_PRICE_KEY: 50000.0,
        }
        result = translator_cls._pre_process_special_params(operator_class, params)
        assert result == {
            trading_view_signals_trading.TradingViewSignalsTradingMode.PRICE_KEY: 50000.0
        }


class TestResolveOperatorParams:
    def test_merges_params_and_other_params(self, translator_cls):
        operator_class = mock.Mock()
        param_side = _make_operator_param("side")
        param_symbol = _make_operator_param("symbol")
        param_amount = _make_operator_param("amount")
        operator_class.get_parameters.return_value = [param_side, param_symbol, param_amount]
        operator_class.get_name.return_value = "market"
        params = {"side": "buy", "symbol": "BTC/USDT"}
        other_params = {trading_view_signals_trading.TradingViewSignalsTradingMode.VOLUME_KEY: 0.01}
        result = translator_cls._resolve_operator_params(operator_class, params, other_params)
        assert result == ["'buy'", "'BTC/USDT'", "0.01"]


class TestTranslateSignal:
    def test_returns_none_for_empty_keyword(self, translator_cls):
        parsed_data_no_keyword = {trading_view_signals_trading.TradingViewSignalsTradingMode.SIGNAL_KEY: "invalid"}
        assert translator_cls.translate_signal(parsed_data_no_keyword) == "None"
        parsed_data_empty_order_type = {
            trading_view_signals_trading.TradingViewSignalsTradingMode.SIGNAL_KEY: "buy",
            trading_view_signals_trading.TradingViewSignalsTradingMode.ORDER_TYPE_SIGNAL: "",
        }
        assert translator_cls.translate_signal(parsed_data_empty_order_type) == "None"

    def test_returns_none_for_unknown_keyword(self, translator_cls):
        parsed_data = {
            trading_view_signals_trading.TradingViewSignalsTradingMode.SIGNAL_KEY: "buy",
            trading_view_signals_trading.TradingViewSignalsTradingMode.ORDER_TYPE_SIGNAL: "unknown_op",
        }
        with mock.patch.object(translator_cls, "_get_operator_class", return_value=None):
            result = translator_cls.translate_signal(parsed_data)
        assert result == "None"

    def test_returns_dsl_expression_for_known_operator(self, translator_cls):
        parsed_data = {trading_view_signals_trading.TradingViewSignalsTradingMode.SIGNAL_KEY: "buy"}
        mock_op = mock.Mock()
        mock_op.get_name.return_value = "market"
        with mock.patch.object(translator_cls, "_get_operator_class", return_value=mock_op):
            with mock.patch.object(
                translator_cls, "_resolve_operator_params", return_value=["'buy'", "'BTC/USDT'", "0.01"]
            ):
                result = translator_cls.translate_signal(parsed_data)
        assert result == "market('buy', 'BTC/USDT', 0.01)"
