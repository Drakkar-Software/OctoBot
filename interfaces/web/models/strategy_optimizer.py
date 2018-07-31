import threading


from interfaces import get_bot
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.Strategies.strategies_evaluator import StrategiesEvaluator
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator import Strategies
from tools.class_inspector import get_class_from_string, evaluator_parent_inspection
from config.cst import BOT_TOOLS_STRATEGY_OPTIMIZER
from backtesting.strategy_optimizer.strategy_optimizer import StrategyOptimizer


def get_strategies_list():
    try:
        config = get_bot().get_config()
        classes = AdvancedManager.get_all_classes(StrategiesEvaluator, config)
        return set(strategy.get_name() for strategy in classes)
    except Exception:
        return []


def get_time_frames_list(strategy_name=None):
    if strategy_name is None:
        strategy_name = get_current_strategy()
    if strategy_name:
        strategy_class = get_class_from_string(strategy_name, StrategiesEvaluator,
                                               Strategies, evaluator_parent_inspection)
        return [tf.value for tf in strategy_class.get_required_time_frames(get_bot().get_config())]
    else:
        return []


def get_evaluators_list(strategy_name=None):
    if strategy_name is None:
        strategy_name = get_current_strategy()
    if strategy_name:
        strategy_class = get_class_from_string(strategy_name, StrategiesEvaluator,
                                               Strategies, evaluator_parent_inspection)
        evaluators = EvaluatorCreator.get_relevant_TAs_for_strategy(strategy_class, get_bot().get_config())
        return set(evaluator.get_name() for evaluator in evaluators)
    else:
        return []


def get_risks_list():
    return [i/10 for i in range(10, 0, -1)]


def get_current_strategy():
    try:
        first_symbol_evaluator = next(iter(get_bot().get_symbol_evaluator_list().values()))
        first_exchange = next(iter(get_bot().get_exchanges_list().values()))
        return first_symbol_evaluator.get_strategies_eval_list(first_exchange)[0].get_name()
    except Exception:
        strategy_list = get_strategies_list()
        return strategy_list[0] if strategy_list else ""


def start_optimizer(strategy, time_frames, evaluators, risks):
    tools = get_bot().get_tools
    if not tools[BOT_TOOLS_STRATEGY_OPTIMIZER]:
        tools[BOT_TOOLS_STRATEGY_OPTIMIZER] = StrategyOptimizer(get_bot().get_config(), strategy)
    optimizer = tools[BOT_TOOLS_STRATEGY_OPTIMIZER]
    if optimizer.get_is_computing():
        return False, "Optimizer already running"
    else:
        # thread = threading.Thread(target=optimizer.find_optimal_configuration, args=(time_frames, evaluators, risks))
        # thread.start()
        return True, "Optimizer started"


def get_optimizer_results():
    optimizer = get_bot().get_tools[BOT_TOOLS_STRATEGY_OPTIMIZER]
    if optimizer:
        results = optimizer.get_results()
        return [result.get_result_dict(i) for i, result in enumerate(results)]
    else:
        return []
