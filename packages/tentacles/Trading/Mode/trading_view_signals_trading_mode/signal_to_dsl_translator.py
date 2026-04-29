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

import json
import typing

import octobot_commons.dsl_interpreter as dsl_interpreter
import tentacles.Meta.DSL_operators as dsl_operators
import octobot_trading.exchanges as trading_exchanges

TRADING_VIEW_TO_DSL_PARAM = {
    "SYMBOL": "symbol",
    "VOLUME": "amount",
    "PRICE": "price",
    "REDUCE_ONLY": "reduce_only",
    "TAG": "tag",
    "STOP_PRICE": "stop_loss_price",
    "TAKE_PROFIT_PRICE": "take_profit_prices",
    "TAKE_PROFIT_VOLUME_RATIO": "take_profit_volume_percents",
    "EXCHANGE_ORDER_IDS": "exchange_order_ids",
    "SIDE": "side",
    "TRAILING_PROFILE": "trailing_profile",
    "CANCEL_POLICY": "cancel_policy",
    "CANCEL_POLICY_PARAMS": "cancel_policy_params",
}

PARAM_PREFIX = "PARAM_"


class SignalToDSLTranslator:
    def __init__(self, exchange_manager: trading_exchanges.ExchangeManager):
        self.exchange_manager = exchange_manager

    def _map_other_params_to_dsl(
        self, other_params: dict[str, typing.Any], operator_params: list[dsl_interpreter.OperatorParameter]
    ) -> dict[str, typing.Any]:
        operator_param_names = {p.name for p in operator_params}
        dsl_params = {}
        params_dict = {}
        for key, value in other_params.items():
            if not isinstance(key, str):
                continue
            dsl_key = TRADING_VIEW_TO_DSL_PARAM.get(key, key.lower())
            if key.startswith(PARAM_PREFIX):
                param_name = key[len(PARAM_PREFIX):]
                params_dict[param_name] = value
            elif dsl_key in operator_param_names:
                dsl_params[dsl_key] = value
        if params_dict and "params" in operator_param_names:
            dsl_params["params"] = params_dict
        return dsl_params

    def _format_value(self, value: typing.Any, param_type: type) -> str:
        if value is None:
            return "None"
        if isinstance(value, bool):
            return "True" if value else "False"
        if isinstance(value, (int, float)):
            return repr(value)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return repr(parsed)
                if isinstance(parsed, dict):
                    return repr(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
            return repr(value)
        if isinstance(value, list):
            return repr(value)
        if isinstance(value, dict):
            return repr(value)
        return repr(value)

    def _adapt_special_format_values_for_param(
        self, value: typing.Any, param_name: str, param_type: type
    ) -> typing.Any:
        if param_name == "take_profit_prices":
            if isinstance(value, list):
                return value
            if isinstance(value, (str, int, float)):
                return [value] if value else []
        if param_name == "take_profit_volume_percents":
            if isinstance(value, list):
                return [float(v) for v in value]
            if isinstance(value, (str, int, float)):
                return [float(value)] if value else []
        if param_name == "exchange_order_ids" and isinstance(value, str):
            return [oid.strip() for oid in value.split(",") if oid.strip()]
        return value
    
    def _get_operator_class(
        self,
        keyword: str,
    ) -> typing.Optional[dsl_interpreter.Operator]:
        allowed_operators = self._get_allowed_keywords()
        for op in allowed_operators:
            if op.get_name() == keyword:
                return op
        return None

    def _collect_list_param_values(
        self, params: dict[str, typing.Any], base_key: str
    ) -> list[typing.Any]:
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

    def _pre_process_params(
        self,
        operator_class: dsl_interpreter.Operator,
        params: dict[str, typing.Any]
    ) -> dict[str, typing.Any]:
        result = {
            k: v 
            for k, v in params.items() 
            if not isinstance(k, str) 
            or not (
                k.startswith("TAKE_PROFIT_PRICE_") or k.startswith("TAKE_PROFIT_VOLUME_RATIO_")
            )
        }
        if operator_class.get_name() == "stop_loss" and "STOP_PRICE" in params:
            # special casee for stop loss price: used as price when creating a stop loss order
            result["PRICE"] = params["STOP_PRICE"]
            result.pop("STOP_PRICE")
        for base_key in ("TAKE_PROFIT_PRICE", "TAKE_PROFIT_VOLUME_RATIO"):
            if base_key in params or any(
                isinstance(k, str) and k.startswith(f"{base_key}_")
                for k in params
            ):
                values = self._collect_list_param_values(params, base_key)
                if values:
                    result[base_key] = values
                elif base_key in params:
                    result[base_key] = [params[base_key]] if params[base_key] not in (None, "") else []
        return result

    def _resolve_operator_params(
        self,
        operator_class: dsl_interpreter.Operator,
        params: dict[str, typing.Any],
        other_params: dict[str, typing.Any]
    ) -> list[str]:
        operator_params = operator_class.get_parameters()
        adapted_other = self._pre_process_params(operator_class, other_params)
        mapped_other = self._map_other_params_to_dsl(adapted_other, operator_params)
        merged = dict(params)
        for dsl_key, value in mapped_other.items():
            if dsl_key not in merged:
                merged[dsl_key] = value
        required_params = [p for p in operator_params if p.required]
        optional_params = [p for p in operator_params if not p.required]
        positional_parts = []
        keyword_parts = []
        for param_def in required_params:
            name = param_def.name
            if name in merged:
                value = merged[name]
                value = self._adapt_special_format_values_for_param(value, name, param_def.type)
                positional_parts.append(
                    self._format_value(value, param_def.type)
                )
        for param_def in optional_params:
            name = param_def.name
            if name in merged:
                value = merged[name]
                value = self._adapt_special_format_values_for_param(value, name, param_def.type)
                keyword_parts.append(f"{name}={self._format_value(value, param_def.type)}")
        return positional_parts + keyword_parts

    def translate_signal(
        self, keyword: typing.Optional[str], params: dict[str, typing.Any], other_params: dict[str, typing.Any]
    ) -> str:
        if not keyword:
            return "None"
        if operator_class := self._get_operator_class(keyword):
            all_params = self._resolve_operator_params(operator_class, params, other_params)
            return f"{operator_class.get_name()}({', '.join(all_params)})"
        return "None"


    def _get_allowed_keywords(self) -> list[dsl_interpreter.Operator]:
        return (
            dsl_operators.create_create_order_operators(self.exchange_manager) +
            dsl_operators.create_cancel_order_operators(self.exchange_manager) +
            dsl_operators.create_blockchain_wallet_operators(self.exchange_manager) +
            dsl_operators.create_portfolio_operators(self.exchange_manager)
        ) # type: ignore
