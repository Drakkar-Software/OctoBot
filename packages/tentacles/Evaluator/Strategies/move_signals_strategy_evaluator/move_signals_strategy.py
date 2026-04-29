#  Drakkar-Software OctoBot-Tentacles
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
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enum
import octobot_evaluators.api.matrix as evaluators_api
import octobot_evaluators.evaluators.channel as evaluators_channel
import octobot_evaluators.matrix as matrix
import octobot_evaluators.enums as evaluators_enums
import octobot_evaluators.errors as errors
import octobot_evaluators.evaluators as evaluators
import octobot_trading.api as trading_api
import tentacles.Evaluator.TA as TA


class MoveSignalsStrategyEvaluator(evaluators.StrategyEvaluator):
    SIGNAL_CLASS_NAME = TA.KlingerOscillatorMomentumEvaluator.get_name()
    WEIGHT_CLASS_NAME = TA.BBMomentumEvaluator.get_name()

    SHORT_PERIOD_WEIGHT = 4
    MEDIUM_PERIOD_WEIGHT = 3
    LONG_PERIOD_WEIGHT = 3

    SIGNAL_MINIMUM_THRESHOLD = 0.15

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.evaluation_time_frames = [commons_enum.TimeFrames.THIRTY_MINUTES.value,
                                       commons_enum.TimeFrames.ONE_HOUR.value,
                                       commons_enum.TimeFrames.FOUR_HOURS.value]
        self.weights_and_period_evals = []
        self.short_period_eval = None
        self.medium_period_eval = None
        self.long_period_eval = None

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        pass

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
        if evaluator_type == evaluators_enums.EvaluatorMatrixTypes.REAL_TIME.value:
            # trigger re-evaluation
            exchange_id = trading_api.get_exchange_id_from_matrix_id(exchange_name, matrix_id)
            await evaluators_channel.trigger_technical_evaluators_re_evaluation_with_updated_data(matrix_id,
                                                                                                  evaluator_name,
                                                                                                  evaluator_type,
                                                                                                  exchange_name,
                                                                                                  cryptocurrency,
                                                                                                  symbol,
                                                                                                  exchange_id,
                                                                                                  self.strategy_time_frames)
            # do not continue this evaluation
            return
        elif evaluator_type == evaluators_enums.EvaluatorMatrixTypes.TA.value:
            try:
                TA_by_timeframe = {
                    available_time_frame: matrix.get_evaluations_by_evaluator(
                        matrix_id,
                        exchange_name,
                        evaluators_enums.EvaluatorMatrixTypes.TA.value,
                        cryptocurrency,
                        symbol,
                        available_time_frame.value,
                        allow_missing=False,
                        allowed_values=[commons_constants.START_PENDING_EVAL_NOTE])
                    for available_time_frame in self.strategy_time_frames
                }

                self._refresh_evaluations(TA_by_timeframe)
                self._compute_final_evaluation()
                await self.strategy_completed(cryptocurrency, symbol)

            except errors.UnsetTentacleEvaluation as e:
                self.logger.debug(f"Tentacles evaluation initialization: not ready yet for a strategy update ({e})")
            except KeyError as e:
                self.logger.exception(e, True, f"Missing {e} evaluation in matrix for {symbol} on {time_frame}, "
                                      f"did you activate the required evaluator ?")

    def _compute_final_evaluation(self):
        weights = 0
        composite_evaluation = 0
        for weight, evaluation in self.weights_and_period_evals:
            composite_evaluation += self._compute_fractal_evaluation(evaluation, weight)
            weights += weight
        self.eval_note = composite_evaluation / weights

    @staticmethod
    def _compute_fractal_evaluation(signal_with_weight, multiplier):
        if signal_with_weight.signal != commons_constants.START_PENDING_EVAL_NOTE \
                and signal_with_weight.weight != commons_constants.START_PENDING_EVAL_NOTE:
            evaluation_sign = signal_with_weight.signal * signal_with_weight.weight
            if abs(signal_with_weight.signal) >= MoveSignalsStrategyEvaluator.SIGNAL_MINIMUM_THRESHOLD \
                    and evaluation_sign > 0:
                eval_side = 1 if signal_with_weight.signal > 0 else -1
                signal_strength = 2 * signal_with_weight.signal * signal_with_weight.weight
                weighted_eval = min(signal_strength, 1)
                return weighted_eval * multiplier * eval_side
        return 0

    def _refresh_evaluations(self, TA_by_timeframe):
        for _, evaluation in self.weights_and_period_evals:
            evaluation.refresh_evaluation(TA_by_timeframe)

    def _get_tentacle_registration_topic(self, all_symbols_by_crypto_currencies, time_frames, real_time_time_frames):
        currencies, symbols, time_frames = super()._get_tentacle_registration_topic(all_symbols_by_crypto_currencies,
                                                                                    time_frames,
                                                                                    real_time_time_frames)
        # register evaluation fractals based on available time frames
        self._register_time_frame(commons_enum.TimeFrames.THIRTY_MINUTES, self.SHORT_PERIOD_WEIGHT)
        self._register_time_frame(commons_enum.TimeFrames.ONE_HOUR, self.MEDIUM_PERIOD_WEIGHT)
        self._register_time_frame(commons_enum.TimeFrames.FOUR_HOURS, self.LONG_PERIOD_WEIGHT)
        return currencies, symbols, time_frames

    def _register_time_frame(self, time_frame, weight):
        if time_frame in self.strategy_time_frames:
            self.weights_and_period_evals.append((weight,
                                                  SignalWithWeight(time_frame)))
        else:
            self.logger.warning(f"Missing {time_frame.value} time frame on {self.exchange_name}, "
                                f"this strategy will not work at its optimal potential.")


class SignalWithWeight:

    def __init__(self, time_frame):
        self.time_frame = time_frame
        self.signal = commons_constants.START_PENDING_EVAL_NOTE
        self.weight = commons_constants.START_PENDING_EVAL_NOTE

    def reset_evaluation(self):
        self.signal = commons_constants.START_PENDING_EVAL_NOTE
        self.weight = commons_constants.START_PENDING_EVAL_NOTE

    def refresh_evaluation(self, TA_by_timeframe):
        self.reset_evaluation()
        self.signal = evaluators_api.get_value(
            TA_by_timeframe[self.time_frame][MoveSignalsStrategyEvaluator.SIGNAL_CLASS_NAME])
        self.weight = evaluators_api.get_value(
            TA_by_timeframe[self.time_frame][MoveSignalsStrategyEvaluator.WEIGHT_CLASS_NAME])
