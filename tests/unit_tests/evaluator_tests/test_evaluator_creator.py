from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.Strategies import StrategiesEvaluator
from tests.test_utils.config import load_test_config
from evaluator.Util.advanced_manager import AdvancedManager
from config import TimeFrames, CONFIG_EVALUATORS_WILDCARD
from evaluator.evaluator import Evaluator
from evaluator.TA import TAEvaluator
from evaluator.Social import SocialEvaluator
# from evaluator.RealTime import RealTimeEvaluator


def _get_tools():
    config = load_test_config()
    AdvancedManager.create_class_list(config)
    evaluator = Evaluator()
    evaluator.set_config(config)
    evaluator.set_symbol("BTC/USDT")
    evaluator.set_time_frame(TimeFrames.ONE_HOUR)
    return evaluator, config


def _assert_created_instances(instances_list, super_class, config):
    class_list = [instance.__class__ for instance in instances_list]
    for eval_class in AdvancedManager.create_advanced_evaluator_types_list(super_class, config):
        eval_instance = eval_class()
        eval_instance.set_config(config)
        if eval_instance.get_is_enabled():
            assert eval_class in class_list


def test_create_dispatchers():
    _, config = _get_tools()
    dispatchers = EvaluatorCreator.create_dispatchers(config)
    assert len(dispatchers) == 0  # no dispatcher created because no config for associated services


def test_create_ta_eval_list():
    evaluator, config = _get_tools()
    ta_list = EvaluatorCreator.create_ta_eval_list(evaluator, CONFIG_EVALUATORS_WILDCARD)
    _assert_created_instances(ta_list, TAEvaluator, config)


def test_create_social_eval_list():
    evaluator, config = _get_tools()
    so_list = EvaluatorCreator.create_social_eval(config, evaluator.symbol, [], CONFIG_EVALUATORS_WILDCARD)
    _assert_created_instances(so_list, SocialEvaluator, config)


def test_create_social_not_threaded_list():
    evaluator, config = _get_tools()
    so_list = EvaluatorCreator.create_social_eval(config, evaluator.symbol, [], CONFIG_EVALUATORS_WILDCARD)
    not_thread_so_list = EvaluatorCreator.create_social_not_threaded_list(so_list)
    for evalator in not_thread_so_list:
        assert not evalator.is_threaded


def test_create_strategies_eval_list():
    evaluator, config = _get_tools()
    strat_list = EvaluatorCreator.create_strategies_eval_list(config)
    _assert_created_instances(strat_list, StrategiesEvaluator, config)


# not tested for now
# def test_create_real_time_ta_evals():
#     evaluator, config = _get_tools()
#     ta_list = EvaluatorCreator.create_real_time_ta_evals(config, evaluator.exchange,
#                                                          evaluator.symbol, CONFIG_EVALUATORS_WILDCARD)
#     _assert_created_instances(ta_list, RealTimeEvaluator, config)
