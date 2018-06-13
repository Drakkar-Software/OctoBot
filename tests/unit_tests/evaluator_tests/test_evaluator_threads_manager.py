import ccxt

from trading.exchanges.exchange_manager import ExchangeManager
from evaluator.symbol_evaluator import SymbolEvaluator
from trading.trader.trader_simulator import TraderSimulator
from evaluator.cryptocurrency_evaluator import CryptocurrencyEvaluator
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.evaluator import Evaluator
from tests.test_utils.config import load_test_config
from evaluator.Util.advanced_manager import AdvancedManager
from trading.trader.portfolio import Portfolio
from evaluator.Updaters.symbol_time_frames_updater import SymbolTimeFramesDataUpdaterThread
from evaluator.evaluator_threads_manager import EvaluatorThreadsManager
from config.cst import TimeFrames


def _get_tools():
    symbol = "BTC/USDT"
    exchange_traders = {}
    exchange_traders2 = {}
    config = load_test_config()
    time_frame = TimeFrames.ONE_HOUR
    AdvancedManager.create_class_list(config)
    symbol_time_frame_updater_thread = SymbolTimeFramesDataUpdaterThread()
    exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
    exchange_inst = exchange_manager.get_exchange()
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
    symbol_evaluator.strategies_eval_lists[exchange_inst.get_name()] = EvaluatorCreator.create_strategies_eval_list(config)
    evaluator_thread_manager = EvaluatorThreadsManager(config, symbol, time_frame, symbol_time_frame_updater_thread,
                                                       symbol_evaluator, exchange_inst, [])
    trader_inst.portfolio.portfolio["USDT"] = {
        Portfolio.TOTAL: 2000,
        Portfolio.AVAILABLE: 2000
    }
    return evaluator_thread_manager, time_frame, symbol_time_frame_updater_thread, symbol_evaluator


def test_default_values():
    evaluator_thread_manager, time_frame, symbol_time_frame_updater_thread, symbol_evaluator = _get_tools()
    assert symbol_evaluator.evaluator_thread_managers[evaluator_thread_manager.exchange.get_name()][time_frame] \
        == evaluator_thread_manager
    assert symbol_time_frame_updater_thread.evaluator_threads_manager_by_time_frame[time_frame] \
        == evaluator_thread_manager
    assert isinstance(evaluator_thread_manager.evaluator, Evaluator)
    assert evaluator_thread_manager.evaluator.get_config() == evaluator_thread_manager.config
    assert evaluator_thread_manager.evaluator.get_symbol() == evaluator_thread_manager.symbol
    assert evaluator_thread_manager.evaluator.get_time_frame() == evaluator_thread_manager.time_frame
    assert evaluator_thread_manager.evaluator.get_exchange() == evaluator_thread_manager.exchange
    assert evaluator_thread_manager.evaluator.get_symbol_evaluator() == evaluator_thread_manager.symbol_evaluator


def test_refresh_matrix():
    evaluator_thread_manager, time_frame, symbol_time_frame_updater_thread, symbol_evaluator = _get_tools()
    evaluator_thread_manager.matrix = None
    evaluator_thread_manager.refresh_matrix()
    assert evaluator_thread_manager.matrix is not None
