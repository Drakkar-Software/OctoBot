

from interfaces import get_bot
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.Strategies.strategies_evaluator import StrategiesEvaluator
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator import Strategies
from tools.class_inspector import get_class_from_string, evaluator_parent_inspection


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
    print(strategy)
    print(time_frames)
    print(evaluators)
    print(risks)

def get_optimizer_results():
    id = "id"
    evaluators = "evaluators"
    time_frames = "time_frames"
    risk = "risk"
    score = "score"
    average_trades = "average_trades"
    return []
