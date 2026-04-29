#  Drakkar-Software OctoBot-Evaluators
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

import typing

import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.time_frame_manager as time_frame_manager

import octobot_evaluators.constants as constants
import octobot_evaluators.enums as enums
import octobot_evaluators.evaluators as evaluator
import octobot_evaluators.evaluators.channel as evaluator_channels
import octobot_evaluators.matrix as matrix

import octobot_tentacles_manager.api as api
import octobot_tentacles_manager.configuration as tm_configuration


class StrategyEvaluator(evaluator.AbstractEvaluator):
    __metaclass__ = evaluator.AbstractEvaluator

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.consumer_instance = None
        self.strategy_time_frames = []
        self.evaluations_last_updates = {}
        self.allowed_time_delta = None

        # caches
        self.available_evaluators_cache = {}
        self.available_time_frames_cache = {}
        self.available_node_paths_cache = {}

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        self.UI.user_input(constants.STRATEGIES_REQUIRED_TIME_FRAME, common_enums.UserInputTypes.MULTIPLE_OPTIONS,
                           [common_enums.TimeFrames.ONE_HOUR.value],
                           inputs, options=[tf.value for tf in common_enums.TimeFrames],
                           title="Time frame: The time frame to observe in order to spot changes.")

    async def start(self, bot_id: str) -> bool:
        """
        Default Strategy start: to be overwritten
        Subscribe to Matrix notification from self.symbols and self.time_frames
        :return: success of the evaluator's start
        """
        await super().start(bot_id)
        self.consumer_instance = await evaluator_channels.get_chan(constants.MATRIX_CHANNEL,
                                                                   self.matrix_id).new_consumer(
            self.strategy_matrix_callback,
            priority_level=self.priority_level,
            exchange_name=self.exchange_name if self.exchange_name else common_constants.CHANNEL_WILDCARD)
        self._init_exchange_allowed_time_delta(self.exchange_name, self.matrix_id)
        return True

    async def strategy_completed(self,
                                 cryptocurrency: typing.Optional[str] = None,
                                 symbol: typing.Optional[str] = None,
                                 time_frame: typing.Optional[str] = None,
                                 eval_note = None,
                                 eval_time: int = 0,
                                 notify: bool = True) -> None:
        """
        Main async method to notify that a strategy has updated its evaluation
        :param cryptocurrency: evaluated cryptocurrency
        :param symbol: evaluated symbol
        :param time_frame: evaluated time frame
        :param eval_note: if None = self.eval_note
        :param eval_time: the time of the evaluation if relevant, default is 0
        :param notify: if true, will trigger matrix consumers
        :return: None
        """
        return await self.evaluation_completed(cryptocurrency=cryptocurrency,
                                               symbol=symbol,
                                               time_frame=time_frame,
                                               eval_note=eval_note,
                                               eval_time=eval_time,
                                               notify=notify,
                                               origin_consumer=self.consumer_instance)

    def is_evaluator_cycle_complete(self, matrix_id, evaluator_name, evaluator_type, exchange_name,
                                    cryptocurrency, symbol, time_frame) -> bool:
        """
        :return: True if the strategy is to be waken up by evaluators of the given type at the moment of this call.
        This avoids partial time frame updates wakeup.
        Override if necessary
        """
        # 1. Ensure this evaluation has not already been sent
        # 2. Ensure every evaluator of the given type form this time frame are valid
        return not self._already_sent_this_technical_evaluation(matrix_id,
                                                                evaluator_name,
                                                                evaluator_type,
                                                                exchange_name,
                                                                cryptocurrency,
                                                                symbol,
                                                                time_frame) and \
               self._are_every_evaluation_valid_and_up_to_date(matrix_id,
                                                               evaluator_name,
                                                               evaluator_type,
                                                               exchange_name,
                                                               cryptocurrency,
                                                               symbol,
                                                               time_frame)

    def clear_cache(self):
        self.available_evaluators_cache = {}
        self.available_time_frames_cache = {}
        self.available_node_paths_cache = {}

    async def stop(self) -> None:
        await super().stop()
        if self.consumer_instance:
            await evaluator_channels.get_chan(constants.MATRIX_CHANNEL,
                                              self.matrix_id).remove_consumer(self.consumer_instance)
            self.consumer_instance = None

    def get_full_cycle_evaluator_types(self) -> tuple:
        # returns a tuple as it is faster to create than a list
        return enums.EvaluatorMatrixTypes.TA.value,

    async def strategy_matrix_callback(self,
                                       matrix_id,
                                       evaluator_name,
                                       evaluator_type,
                                       eval_note,
                                       eval_note_type,
                                       eval_note_description,
                                       eval_note_metadata,
                                       exchange_name,
                                       cryptocurrency,
                                       symbol,
                                       time_frame):
        # if this callback is from a technical evaluator: ensure strategy should be notified at this moment
        for full_cycle_evaluator in self.get_full_cycle_evaluator_types():
            if evaluator_type == full_cycle_evaluator:
                # ensure this time frame is within the strategy's time frames
                if time_frame is None or common_enums.TimeFrames(time_frame) not in self.strategy_time_frames or \
                        not self.is_evaluator_cycle_complete(matrix_id,
                                                             evaluator_name,
                                                             evaluator_type,
                                                             exchange_name,
                                                             cryptocurrency,
                                                             symbol,
                                                             time_frame):
                    # do not call the strategy
                    return
        await self.matrix_callback(
            matrix_id,
            evaluator_name,
            evaluator_type,
            eval_note,
            eval_note_type,
            eval_note_description,
            eval_note_metadata,
            exchange_name,
            cryptocurrency,
            symbol,
            time_frame
        )

    async def matrix_callback(self,
                              matrix_id,
                              evaluator_name,
                              evaluator_type,
                              eval_note,
                              eval_note_type,
                              eval_note_description,
                              eval_note_metadata,
                              exchange_name,
                              cryptocurrency,
                              symbol,
                              time_frame):
        # To be used to trigger an evaluation
        # Do not forget to check if evaluator_name is self.name
        pass

    def _are_every_evaluation_valid_and_up_to_date(self,
                                                   matrix_id,
                                                   evaluator_name,
                                                   evaluator_type,
                                                   exchange_name,
                                                   cryptocurrency,
                                                   symbol,
                                                   time_frame,
                                                   can_retry=True):
        to_validate_node_paths = self._get_available_node_paths(matrix_id,
                                                                evaluator_type,
                                                                exchange_name,
                                                                cryptocurrency,
                                                                symbol,
                                                                use_cache=True)
        current_time = self._get_exchange_current_time(exchange_name, matrix_id)
        # ensure all evaluations are valid (do not trigger on an expired evaluation)
        try:
            if all(matrix.is_tentacle_value_valid(self.matrix_id, evaluation_node_path,
                                                  timestamp=current_time,
                                                  delta=self.allowed_time_delta)
                   for evaluation_node_path in to_validate_node_paths):
                self._save_last_evaluation(matrix_id, exchange_name, evaluator_type, evaluator_name,
                                           cryptocurrency, symbol, time_frame)
                return True
            return False
        except KeyError:
            self.clear_cache()
            if can_retry:
                return self._are_every_evaluation_valid_and_up_to_date(matrix_id,
                                                                       evaluator_name,
                                                                       evaluator_type,
                                                                       exchange_name,
                                                                       cryptocurrency,
                                                                       symbol,
                                                                       time_frame,
                                                                       can_retry=False)
            raise

    def _get_available_node_paths(self,
                                  matrix_id,
                                  evaluator_type,
                                  exchange_name,
                                  cryptocurrency,
                                  symbol,
                                  use_cache=True):
        if use_cache:
            try:
                return self.available_node_paths_cache[matrix_id][exchange_name][evaluator_type][cryptocurrency][symbol]
            except KeyError:
                # No cache usage here to be use to refresh data
                node_paths = self._inner_get_available_node_paths(matrix_id, evaluator_type, exchange_name,
                                                                  cryptocurrency, symbol, use_cache=False)
                if matrix_id not in self.available_node_paths_cache:
                    self.available_node_paths_cache[matrix_id] = {}
                if exchange_name not in self.available_node_paths_cache[matrix_id]:
                    self.available_node_paths_cache[matrix_id][exchange_name] = {}
                if evaluator_type not in self.available_node_paths_cache[matrix_id][exchange_name]:
                    self.available_node_paths_cache[matrix_id][exchange_name][evaluator_type] = {}
                if cryptocurrency not in self.available_node_paths_cache[matrix_id][exchange_name][evaluator_type]:
                    self.available_node_paths_cache[matrix_id][exchange_name][evaluator_type][cryptocurrency] = {}
                self.available_node_paths_cache[matrix_id][exchange_name][evaluator_type][cryptocurrency][symbol] = \
                    node_paths
                return node_paths
        return self._inner_get_available_node_paths(matrix_id, evaluator_type, exchange_name,
                                                    cryptocurrency, symbol, use_cache=use_cache)

    def _inner_get_available_node_paths(self, matrix_id, evaluator_type, exchange_name, cryptocurrency, symbol,
                                        use_cache=True):
        paths = []
        for time_frame in self.get_available_time_frames(matrix_id, exchange_name, evaluator_type,
                                                         cryptocurrency, symbol, use_cache=use_cache):
            if common_enums.TimeFrames(time_frame) in self.strategy_time_frames:
                for evaluator_name in self._get_available_evaluators(matrix_id, exchange_name, evaluator_type,
                                                                     use_cache=use_cache):
                    path = matrix.get_matrix_default_value_path(tentacle_name=evaluator_name,
                                                                tentacle_type=evaluator_type,
                                                                exchange_name=exchange_name,
                                                                cryptocurrency=cryptocurrency,
                                                                symbol=symbol,
                                                                time_frame=time_frame)
                    if matrix.get_tentacle_node(matrix_id, path) is not None:
                        paths.append(path)
        return paths

    def _save_last_evaluation(self, matrix_id, exchange_name, evaluator_type, tentacle_name,
                              cryptocurrency, symbol, time_frame):
        self._set_last_evaluation_time(exchange_name,
                                       evaluator_type,
                                       cryptocurrency,
                                       symbol,
                                       time_frame,
                                       matrix.get_tentacle_eval_time(matrix_id,
                                                                     matrix.get_matrix_default_value_path(
                                                                         tentacle_name=tentacle_name,
                                                                         tentacle_type=evaluator_type,
                                                                         exchange_name=exchange_name,
                                                                         cryptocurrency=cryptocurrency,
                                                                         symbol=symbol,
                                                                         time_frame=time_frame)
                                                                     )
                                       )

    def _already_sent_this_technical_evaluation(self, matrix_id, evaluator, evaluator_type, exchange_name,
                                                cryptocurrency, symbol, time_frame):
        try:
            update_time = matrix.get_tentacle_eval_time(matrix_id,
                                                        matrix.get_matrix_default_value_path(
                                                            tentacle_name=evaluator,
                                                            tentacle_type=evaluator_type,
                                                            exchange_name=exchange_name,
                                                            cryptocurrency=cryptocurrency,
                                                            symbol=symbol,
                                                            time_frame=time_frame)
                                                        )
            return self.evaluations_last_updates[exchange_name][evaluator_type][cryptocurrency][symbol][time_frame] \
                   == update_time
        except KeyError:
            return False

    def _set_last_evaluation_time(self, exchange_name, evaluator_type, cryptocurrency, symbol, time_frame, value):
        try:
            self.evaluations_last_updates[exchange_name][evaluator_type][cryptocurrency][symbol][time_frame] = value
        except KeyError:
            if exchange_name not in self.evaluations_last_updates:
                self.evaluations_last_updates[exchange_name] = {}
            if evaluator_type not in self.evaluations_last_updates[exchange_name]:
                self.evaluations_last_updates[exchange_name][evaluator_type] = {}
            if cryptocurrency not in self.evaluations_last_updates[exchange_name][evaluator_type]:
                self.evaluations_last_updates[exchange_name][evaluator_type][cryptocurrency] = {}
            if symbol not in self.evaluations_last_updates[exchange_name][evaluator_type][cryptocurrency]:
                self.evaluations_last_updates[exchange_name][evaluator_type][cryptocurrency][symbol] = {}
            self.evaluations_last_updates[exchange_name][evaluator_type][cryptocurrency][symbol] = {
                time_frame: value
            }

    def _init_exchange_allowed_time_delta(self, exchange_name, matrix_id):
        try:
            import octobot_trading.api as exchange_api
            exchange_manager = exchange_api.get_exchange_manager_from_exchange_name_and_id(
                exchange_name,
                exchange_api.get_exchange_id_from_matrix_id(exchange_name, matrix_id)
            )
            self.allowed_time_delta = exchange_api.get_exchange_allowed_time_lag(exchange_manager)
        except ImportError:
            self.logger.error("Strategy requires OctoBot-Trading package installed")

    async def evaluators_callback(self,
                                  matrix_id,
                                  evaluator_name,
                                  evaluator_type,
                                  exchange_name,
                                  cryptocurrency,
                                  symbol,
                                  time_frame,
                                  data):
        # Used to communicate between evaluators
        if data[constants.EVALUATOR_CHANNEL_DATA_ACTION] == constants.RESET_EVALUATION:
            for time_frame in data[constants.EVALUATOR_CHANNEL_DATA_TIME_FRAMES]:
                self._set_last_evaluation_time(exchange_name, enums.EvaluatorMatrixTypes.TA.value,
                                               cryptocurrency, symbol, time_frame.value, None)

    def _get_available_evaluators(self, matrix_id, exchange_name, tentacle_type, use_cache=True):
        if use_cache:
            try:
                return self.available_evaluators_cache[matrix_id][exchange_name][tentacle_type]
            except KeyError:
                available_evaluators = matrix.get_node_children_by_names_at_path(
                    matrix_id, matrix.get_tentacle_path(exchange_name=exchange_name, tentacle_type=tentacle_type)
                ).keys()
                if matrix_id not in self.available_evaluators_cache:
                    self.available_evaluators_cache[matrix_id] = {}
                if exchange_name not in self.available_evaluators_cache[matrix_id]:
                    self.available_evaluators_cache[matrix_id][exchange_name] = {}
                self.available_evaluators_cache[matrix_id][exchange_name][tentacle_type] = available_evaluators
                return available_evaluators
        return matrix.get_node_children_by_names_at_path(
            matrix_id, matrix.get_tentacle_path(exchange_name=exchange_name, tentacle_type=tentacle_type)
        ).keys()

    def get_available_time_frames(self,
                                  matrix_id,
                                  exchange_name=None,
                                  tentacle_type=None,
                                  cryptocurrency=None,
                                  symbol=None,
                                  use_cache=True):
        if use_cache:
            try:
                return self.available_time_frames_cache[matrix_id][exchange_name][tentacle_type][cryptocurrency][symbol]
            except KeyError:
                available_time_frames = matrix.get_available_time_frames(
                    matrix_id, exchange_name, tentacle_type, cryptocurrency, symbol)
                if matrix_id not in self.available_time_frames_cache:
                    self.available_time_frames_cache[matrix_id] = {}
                if exchange_name not in self.available_time_frames_cache[matrix_id]:
                    self.available_time_frames_cache[matrix_id][exchange_name] = {}
                if tentacle_type not in self.available_time_frames_cache[matrix_id][exchange_name]:
                    self.available_time_frames_cache[matrix_id][exchange_name][tentacle_type] = {}
                if cryptocurrency not in self.available_time_frames_cache[matrix_id][exchange_name][tentacle_type]:
                    self.available_time_frames_cache[matrix_id][exchange_name][tentacle_type][cryptocurrency] = {}
                self.available_time_frames_cache[matrix_id][exchange_name][tentacle_type][cryptocurrency][symbol] = \
                    available_time_frames
                return available_time_frames
        return matrix.get_available_time_frames(matrix_id, exchange_name, tentacle_type, cryptocurrency, symbol)

    def _get_tentacle_registration_topic(self, all_symbols_by_crypto_currencies, time_frames, real_time_time_frames):
        strategy_currencies, symbols, self.strategy_time_frames = super()._get_tentacle_registration_topic(
            all_symbols_by_crypto_currencies,
            time_frames,
            real_time_time_frames)
        # by default no time frame registration for strategies
        return strategy_currencies, symbols, [self.time_frame]

    @classmethod
    def get_required_time_frames(cls, config: dict,
                                 tentacles_setup_config: tm_configuration.TentaclesSetupConfiguration,
                                 strategy_config=None):
        if constants.CONFIG_FORCED_TIME_FRAME in config:
            return time_frame_manager.parse_time_frames(config[constants.CONFIG_FORCED_TIME_FRAME])
        strategy_config: dict = strategy_config or api.get_tentacle_config(tentacles_setup_config, cls)
        if constants.STRATEGIES_REQUIRED_TIME_FRAME in strategy_config:
            return time_frame_manager.parse_time_frames(strategy_config[constants.STRATEGIES_REQUIRED_TIME_FRAME])
        else:
            raise Exception(f"'{constants.STRATEGIES_REQUIRED_TIME_FRAME}' is missing in configuration file")

    @classmethod
    def get_required_evaluators(cls, tentacles_config: tm_configuration.TentaclesSetupConfiguration,
                                strategy_config: dict = None) -> list:
        """
        :param tentacles_config: the tentacles config to find the current strategy config from
        :param strategy_config: the strategy configuration dict
        :return: the list of required evaluators, [CONFIG_WILDCARD] means any evaluator
        """
        strategy_config: dict = strategy_config or api.get_tentacle_config(tentacles_config, cls)
        if constants.STRATEGIES_REQUIRED_EVALUATORS in strategy_config:
            return strategy_config[constants.STRATEGIES_REQUIRED_EVALUATORS]
        else:
            raise Exception(f"'{constants.STRATEGIES_REQUIRED_EVALUATORS}' is missing in configuration file")

    @classmethod
    def get_compatible_evaluators_types(cls, tentacles_config: tm_configuration.TentaclesSetupConfiguration,
                                        strategy_config: dict = None) -> list:
        """
        :param tentacles_config: the tentacles config to find the current strategy config from
        :param strategy_config: the strategy configuration dict
        :return: the list of compatible evaluator type, [CONFIG_WILDCARD] means any type
        """
        strategy_config: dict = strategy_config or api.get_tentacle_config(tentacles_config, cls)
        if constants.STRATEGIES_COMPATIBLE_EVALUATOR_TYPES in strategy_config:
            return strategy_config[constants.STRATEGIES_COMPATIBLE_EVALUATOR_TYPES]
        return [common_constants.CONFIG_WILDCARD]

    @classmethod
    def get_default_evaluators(cls, tentacles_config: tm_configuration.TentaclesSetupConfiguration,
                               strategy_config: dict = None):
        strategy_config: dict = strategy_config or api.get_tentacle_config(tentacles_config, cls)
        if constants.TENTACLE_DEFAULT_CONFIG in strategy_config:
            return strategy_config[constants.TENTACLE_DEFAULT_CONFIG]
        else:
            required_evaluators = cls.get_required_evaluators(tentacles_config, strategy_config)
            if required_evaluators == common_constants.CONFIG_WILDCARD:
                return []
            return required_evaluators
