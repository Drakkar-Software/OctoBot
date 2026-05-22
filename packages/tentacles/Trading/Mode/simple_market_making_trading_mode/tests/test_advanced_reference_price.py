# Drakkar-Software OctoBot-Tentacles
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
import decimal
import uuid

import numpy as np
import mock
import pytest

import octobot_commons.enums as commons_enums
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors
import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants
import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators

import tentacles.Trading.Mode.simple_market_making_trading_mode.advanced_reference_price as advanced_reference_price

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def exchange_manager_mock():
    """Create a mock exchange manager for testing."""
    exchange_manager = mock.Mock()
    exchange_manager.id = str(uuid.uuid4())
    exchange_manager.exchange_name = "binance"
    exchange_manager.get_exchange_symbol = mock.Mock(
        side_effect=lambda symbol, **kwargs: symbol
    )
    return exchange_manager


@pytest.fixture
def candle_manager_by_time_frame_by_symbol():
    """Create a mock candle manager structure."""
    return {
        commons_enums.TimeFrames.ONE_HOUR.value: {
            "BTC/USDT": mock.Mock()
        }
    }


@pytest.fixture
def price_source_no_formula(exchange_manager_mock):
    """Create an AdvancedPriceSource without a formula."""
    return advanced_reference_price.AdvancedPriceSource(
        exchange="binance",
        pair="BTC/USDT",
        time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
        weight=decimal.Decimal("1.0"),
        formula=""
    )


@pytest.fixture
def price_source_with_formula(exchange_manager_mock):
    """Create an AdvancedPriceSource with a formula."""
    return advanced_reference_price.AdvancedPriceSource(
        exchange="binance",
        pair="BTC/USDT",
        time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
        weight=decimal.Decimal("2.0"),
        formula="50000"
    )


async def test_evaluate_formula_no_formula(price_source_no_formula):
    """Test evaluate_formula when no formula is provided."""
    price = decimal.Decimal("50000.50")
    result = await price_source_no_formula.evaluate_formula(price)
    assert result == price


async def test_evaluate_formula_no_formula_requires_price(price_source_no_formula):
    with pytest.raises(ValueError, match="price is required when no formula is configured"):
        await price_source_no_formula.evaluate_formula()


async def test_evaluate_formula_with_valid_formula(price_source_with_formula, exchange_manager_mock):
    """Test evaluate_formula with a valid numeric formula."""
    # Set a simple numeric formula
    price_source_with_formula.formula = "50000.25"
    
    # Initialize the formula interpreter with real interpreter
    with mock.patch.object(
        trading_api, 'get_watched_timeframes', return_value=[commons_enums.TimeFrames.ONE_HOUR]
    ), mock.patch.object(
        exchange_operators, 'create_ohlcv_operators', return_value=[]
    ):
        await price_source_with_formula.initialize_if_required(exchange_manager_mock)
    
    result = await price_source_with_formula.evaluate_formula()
    assert result == decimal.Decimal("50000.25")


async def test_evaluate_formula_with_invalid_formula(price_source_with_formula, exchange_manager_mock):
    """Test evaluate_formula with an invalid formula that raises DecimalException."""
    # Set a formula that will return a non-numeric value (using a string literal)
    # The interpreter will parse it but Decimal conversion will fail
    price_source_with_formula.formula = '"invalid"'
    
    # Initialize the formula interpreter with real interpreter
    with mock.patch.object(
        trading_api, 'get_watched_timeframes', return_value=[commons_enums.TimeFrames.ONE_HOUR]
    ), mock.patch.object(
        exchange_operators, 'create_ohlcv_operators', return_value=[]
    ):
        await price_source_with_formula.validate_interpreted_formula(exchange_manager_mock)

    price_source_with_formula.formula = "[1, 2, 3] * 4.2"
    # Initialize the formula interpreter with real interpreter
    with mock.patch.object(
        trading_api, 'get_watched_timeframes', return_value=[commons_enums.TimeFrames.ONE_HOUR]
    ), mock.patch.object(
        exchange_operators, 'create_ohlcv_operators', return_value=[]
    ):
        await price_source_with_formula.validate_interpreted_formula(exchange_manager_mock)
    
    price = decimal.Decimal("50000.50")
    with pytest.raises(TypeError, match="Invalid BTC/USDT reference price formula: TypeError"):
        await price_source_with_formula.evaluate_formula(price)


