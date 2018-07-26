from abc import ABCMeta, abstractmethod
import copy

from tests.test_utils.backtesting_util import create_backtesting_config, create_backtesting_bot, \
    start_backtesting_bot, filter_wanted_symbols
from config.cst import CONFIG_EVALUATOR, CONFIG_BACKTESTING, CONFIG_BACKTESTING_DATA_FILES
from evaluator import Strategies
from evaluator.Strategies.strategies_evaluator import StrategiesEvaluator
from tools.class_inspector import get_class_from_string, evaluator_parent_inspection
from backtesting.collector.exchange_collector import ExchangeDataCollector


DEFAULT_SYMBOL = "ICX/BTC"
DATA_FILE_PATH = "tests/static/"
DATA_FILE_EXT = ".data"


class AbstractStrategyTest:
    __metaclass__ = ABCMeta

    def init(self, strategy_evaluator_class, config=None):
        if config is None:
            self.config = create_backtesting_config(filter_symbols=False)
        else:
            self.config = config
        self.strategy_evaluator_class = strategy_evaluator_class
        self._register_only_strategy(strategy_evaluator_class)
        self._assert_init()

    # plays a backtesting market profitability:
    # 1. ICX/BTC[30m]: -13.704206241519667 % (binance_ICX_BTC_20180716_131148)
    @staticmethod
    @abstractmethod
    def test_default_run(strategy_tester):
        raise NotImplementedError("test_default_run not implemented")

    # plays a backtesting on a slow downtrend market:
    # 1. ICX/BTC[30m]: -13.704206241519667 % (binance_ICX_BTC_20180716_131148)
    # 2. NEO/BTC[30m]: -41.09080962800873 % (bittrex_NEO_BTC_20180722_195942)
    # 3. ONT/BTC[30m]: -17.9185520361991 % (binance_ONT_BTC_20180722_230900)
    # 4. XVG/BTC[30m]: -47.29729729729728 % (bittrex_XVG_BTC_20180726_211225)
    @staticmethod
    @abstractmethod
    def test_slow_downtrend(strategy_tester):
        raise NotImplementedError("test_slow_downtrend not implemented")

    # plays a backtesting on a sharp downtrend market:
    # 1. VEN/BTC[30m] -35.26645213762865 % (binance_VEN_BTC_20180716_131148)
    # 2. XRP/BTC[30m]: -47.41750358680059 (vs btc) % (bittrex_XRP_BTC_20180726_210927)
    @staticmethod
    @abstractmethod
    def test_sharp_downtrend(strategy_tester):
        raise NotImplementedError("test_sharp_downtrend not implemented")

    # plays a backtesting flat markets profitability:
    # 1. NEO/BTC[30m] -11.80763473053894 % (binance_NEO_BTC_20180716_131148)
    # 2. XRB/BTC[30m] -3.5209457722950255 % (binance_XRB_BTC_20180716_131148)
    # 3. ADA/BTC[30m] -6.140724946695086 % (bittrex_ADA_BTC_20180722_223357)
    # 4. WAX/BTC[30m] -8.77598152424941 % (bittrex_WAX_BTC_20180726_205032)
    @staticmethod
    @abstractmethod
    def test_flat_markets(strategy_tester):
        raise NotImplementedError("test_flat_markets not implemented")

    # plays a backtesting with this strategy on a slow uptrend market:
    # 1. BTC/USDT[30m]: 17.20394836443646 (vs btc) % (binance_BTC_USDT_20180428_121156)
    # 2. ADA/BTC[30m] 16.19613670133728 % (binance_ADA_BTC_20180722_223335)
    @staticmethod
    @abstractmethod
    def test_slow_uptrend(strategy_tester):
        raise NotImplementedError("test_slow_uptrend not implemented")

    # plays a backtesting with this strategy on a slow uptrend market:
    # 1. XLM/BTC[30m]: 30.88185223016684 (vs btc) % (binance_XLM_BTC_20180722_234305)
    # 2. POWR/BTC[30m]: 12.28597871355852 (vs btc) % (binance_POWR_BTC_20180722_234855)
    @staticmethod
    @abstractmethod
    def test_sharp_uptrend(strategy_tester):
        raise NotImplementedError("test_sharp_uptrend not implemented")

    # plays a backtesting with this strategy on a slow uptrend market followed by a slow downtrend market:
    # 1. ETC/BTC[30m] -6.428386403538222 % (bittrex_ETC_BTC_20180726_210341)
    @staticmethod
    @abstractmethod
    def test_up_then_down(strategy_tester):
        raise NotImplementedError("test_up_then_down not implemented")

    def run_test_default_run(self, profitability):
        run_results, bot = self._run_backtesting_with_current_config(DEFAULT_SYMBOL)
        self._assert_results(run_results, profitability, bot)

    def run_test_slow_downtrend(self, profitability_1, profitability_2, profitability_3, profitability_4,
                                skip_bittrex=False):
        run_results, bot = self._run_backtesting_with_current_config("ICX/BTC")
        self._assert_results(run_results, profitability_1, bot)
        run_results, bot = self._run_backtesting_with_current_config("ONT/BTC")
        self._assert_results(run_results, profitability_2, bot)
        if not skip_bittrex:
            run_results, bot = self._run_backtesting_with_current_config("NEO/BTC", "bittrex_NEO_BTC_20180722_195942")
            self._assert_results(run_results, profitability_3, bot)
            run_results, bot = self._run_backtesting_with_current_config("XVG/BTC", "bittrex_XVG_BTC_20180726_211225")
            self._assert_results(run_results, profitability_4, bot)

    def run_test_sharp_downtrend(self, profitability_1, profitability_2, skip_bittrex=False):
        run_results, bot = self._run_backtesting_with_current_config("VEN/BTC")
        self._assert_results(run_results, profitability_1, bot)
        if not skip_bittrex:
            run_results, bot = self._run_backtesting_with_current_config("XRP/BTC", "bittrex_XRP_BTC_20180726_210927")
            self._assert_results(run_results, profitability_2, bot)

    def run_test_flat_markets(self, profitability_1, profitability_2, profitability_3, profitability_4,
                              skip_bittrex=False):
        run_results, bot = self._run_backtesting_with_current_config("NEO/BTC")
        self._assert_results(run_results, profitability_1, bot)
        run_results, bot = self._run_backtesting_with_current_config("XRB/BTC")
        self._assert_results(run_results, profitability_2, bot)
        if not skip_bittrex:
            run_results, bot = self._run_backtesting_with_current_config("ADA/BTC", "bittrex_ADA_BTC_20180722_223357")
            self._assert_results(run_results, profitability_3, bot)
            run_results, bot = self._run_backtesting_with_current_config("WAX/BTC", "bittrex_WAX_BTC_20180726_205032")
            self._assert_results(run_results, profitability_4, bot)

    def run_test_slow_uptrend(self, profitability_1, profitability_2):
        run_results, bot = self._run_backtesting_with_current_config("BTC/USDT")
        self._assert_results(run_results, profitability_1, bot)
        run_results, bot = self._run_backtesting_with_current_config("ADA/BTC")
        self._assert_results(run_results, profitability_2, bot)

    def run_test_sharp_uptrend(self, profitability_1, profitability_2):
        run_results, bot = self._run_backtesting_with_current_config("XLM/BTC")
        self._assert_results(run_results, profitability_1, bot)
        run_results, bot = self._run_backtesting_with_current_config("POWR/BTC")
        self._assert_results(run_results, profitability_2, bot)

    def run_test_up_then_down(self, profitability_1, skip_bittrex=False):
        if not skip_bittrex:
            run_results, bot = self._run_backtesting_with_current_config("ETC/BTC", "bittrex_ETC_BTC_20180726_210341")
            self._assert_results(run_results, profitability_1, bot)

    def _assert_results(self, run_results, profitability, bot):
        # print(f"results: {run_results} expected: {profitability}")  # convenient for building tests
        assert run_results[0] >= profitability

    def _run_backtesting_with_current_config(self, symbol, data_file_to_use=None):
        config_to_use = copy.deepcopy(self.config)
        if data_file_to_use is not None:
            for index, datafile in enumerate(config_to_use[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILES]):
                _, file_symbol, _ = ExchangeDataCollector.get_file_name(datafile)
                if symbol == file_symbol:
                    config_to_use[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILES][index] = \
                        DATA_FILE_PATH + data_file_to_use + DATA_FILE_EXT

        filter_wanted_symbols(config_to_use, [symbol])
        bot = create_backtesting_bot(config_to_use)
        return start_backtesting_bot(bot), bot

    def _register_only_strategy(self, strategy_evaluator_class):
        for evaluatotor_name in self.config[CONFIG_EVALUATOR]:
            if get_class_from_string(evaluatotor_name, StrategiesEvaluator, Strategies,
                                     evaluator_parent_inspection) is not None:
                self.config[CONFIG_EVALUATOR][evaluatotor_name] = False
        self.config[CONFIG_EVALUATOR][strategy_evaluator_class.get_name()] = True

    def _assert_init(self):
        assert self.config
        assert self.config[CONFIG_EVALUATOR][self.strategy_evaluator_class.get_name()] is True
