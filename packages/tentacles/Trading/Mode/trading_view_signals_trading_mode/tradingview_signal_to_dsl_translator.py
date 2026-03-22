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
import typing

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors as commons_errors
import tentacles.Meta.DSL_operators as dsl_operators
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.constants as trading_constants
import octobot_trading.errors as trading_errors
import tentacles.Trading.Mode.trading_view_signals_trading_mode.trading_view_signals_trading as trading_view_signals_trading


FREE_PARAMS_NAME = "params"
UNKNOWN_SIGNAL_RESULT = "None"


class TradingViewSignalToDSLTranslator:
    """
    Translates TradingView signal parameters to DSL parameters.
    Handles special cases for some parameters (ex: take profit prices, exchange order ids, ...).
    """

    @classmethod
    def _get_dsl_signal_keyword_and_params(cls, parsed_data: dict) -> tuple[typing.Optional[str], dict[str, typing.Any]]:
        keyword = None
        params = {}
        try:
            signal = parsed_data[trading_view_signals_trading.TradingViewSignalsTradingMode.SIGNAL_KEY].casefold()
        except KeyError:
            raise trading_errors.InvalidArgumentError(
                f"{trading_view_signals_trading.TradingViewSignalsTradingMode.SIGNAL_KEY} key "
                f"not found in parsed data: {parsed_data}"
            )
        price = parsed_data.get(trading_view_signals_trading.TradingViewSignalsTradingMode.PRICE_KEY)
        default_order_type = "market" if price is None else "limit"
        order_type = parsed_data.get(trading_view_signals_trading.TradingViewSignalsTradingMode.ORDER_TYPE_SIGNAL, default_order_type).casefold()
        if order_type == trading_view_signals_trading.TradingViewSignalsTradingMode.STOP_SIGNAL.lower():
            order_type = "stop_loss"
        if signal == trading_view_signals_trading.TradingViewSignalsTradingMode.SELL_SIGNAL:
            keyword = order_type
            params[
                trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM[trading_view_signals_trading.TradingViewSignalsTradingMode.SIDE_PARAM_KEY]
            ] = "sell"
        elif signal == trading_view_signals_trading.TradingViewSignalsTradingMode.BUY_SIGNAL:
            keyword = order_type
            params[
                trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM[trading_view_signals_trading.TradingViewSignalsTradingMode.SIDE_PARAM_KEY]
            ] = "buy"
        elif signal == trading_view_signals_trading.TradingViewSignalsTradingMode.CANCEL_SIGNAL:
            keyword = "cancel_order"
        elif signal == trading_view_signals_trading.TradingViewSignalsTradingMode.WITHDRAW_FUNDS_SIGNAL:
            if not trading_constants.ALLOW_FUNDS_TRANSFER:
                raise trading_errors.DisabledFundsTransferError(
                    "Withdraw funds signal is not allowed when ALLOW_FUNDS_TRANSFER is disabled"
                )
            keyword = "withdraw"
        elif signal == trading_view_signals_trading.TradingViewSignalsTradingMode.TRANSFER_FUNDS_SIGNAL:
            if not trading_constants.ALLOW_FUNDS_TRANSFER:
                raise trading_errors.DisabledFundsTransferError(
                    "Transfer funds signal is not allowed when ALLOW_FUNDS_TRANSFER is disabled"
                )
            keyword = "blockchain_wallet_transfer"
        return keyword, params

    @classmethod
    def _map_other_params_to_dsl(
        cls, other_params: dict[str, typing.Any], operator_params: list[dsl_interpreter.OperatorParameter]
    ) -> dict[str, typing.Any]:
        operator_param_names = {p.name for p in operator_params}
        dsl_params = {}
        params_dict = {}
        for key, value in other_params.items():
            if not isinstance(key, str):
                continue
            dsl_key = trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM.get(key, key.lower())
            if key.startswith(trading_view_signals_trading.TradingViewSignalsTradingMode.PARAM_PREFIX_KEY):
                param_name = key[len(trading_view_signals_trading.TradingViewSignalsTradingMode.PARAM_PREFIX_KEY):]
                params_dict[param_name] = value
            elif dsl_key in operator_param_names:
                dsl_params[dsl_key] = value
        if params_dict and FREE_PARAMS_NAME in operator_param_names:
            dsl_params[FREE_PARAMS_NAME] = params_dict
        return dsl_params

    @classmethod
    def _adapt_special_format_values_for_param(
        cls, param_name: str, value: typing.Any
    ) -> typing.Any:
        if param_name == trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM[trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY]:
            if isinstance(value, list):
                return value
            if isinstance(value, (str, int, float)):
                return [value] if value else []
        if param_name == trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM[trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_VOLUME_RATIO_KEY]:
            if isinstance(value, list):
                return [float(v) for v in value]
            if isinstance(value, (str, int, float)):
                return [float(value)] if value else []
        if param_name == trading_view_signals_trading.TradingViewSignalsTradingMode.TRADINGVIEW_TO_DSL_PARAM[trading_view_signals_trading.TradingViewSignalsTradingMode.EXCHANGE_ORDER_IDS] and isinstance(value, str):
            return [oid.strip() for oid in value.split(",") if oid.strip()]
        return value
    
    @classmethod
    def _get_operator_class(cls, keyword: str) -> typing.Optional[dsl_interpreter.Operator]:
        allowed_operators = cls._get_allowed_keywords()
        for op in allowed_operators:
            if op.get_name() == keyword:
                return op
        return None

    @classmethod
    def _collect_numbered_list_param_values(
        cls, params: dict[str, typing.Any], base_key: str
    ) -> list[typing.Any]:
        # collect numbered list values from params, ex: TAKE_PROFIT_PRICE_1, TAKE_PROFIT_PRICE_2, ...
        standalone = params.get(base_key)
        numbered: list[tuple[int, typing.Any]] = []
        prefix = f"{base_key}_"
        for key, value in params.items():
            if not isinstance(key, str) or not key.startswith(prefix):
                continue
            suffix = key[len(prefix):]
            try:
                index = int(suffix)
                numbered.append((index, value))
            except ValueError:
                continue
        numbered.sort(key=lambda item: item[0])
        if standalone is not None and standalone != "":
            return [standalone] + [v for _, v in numbered]
        return [v for _, v in numbered]

    @classmethod
    def _pre_process_special_params(
        cls,
        operator_class: dsl_interpreter.Operator,
        params: dict[str, typing.Any]
    ) -> dict[str, typing.Any]:
        result = {
            k: v 
            for k, v in params.items() 
            if not isinstance(k, str) 
            or not (
                k.startswith(
                    f"{trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY}_"
                ) or k.startswith(
                    f"{trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_VOLUME_RATIO_KEY}_"
                )
            )
        }
        if operator_class.get_name() == "stop_loss" and trading_view_signals_trading.TradingViewSignalsTradingMode.STOP_PRICE_KEY in params:
            # special casee for stop loss price: used as price when creating a stop loss order
            result[trading_view_signals_trading.TradingViewSignalsTradingMode.PRICE_KEY] = params[trading_view_signals_trading.TradingViewSignalsTradingMode.STOP_PRICE_KEY]
            result.pop(trading_view_signals_trading.TradingViewSignalsTradingMode.STOP_PRICE_KEY)
        for base_key in (
            trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_PRICE_KEY,
            trading_view_signals_trading.TradingViewSignalsTradingMode.TAKE_PROFIT_VOLUME_RATIO_KEY,
        ):
            if base_key in params or any(
                isinstance(k, str) and k.startswith(f"{base_key}_")
                for k in params
            ):
                values = cls._collect_numbered_list_param_values(params, base_key)
                if values:
                    result[base_key] = values
                elif base_key in params:
                    result[base_key] = [params[base_key]] if params[base_key] not in (None, "") else []
        return result

    @classmethod
    def _resolve_operator_params(
        cls,
        operator_class: dsl_interpreter.Operator,
        params: dict[str, typing.Any],
        other_params: dict[str, typing.Any]
    ) -> list[str]:
        operator_params = operator_class.get_parameters()
        adapted_other = cls._pre_process_special_params(operator_class, other_params)
        mapped_other = cls._map_other_params_to_dsl(adapted_other, operator_params)
        merged = dict(params)
        for dsl_key, value in mapped_other.items():
            if dsl_key not in merged:
                merged[dsl_key] = value
        # adapt special format values when needed
        merged = {
            name: cls._adapt_special_format_values_for_param(name, value)
            for name, value in merged.items()
        }
        return dsl_interpreter.resove_operator_params(operator_class, merged)

    @classmethod
    def translate_signal(cls, parsed_data: dict) -> str:
        keyword, params = cls._get_dsl_signal_keyword_and_params(parsed_data)
        if not keyword:
            return UNKNOWN_SIGNAL_RESULT
        if operator_class := cls._get_operator_class(keyword):
            all_params = cls._resolve_operator_params(operator_class, params, parsed_data)
            return f"{operator_class.get_name()}({', '.join(all_params)})"
        return UNKNOWN_SIGNAL_RESULT

    @classmethod
    def _get_allowed_keywords(cls) -> list[dsl_interpreter.Operator]:
        return (
            dsl_operators.create_create_order_operators(None) +
            dsl_operators.create_cancel_order_operators(None) +
            dsl_operators.create_blockchain_wallet_operators(None) +
            dsl_operators.create_portfolio_operators(None)
        )  # type: ignore