async def test_evaluate_formula_with_invalid_formula_error_messages(price_source_with_formula, exchange_manager_mock):
    price = decimal.Decimal("50000.50")
    price_source_with_formula.formula = "[1, 2, 3, 4, 5, 6]"
    # Initialize the formula interpreter with real interpreter
    with mock.patch.object(
        trading_api, 'get_watched_timeframes', return_value=[commons_enums.TimeFrames.ONE_HOUR]
    ), mock.patch.object(
        exchange_operators, 'create_ohlcv_operators', return_value=[]
    ):
        await price_source_with_formula.initialize_if_required(exchange_manager_mock)
        with pytest.raises(NotImplementedError) as err:
            await price_source_with_formula.evaluate_formula(price)
        assert str(err.value) == "Configured formula \"[1, 2, 3, 4, 5, 6]\" should return a number, got list (value: [1, 2, '...', 5, 6])"

    for return_value in (
        [1, 2, 3, 4, 5, 6],
        tuple([1, 2, 3, 4, 5, 6]),
        np.array([1, 2, 3, 4, 5, 6], dtype=np.float64),
        np.array([1, 2, 3, 4, 5, 6], dtype=np.int64),
    ):
        # Initialize the formula interpreter with real interpreter
        with mock.patch.object(
            price_source_with_formula, '_evaluate_formula', return_value=return_value
        ):
            with pytest.raises(NotImplementedError) as err:
                await price_source_with_formula.evaluate_formula(price)
            assert str(err.value) == f"Configured formula \"[1, 2, 3, 4, 5, 6]\" should return a number, got {type(return_value).__name__} (value: {list(return_value[:2]) + ['...'] + list(return_value[-2:])})"


def test_get_dependencies_no_formula(price_source_no_formula, exchange_manager_mock):
    """Test get_dependencies when no formula is provided."""
    with mock.patch.object(
        trading_api, 'get_exchange_manager_id', return_value=exchange_manager_mock.id
    ):
        dependencies = price_source_no_formula.get_dependencies(exchange_manager_mock)
    assert dependencies == [
        exchange_operators.ExchangeDataDependency(
            symbol="BTC/USDT",
            time_frame=None,
            data_source=trading_constants.MARK_PRICE_CHANNEL
        )
    ]


async def test_get_dependencies_with_formula(price_source_with_formula, exchange_manager_mock):
    """Test get_dependencies when a formula is provided."""
    # Use a simple numeric formula (no dependencies expected)
    price_source_with_formula.formula = "50000"
    
    # Initialize the formula interpreter with real interpreter
    with mock.patch.object(
        trading_api, 'get_watched_timeframes', return_value=[commons_enums.TimeFrames.ONE_HOUR]
    ), mock.patch.object(
        exchange_operators, 'create_ohlcv_operators', return_value=[]
    ):
        await price_source_with_formula.initialize_if_required(exchange_manager_mock)
    
    dependencies = price_source_with_formula.get_dependencies(exchange_manager_mock)
    
    # Simple numeric formula should have no dependencies
    assert dependencies == [
        exchange_operators.ExchangeDataDependency(
            symbol="BTC/USDT",
            time_frame=None,
            data_source=trading_constants.MARK_PRICE_CHANNEL
        )
    ]


async def test_initialize_no_formula(price_source_no_formula, exchange_manager_mock):
    """Test initialize when no formula is provided."""
    await price_source_no_formula.initialize_if_required(exchange_manager_mock)
    assert price_source_no_formula._formula_interpreter is None


