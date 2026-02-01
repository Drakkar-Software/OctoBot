# pylint: disable=missing-class-docstring,missing-function-docstring
#  Drakkar-Software OctoBot-Commons
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
import tulipy
import numpy as np

import octobot_commons.errors
import tentacles.Meta.DSL_operators.ta_operators.ta_operator as ta_operator
import octobot_commons.dsl_interpreter as dsl_interpreter


def _to_numpy_array(data):
    if isinstance(data, list):
        return np.array(data, dtype=np.float64)
    elif isinstance(data, tuple):
        return np.array(list(data), dtype=np.float64)
    elif isinstance(data, np.ndarray):
        if data.dtype != np.float64:
            return data.astype(np.float64)
        return data
    else:
        raise octobot_commons.errors.InvalidParametersError(f"Unsupported data type: {type(data)}")


def _to_int(value):
    if isinstance(value, int):
        return value
    elif isinstance(value, float):
        return int(value)
    else:
        raise octobot_commons.errors.InvalidParametersError(f"Unsupported value type: {type(value)}")


def converted_tulipy_error(f):
    def converted_tulipy_error_wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except tulipy.InvalidOptionError as err:
            raise TypeError(
                f"Invalid technical indicator parameter - {err.__class__.__name__}"
            ) from err
    return converted_tulipy_error_wrapper


class RSIOperator(ta_operator.TAOperator):
    DESCRIPTION = "Returns the Relative Strength Index (RSI) of the given array of numbers"
    EXAMPLE = "rsi([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110], 14)"

    @staticmethod
    def get_name() -> str:
        return "rsi"

    @staticmethod
    def get_parameters() -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="data", description="the data to compute the RSI on", required=True, type=list),
            dsl_interpreter.OperatorParameter(name="period", description="the period to use for the RSI", required=True, type=int),
        ]

    @converted_tulipy_error
    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        operands = self.get_computed_parameters()
        return list(tulipy.rsi(_to_numpy_array(operands[0]), period=_to_int(operands[1])))


class MACDOperator(ta_operator.TAOperator):
    DESCRIPTION = "Returns the Moving Average Convergence Divergence (MACD) of the given array of numbers"
    EXAMPLE = "macd(close('BTC/USDT', '1h'), 12, 26, 9)"

    @staticmethod
    def get_name() -> str:
        return "macd"

    @staticmethod
    def get_parameters() -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="data", description="the data to compute the MACD on", required=True, type=list),
            dsl_interpreter.OperatorParameter(name="short_period", description="the short period to use for the MACD", required=True, type=int),
            dsl_interpreter.OperatorParameter(name="long_period", description="the long period to use for the MACD", required=True, type=int),
            dsl_interpreter.OperatorParameter(name="signal_period", description="the signal period to use for the MACD", required=True, type=int),
        ]

    @converted_tulipy_error
    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        operands = self.get_computed_parameters()
        macd, macd_signal, macd_hist = tulipy.macd(
            _to_numpy_array(operands[0]), short_period=_to_int(operands[1]), long_period=_to_int(operands[2]), signal_period=_to_int(operands[3])
        )
        return list(macd_hist)


class MAOperator(ta_operator.TAOperator):
    DESCRIPTION = "Returns the moving average of the given array of numbers"
    EXAMPLE = "ma(close('BTC/USDT', '1h'), 14)"

    @staticmethod
    def get_name() -> str:
        return "ma"

    @staticmethod
    def get_parameters() -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="data", description="the data to compute the moving average on", required=True, type=list),
            dsl_interpreter.OperatorParameter(name="period", description="the period to use for the moving average", required=True, type=int),
        ]

    @converted_tulipy_error
    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        operands = self.get_computed_parameters()
        return list(tulipy.sma(_to_numpy_array(operands[0]), period=_to_int(operands[1])))


class EMAOperator(ta_operator.TAOperator):
    DESCRIPTION = "Returns the exponential moving average of the given array of numbers"
    EXAMPLE = "ema(close('BTC/USDT', '1h'), 14)"

    @staticmethod
    def get_name() -> str:
        return "ema"

    @staticmethod
    def get_parameters() -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="data", description="the data to compute the exponential moving average on", required=True, type=list),
            dsl_interpreter.OperatorParameter(name="period", description="the period to use for the exponential moving average", required=True, type=int),
        ]

    @converted_tulipy_error
    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        operands = self.get_computed_parameters()
        return list(tulipy.ema(_to_numpy_array(operands[0]), period=_to_int(operands[1])))


class VWMAOperator(ta_operator.TAOperator):
    DESCRIPTION = "Returns the volume weighted moving average of the given array of numbers"
    EXAMPLE = "vwma(close('BTC/USDT', '1h'), volume('BTC/USDT', '1h'), 14)"

    @staticmethod
    def get_name() -> str:
        return "vwma"

    @staticmethod
    def get_parameters() -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="data", description="the data to compute the volume weighted moving average on", required=True, type=list),
            dsl_interpreter.OperatorParameter(name="volume", description="the volume data to use for the volume weighted moving average", required=True, type=list),
            dsl_interpreter.OperatorParameter(name="period", description="the period to use for the volume weighted moving average", required=True, type=int),
        ]

    @converted_tulipy_error
    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        operands = self.get_computed_parameters()
        return list(tulipy.vwma(_to_numpy_array(operands[0]), _to_numpy_array(operands[1]), period=_to_int(operands[2])))
