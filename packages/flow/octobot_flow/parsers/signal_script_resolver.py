#  Drakkar-Software OctoBot-Flow
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
#  OctoBot-Flow is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.

import copy
import json
import typing

import octobot_trading.enums as trading_enums

import octobot_flow.entities.signals.signal_exchange_context as signal_exchange_context_module
import octobot_flow.errors


def _trading_view_signals_trading():
    # avoid hard tentacles dependencies
    import tentacles.Trading.Mode.trading_view_signals_trading_mode.trading_view_signals_trading as trading_view_signals_trading

    return trading_view_signals_trading


def _tradingview_signal_to_dsl_translator():
    # avoid hard tentacles dependencies
    import tentacles.Trading.Mode.trading_view_signals_trading_mode.tradingview_signal_to_dsl_translator as tradingview_signal_to_dsl_translator

    return tradingview_signal_to_dsl_translator


def signal_key() -> str:
    return _trading_view_signals_trading().TradingViewSignalsTradingMode.SIGNAL_KEY


def _exchange_key() -> str:
    return _trading_view_signals_trading().TradingViewSignalsTradingMode.EXCHANGE_KEY


def _symbol_key() -> str:
    return _trading_view_signals_trading().TradingViewSignalsTradingMode.SYMBOL_KEY


def _looks_like_signal_param_val(script: str) -> bool:
    separators = _trading_view_signals_trading().TradingViewSignalsTradingMode.PARAM_SEPARATORS
    splittable_data = script
    final_split_char = separators[0]
    for split_char in separators[1:]:
        splittable_data = splittable_data.replace(split_char, final_split_char)
    for line in splittable_data.split(final_split_char):
        if line.strip() and "=" in line:
            return True
    return False


def _looks_like_json_object(script: str) -> bool:
    return script.strip().startswith("{")


def _prepare_signal_parsed_data(
    parsed_data: dict,
    *,
    ignore_exchange_key: bool,
) -> dict:
    prepared_data = copy.deepcopy(parsed_data)
    if ignore_exchange_key:
        prepared_data.pop(_exchange_key(), None)
    return prepared_data


def parse_signal_param_val_string(
    script: str,
    exchange_context: signal_exchange_context_module.SignalExchangeContext,
) -> dict:
    parse_errors: list[str] = []
    parsed_data = _trading_view_signals_trading().TradingViewSignalsTradingMode.parse_signal_data(
        script,
        exchange_context.exchange_name,
        exchange_context.exchange_type,
        exchange_context.reference_market,
        parse_errors,
    )
    if parse_errors:
        raise octobot_flow.errors.InvalidAutomationActionError(
            f"Invalid signal param=val format: {'; '.join(parse_errors)}"
        )
    return _prepare_signal_parsed_data(
        parsed_data,
        ignore_exchange_key=exchange_context.ignore_exchange_key,
    )


def _apply_symbol_adaptation(
    parsed_data: dict,
    exchange_context: signal_exchange_context_module.SignalExchangeContext,
) -> dict:
    adapted_data = copy.deepcopy(parsed_data)
    _trading_view_signals_trading().TradingViewSignalsTradingMode._adapt_symbol(
        adapted_data,
        exchange_context.exchange_name,
        exchange_context.exchange_type,
        exchange_context.reference_market,
    )
    return adapted_data


def _validate_signal_parsed_data(parsed_data: dict) -> None:
    if _symbol_key() not in parsed_data:
        raise octobot_flow.errors.InvalidAutomationActionError(
            f"Signal is missing {_symbol_key()!r}: {parsed_data}"
        )


def translate_signal_parsed_data(parsed_data: dict) -> str:
    tradingview_signal_to_dsl_translator = _tradingview_signal_to_dsl_translator()
    dsl_script = tradingview_signal_to_dsl_translator.TradingViewSignalToDSLTranslator.translate_signal(
        parsed_data
    )
    if dsl_script == tradingview_signal_to_dsl_translator.UNKNOWN_SIGNAL_RESULT:
        raise octobot_flow.errors.InvalidAutomationActionError(
            f"Invalid signal: {parsed_data}"
        )
    return dsl_script


def _translate_signal_dict(
    parsed_data: dict,
    *,
    ignore_exchange_key: bool,
    exchange_context: signal_exchange_context_module.SignalExchangeContext,
) -> str:
    prepared_data = _prepare_signal_parsed_data(parsed_data, ignore_exchange_key=ignore_exchange_key)
    if signal_key() not in prepared_data:
        raise octobot_flow.errors.InvalidAutomationActionError(
            f"Signal dict is missing {signal_key()!r}: {parsed_data}"
        )
    adapted_data = _apply_symbol_adaptation(prepared_data, exchange_context)
    _validate_signal_parsed_data(adapted_data)
    return translate_signal_parsed_data(adapted_data)


def resolve_signal_script(
    script: typing.Any,
    *,
    exchange_name: typing.Optional[str] = None,
    exchange_type: typing.Optional[trading_enums.ExchangeTypes] = None,
    reference_market: typing.Optional[str] = None,
    ignore_exchange_key: bool = True,
) -> str:
    exchange_context = signal_exchange_context_module.SignalExchangeContext(
        exchange_name=exchange_name,
        exchange_type=exchange_type,
        reference_market=reference_market,
        ignore_exchange_key=ignore_exchange_key,
    )
    if isinstance(script, dict):
        return _translate_signal_dict(
            script,
            ignore_exchange_key=ignore_exchange_key,
            exchange_context=exchange_context,
        )

    if not isinstance(script, str):
        raise octobot_flow.errors.InvalidAutomationActionError(
            f"Signal script must be a string or signal dict, got {type(script).__name__}"
        )

    stripped_script = script.strip()
    if not stripped_script:
        raise octobot_flow.errors.InvalidAutomationActionError("Signal script must not be empty")

    if _looks_like_signal_param_val(script):
        parsed_data = parse_signal_param_val_string(script, exchange_context)
        if signal_key() not in parsed_data:
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"Signal param=val string is missing {signal_key()!r}: {script!r}"
            )
        _validate_signal_parsed_data(parsed_data)
        return translate_signal_parsed_data(parsed_data)

    if _looks_like_json_object(script):
        try:
            loaded_payload = json.loads(script)
        except json.JSONDecodeError as error:
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"Invalid JSON signal: {error}"
            ) from error
        if not isinstance(loaded_payload, dict):
            raise octobot_flow.errors.InvalidAutomationActionError(
                f"JSON signal must be an object, got {type(loaded_payload).__name__}"
            )
        if signal_key() in loaded_payload:
            return _translate_signal_dict(
                loaded_payload,
                ignore_exchange_key=ignore_exchange_key,
                exchange_context=exchange_context,
            )

    return script