async def test_initialize_with_formula_and_exchange_manager(price_source_with_formula, exchange_manager_mock):
    """Test initialize with a formula and exchange_manager."""
    price_source_with_formula.formula = "49999 + 1"
    with mock.patch.object(
        trading_api, 'get_watched_timeframes', return_value=[commons_enums.TimeFrames.ONE_HOUR]
    ) as mock_get_timeframes, mock.patch.object(
        exchange_operators, 'create_ohlcv_operators', return_value=[]
    ) as mock_create_ohlcv:
        await price_source_with_formula.initialize_if_required(exchange_manager_mock)
    
    assert price_source_with_formula._formula_interpreter is not None
    assert isinstance(price_source_with_formula._formula_interpreter, dsl_interpreter.Interpreter)
    mock_get_timeframes.assert_called_once_with(exchange_manager_mock)
    mock_create_ohlcv.assert_called_once()
    
    # Verify the interpreter can compute the expression
    result = await price_source_with_formula._formula_interpreter.compute_expression()
    assert result == 50000


async def test_initialize_with_formula_and_candle_manager(price_source_with_formula, candle_manager_by_time_frame_by_symbol):
    """Test initialize with a formula and candle_manager_by_time_frame_by_symbol."""
    price_source_with_formula.formula = "49999 + 1"
    with mock.patch.object(
        exchange_operators, 'create_ohlcv_operators', return_value=[]
    ) as mock_create_ohlcv:
        await price_source_with_formula.initialize_if_required(
            None, candle_manager_by_time_frame_by_symbol=candle_manager_by_time_frame_by_symbol
        )
    
    assert price_source_with_formula._formula_interpreter is not None
    assert isinstance(price_source_with_formula._formula_interpreter, dsl_interpreter.Interpreter)
    mock_create_ohlcv.assert_called_once()
    
    # Verify the interpreter can compute the expression
    result = await price_source_with_formula._formula_interpreter.compute_expression()
    assert result == 50000


async def test_initialize_with_formula_default_time_frame(price_source_with_formula, exchange_manager_mock):
    """Test initialize uses default time frame when time_frame is None."""
    price_source_with_formula.time_frame = None
    
    with mock.patch.object(
        trading_api, 'get_watched_timeframes', return_value=[commons_enums.TimeFrames.ONE_DAY.value]
    ), mock.patch.object(
        exchange_operators, 'create_ohlcv_operators', return_value=[]
    ) as create_ohlcv_operators_mock:
        await price_source_with_formula.initialize_if_required(exchange_manager_mock)
        assert create_ohlcv_operators_mock.mock_calls[0].args[2] == commons_enums.TimeFrames.ONE_DAY.value
    
    assert price_source_with_formula._formula_interpreter is not None
    assert isinstance(price_source_with_formula._formula_interpreter, dsl_interpreter.Interpreter)
    
    # Verify the interpreter can compute the expression
    result = await price_source_with_formula._formula_interpreter.compute_expression()
    assert result == 50000


async def test_initialize_with_formula_prepare_error(price_source_with_formula, exchange_manager_mock):
    """Test initialize raises error when formula preparation fails."""
    # Use an invalid formula that will cause a parse error
    
    with mock.patch.object(
        trading_api, 'get_watched_timeframes', return_value=[commons_enums.TimeFrames.ONE_HOUR]
    ), mock.patch.object(
        exchange_operators, 'create_ohlcv_operators', return_value=[]
    ):
        price_source_with_formula.formula = "invalid_syntax_!!!"
        with pytest.raises(SyntaxError):
            await price_source_with_formula.validate_interpreted_formula(exchange_manager_mock)
        
        price_source_with_formula.formula = "max()"
        with pytest.raises(octobot_commons.errors.InvalidParametersError):
            await price_source_with_formula.validate_interpreted_formula(exchange_manager_mock)
        
        price_source_with_formula.formula = "plop"
        with pytest.raises(octobot_commons.errors.UnsupportedOperatorError):
            await price_source_with_formula.validate_interpreted_formula(exchange_manager_mock)


