#  Drakkar-Software OctoBot
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

import ccxt
import pytest

from trading.exchanges.exchange_manager import ExchangeManager
from evaluator.symbol_evaluator import SymbolEvaluator
from trading.trader.trader_simulator import TraderSimulator
from evaluator.cryptocurrency_evaluator import CryptocurrencyEvaluator
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.evaluator import Evaluator
from tests.test_utils.config import load_test_config
from evaluator.Util.advanced_manager import AdvancedManager
from trading.trader.portfolio import Portfolio
from core.global_price_updater import GlobalPriceUpdater
from evaluator.evaluator_task_manager import EvaluatorTaskManager
from config import TimeFrames, EVALUATOR_EVAL_DEFAULT_TYPE
from trading.util.trading_config_util import get_activated_trading_mode


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def _get_tools(event_loop):
    symbol = "BTC/USDT"
    exchange_traders = {}
    exchange_traders2 = {}
    config = load_test_config()
    time_frame = TimeFrames.ONE_HOUR
    AdvancedManager.create_class_list(config)
    exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
    await exchange_manager.initialize()
    exchange_inst = exchange_manager.get_exchange()
    global_price_updater = GlobalPriceUpdater(exchange_inst)
    trader_inst = TraderSimulator(config, exchange_inst, 0.3)
    trader_inst.stop_order_manager()
    trader_inst2 = TraderSimulator(config, exchange_inst, 0.3)
    trader_inst2.stop_order_manager()
    crypto_currency_evaluator = CryptocurrencyEvaluator(config, "Bitcoin", [])
    symbol_evaluator = SymbolEvaluator(config, symbol, crypto_currency_evaluator)
    exchange_traders[exchange_inst.get_name()] = trader_inst
    exchange_traders2[exchange_inst.get_name()] = trader_inst2
    symbol_evaluator.set_trader_simulators(exchange_traders)
    symbol_evaluator.set_traders(exchange_traders2)
    symbol_evaluator.strategies_eval_lists[exchange_inst.get_name()] = \
        EvaluatorCreator.create_strategies_eval_list(config)
    trading_mode_inst = get_activated_trading_mode(config)(config, exchange_inst)
    evaluator_task_manager = EvaluatorTaskManager(config, time_frame, global_price_updater,
                                                  symbol_evaluator, exchange_inst, trading_mode_inst, [],
                                                  event_loop)
    trader_inst.portfolio.portfolio["USDT"] = {
        Portfolio.TOTAL: 2000,
        Portfolio.AVAILABLE: 2000
    }
    return evaluator_task_manager, time_frame, global_price_updater, symbol_evaluator, symbol


async def test_default_values(event_loop):
    evaluator_task_manager, time_frame, global_updater_thread, symbol_evaluator, symbol = \
        await _get_tools(event_loop)
    assert symbol_evaluator.evaluator_task_managers[evaluator_task_manager.exchange.get_name()][time_frame] \
        == evaluator_task_manager
    assert global_updater_thread.evaluator_task_manager_by_time_frame_by_symbol[time_frame][symbol] \
        == evaluator_task_manager
    assert isinstance(evaluator_task_manager.evaluator, Evaluator)
    assert evaluator_task_manager.evaluator.get_config() == evaluator_task_manager.config
    assert evaluator_task_manager.evaluator.get_symbol() == evaluator_task_manager.symbol
    assert evaluator_task_manager.evaluator.get_time_frame() == evaluator_task_manager.time_frame
    assert evaluator_task_manager.evaluator.get_exchange() == evaluator_task_manager.exchange
    assert evaluator_task_manager.evaluator.get_symbol_evaluator() == evaluator_task_manager.symbol_evaluator


async def test_refresh_matrix(event_loop):
    evaluator_task_manager, _, _, _, _ = \
        await _get_tools(event_loop)
    evaluator_task_manager.matrix = None
    evaluator_task_manager.refresh_matrix(refresh_matrix_evaluation_types=False)
    assert evaluator_task_manager.matrix is not None
    assert evaluator_task_manager.matrix.evaluator_eval_types == {}
    assert evaluator_task_manager.matrix.get_evaluator_eval_type("XYZ") is None
    assert evaluator_task_manager.matrix.get_evaluator_eval_type("ADXMomentumEvaluator") is None
    evaluator_task_manager.refresh_matrix(refresh_matrix_evaluation_types=True)
    assert evaluator_task_manager.matrix is not None
    assert len(evaluator_task_manager.matrix.evaluator_eval_types) == 5
    assert evaluator_task_manager.matrix.get_evaluator_eval_type("ADXMomentumEvaluator") == EVALUATOR_EVAL_DEFAULT_TYPE
    assert evaluator_task_manager.matrix.get_evaluator_eval_type("XYZ") is None