def test_advanced_price_source_attributes(price_source_no_formula):
    """Test that AdvancedPriceSource has the correct attributes."""
    assert price_source_no_formula.exchange == "binance"
    assert price_source_no_formula.pair == "BTC/USDT"
    assert price_source_no_formula.time_frame == commons_enums.TimeFrames.ONE_HOUR.value
    assert price_source_no_formula.weight == decimal.Decimal("1.0")
    assert price_source_no_formula.formula == ""
    assert price_source_no_formula._formula_interpreter is None


@pytest.mark.parametrize("formula, expected_formula_dependencies", [
    pytest.param(
        "close",
        [
            exchange_operators.ExchangeDataDependency(
                symbol="BTC/USDT",
                time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
                data_source=trading_constants.OHLCV_CHANNEL,
            ),
        ],
        id="close",
    ),
    pytest.param(
        "price",
        [],
        id="price",
    ),
])
async def test_get_dependencies_with_formula_dependencies(
    price_source_with_formula,
    exchange_manager_mock,
    formula,
    expected_formula_dependencies,
):
    """Test get_dependencies returns dependencies from interpreter for OHLCV and price operators."""
    ohlcv_operators = exchange_operators.create_ohlcv_operators(
        exchange_manager_mock, "BTC/USDT", commons_enums.TimeFrames.ONE_HOUR.value
    )
    price_operators = exchange_operators.create_price_operators(
        exchange_manager_mock, "BTC/USDT"
    )
    price_source_with_formula.formula = formula

    with mock.patch.object(
        trading_api, 'get_watched_timeframes', return_value=[commons_enums.TimeFrames.ONE_HOUR]
    ), mock.patch.object(
        exchange_operators, 'create_ohlcv_operators', return_value=ohlcv_operators
    ), mock.patch.object(
        exchange_operators, 'create_price_operators', return_value=price_operators
    ):
        await price_source_with_formula.initialize_if_required(exchange_manager_mock)

    mark_price_dependency = exchange_operators.ExchangeDataDependency(
        symbol="BTC/USDT",
        time_frame=None,
        data_source=trading_constants.MARK_PRICE_CHANNEL,
    )
    dependencies = price_source_with_formula.get_dependencies(exchange_manager_mock)
    assert dependencies == [mark_price_dependency] + expected_formula_dependencies


class TestComputeReferencePrice:
    async def test_uses_formula_without_price_in_dict(
        self, price_source_with_formula, exchange_manager_mock
    ):
        price_source_with_formula.formula = "50000.25"
        with mock.patch.object(
            trading_api, 'get_watched_timeframes', return_value=[commons_enums.TimeFrames.ONE_HOUR]
        ), mock.patch.object(
            exchange_operators, 'create_ohlcv_operators', return_value=[]
        ):
            await price_source_with_formula.initialize_if_required(exchange_manager_mock)

        price_by_pair_by_exchange = {"binance": {"BTC/USDT": None}}
        reference_price_specs_by_exchange = {"binance": [price_source_with_formula]}
        result = await advanced_reference_price.compute_reference_price(
            price_by_pair_by_exchange, reference_price_specs_by_exchange
        )
        assert result == decimal.Decimal("50000.25")

    async def test_raises_when_no_formula_and_price_missing(self, price_source_no_formula):
        price_by_pair_by_exchange = {"binance": {"BTC/USDT": None}}
        reference_price_specs_by_exchange = {"binance": [price_source_no_formula]}
        with pytest.raises(ValueError, match="price is required when no formula is configured"):
            await advanced_reference_price.compute_reference_price(
                price_by_pair_by_exchange, reference_price_specs_by_exchange
            )
