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
import typing

import octobot_commons.constants as common_constants
import octobot_commons.enums as commons_enums
import octobot_commons.evaluators_util as evaluators_util
import octobot_evaluators.matrix as matrix
import octobot_evaluators.enums as evaluators_enums
import octobot_evaluators.evaluators as evaluators
import octobot_services.api.services as services_api
import tentacles.Services.Services_bases

from tentacles.Agent.teams.simple_ai_evaluator_agents_team import SimpleAIEvaluatorAgentsTeam, DeepAgentEvaluatorTeam


class BaseLLMAIStrategyEvaluator(evaluators.StrategyEvaluator):
    """
    Base class for LLM-powered AI Strategy Evaluators.
    Contains shared configuration and agent execution logic.
    """

    PROMPT_KEY = "prompt"
    MODEL_KEY = "model"
    MAX_TOKENS_KEY = "max_tokens"
    TEMPERATURE_KEY = "temperature"
    OUTPUT_FORMAT_KEY = "output_format"
    EVALUATOR_TYPES_KEY = "evaluator_types"
    USE_DEEP_AGENT_KEY = "use_deep_agent"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = None
        self.prompt = None
        self.max_tokens = None
        self.temperature = None
        self.output_format = "with_confidence"
        self.evaluator_types = [
            evaluators_enums.EvaluatorMatrixTypes.TA.value,
            evaluators_enums.EvaluatorMatrixTypes.SOCIAL.value,
            evaluators_enums.EvaluatorMatrixTypes.REAL_TIME.value,
        ]

    def init_user_inputs(self, inputs: dict) -> None:
        super().init_user_inputs(inputs)
        default_config = self.get_default_config()
        self.prompt = self.UI.user_input(
            self.PROMPT_KEY,
            commons_enums.UserInputTypes.TEXT,
            default_config[self.PROMPT_KEY],
            inputs,
            title="Custom prompt for LLM analysis. Leave empty to use default.",
        )
        self.model = self.UI.user_input(
            self.MODEL_KEY,
            commons_enums.UserInputTypes.TEXT,
            default_config[self.MODEL_KEY],
            inputs,
            title="LLM model to use for analysis.",
        )
        self.max_tokens = self.UI.user_input(
            self.MAX_TOKENS_KEY,
            commons_enums.UserInputTypes.INT,
            default_config[self.MAX_TOKENS_KEY],
            inputs,
            min_val=100,
            max_val=10000,
            title="Maximum tokens for LLM response.",
        )
        self.temperature = self.UI.user_input(
            self.TEMPERATURE_KEY,
            commons_enums.UserInputTypes.FLOAT,
            default_config[self.TEMPERATURE_KEY],
            inputs,
            min_val=0.0,
            max_val=1.0,
            title="Temperature for LLM randomness (0.0 = deterministic, 1.0 = very random).",
        )
        self.use_deep_agent = self.UI.user_input(
            self.USE_DEEP_AGENT_KEY,
            commons_enums.UserInputTypes.BOOLEAN,
            default_config.get(self.USE_DEEP_AGENT_KEY, False),
            inputs,
            title="Use Deep Agent implementation (requires deepagents package). Default: use traditional AI agent.",
        )
        self.evaluator_types = self.UI.user_input(
            self.EVALUATOR_TYPES_KEY,
            commons_enums.UserInputTypes.MULTIPLE_OPTIONS,
            default_config[self.EVALUATOR_TYPES_KEY],
            inputs,
            options=[
                evaluators_enums.EvaluatorMatrixTypes.TA.value,
                evaluators_enums.EvaluatorMatrixTypes.SOCIAL.value,
                evaluators_enums.EvaluatorMatrixTypes.REAL_TIME.value,
            ],
            title="Evaluator types to include in analysis.",
        )
        self.output_format = self.UI.user_input(
            self.OUTPUT_FORMAT_KEY,
            commons_enums.UserInputTypes.OPTIONS,
            default_config[self.OUTPUT_FORMAT_KEY],
            inputs,
            options=["standard", "with_confidence"],
            title="Output format: standard (eval_note and description) or with_confidence (includes confidence level).",
        )

    @classmethod
    def get_default_config(cls, time_frames: typing.Optional[list[str]] = None) -> dict:
        return {
            cls.PROMPT_KEY: "",
            cls.MODEL_KEY: None,
            cls.MAX_TOKENS_KEY: None,
            cls.TEMPERATURE_KEY: None,
            cls.EVALUATOR_TYPES_KEY: [
                evaluators_enums.EvaluatorMatrixTypes.TA.value,
                evaluators_enums.EvaluatorMatrixTypes.SOCIAL.value,
                evaluators_enums.EvaluatorMatrixTypes.REAL_TIME.value,
            ],
            cls.OUTPUT_FORMAT_KEY: "standard",
        }

    def get_full_cycle_evaluator_types(self) -> tuple:
        # returns a tuple as it is faster to create than a list
        return tuple(self.evaluator_types)

    async def _get_ai_service(self):
        ai_service = await services_api.get_ai_service(
            is_backtesting=self._is_in_backtesting()
        )
        if not ai_service:
            self.logger.error("AIService not available, cannot perform LLM analysis")
            return None
        return ai_service

    async def _run_agents_analysis(
        self,
        aggregated_data: dict,
        missing_data_types: list,
        ai_service,
    ) -> tuple[float | str, str]:
        """
        Run strategy agents on aggregated data using the SimpleAIEvaluatorAgentsTeam.
        
        Returns:
            Tuple of (eval_note, eval_note_description).
        """
        # Determine which agents to include based on available data
        include_ta = evaluators_enums.EvaluatorMatrixTypes.TA.value in aggregated_data
        include_sentiment = evaluators_enums.EvaluatorMatrixTypes.SOCIAL.value in aggregated_data
        include_realtime = evaluators_enums.EvaluatorMatrixTypes.REAL_TIME.value in aggregated_data
        
        if not any([include_ta, include_sentiment, include_realtime]):
            self.logger.error("No valid data available for any agent")
            return common_constants.START_PENDING_EVAL_NOTE, "Error: No valid data available"
        
        # Create and run the team based on use_deep_agent config
        team_class = DeepAgentEvaluatorTeam if self.use_deep_agent else SimpleAIEvaluatorAgentsTeam
        team = team_class(
            ai_service=ai_service,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            include_ta=include_ta,
            include_sentiment=include_sentiment,
            include_realtime=include_realtime,
        )
        
        try:
            eval_note, eval_note_description = await team.run_with_data(
                aggregated_data=aggregated_data,
                missing_data_types=missing_data_types,
            )
            
            return eval_note, eval_note_description
            
        except Exception as e:
            self.logger.exception(f"SimpleAIEvaluatorAgentsTeam failed: {e}")
            return common_constants.START_PENDING_EVAL_NOTE, f"Error: Agent team failed: {str(e)}"


class CryptoLLMAIStrategyEvaluator(BaseLLMAIStrategyEvaluator):
    """
    LLM AI Strategy Evaluator for cryptocurrency-specific evaluations.
    Evaluates individual cryptocurrencies (symbol=wildcard, cryptocurrency is specific).
    Matrix evaluations are published with cryptocurrency set (not None).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pending_evaluations = {}  # {cryptocurrency: {(symbol, timeframe): data}}
        self._expected_symbols_timeframes = {}  # {cryptocurrency: set of (symbol, timeframe)}
        self._completed_cryptocurrencies = set()  # Track which cryptocurrencies have been evaluated

    async def matrix_callback(
        self,
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
        time_frame,
        **kwargs,
    ):
        if evaluator_type not in self.evaluator_types:
            return

        # Skip global evaluations (cryptocurrency=None) - those are for GlobalLLMAIStrategyEvaluator
        if cryptocurrency is None:
            return

        # Check if we have already completed evaluation for this cryptocurrency
        if cryptocurrency in self._completed_cryptocurrencies:
            return

        # Initialize pending evaluations for this cryptocurrency if needed
        if cryptocurrency not in self._pending_evaluations:
            self._pending_evaluations[cryptocurrency] = {}
            self._expected_symbols_timeframes[cryptocurrency] = set()

        # Track this symbol/timeframe combination
        eval_key = (symbol, time_frame)
        self._expected_symbols_timeframes[cryptocurrency].add(eval_key)

        # Check if we have sufficient data for this symbol/timeframe
        available_eval_types = []
        for eval_type in self.evaluator_types:
            if self._are_every_evaluation_valid_and_up_to_date(
                matrix_id,
                evaluator_name,
                eval_type,
                exchange_name,
                cryptocurrency,
                symbol,
                time_frame,
            ):
                available_eval_types.append(eval_type)

        # Require at least one evaluator type to have data
        if not available_eval_types:
            return

        # Store this evaluation data
        self._pending_evaluations[cryptocurrency][eval_key] = {
            'matrix_id': matrix_id,
            'exchange_name': exchange_name,
            'symbol': symbol,
            'time_frame': time_frame,
            'available_eval_types': available_eval_types,
        }

        # Check if we have data for all expected symbols/timeframes
        # Evaluate when we have at least one complete set
        if len(self._pending_evaluations[cryptocurrency]) < 1:
            return

        # Trigger evaluation
        await self._evaluate_for_cryptocurrency(
            matrix_id=matrix_id,
            exchange_name=exchange_name,
            cryptocurrency=cryptocurrency,
        )

    async def _evaluate_for_cryptocurrency(
        self,
        matrix_id: str,
        exchange_name: str,
        cryptocurrency: str,
    ):
        """
        Perform evaluation for a specific cryptocurrency.
        """
        # Aggregate data by evaluator type across all symbols and timeframes
        aggregated_data = {}
        missing_data_types = []
        all_eval_types = set()

        # Collect all available eval types from all pending evaluations
        for eval_data in self._pending_evaluations[cryptocurrency].values():
            all_eval_types.update(eval_data['available_eval_types'])

        for eval_type in self.evaluator_types:
            if eval_type in all_eval_types:
                all_evaluations = {}

                # Collect evaluations from all symbols and timeframes
                for eval_key, eval_data in self._pending_evaluations[cryptocurrency].items():
                    if eval_type not in eval_data['available_eval_types']:
                        continue

                    symbol_tf = eval_key[0]  # symbol
                    time_frame_tf = eval_key[1]  # timeframe
                    matrix_id_tf = eval_data['matrix_id']
                    exchange_name_tf = eval_data['exchange_name']

                    if eval_type == evaluators_enums.EvaluatorMatrixTypes.TA.value:
                        # TA evaluators need time_frame parameter
                        evaluations = matrix.get_evaluations_by_evaluator(
                            matrix_id_tf,
                            exchange_name_tf,
                            eval_type,
                            cryptocurrency,
                            symbol_tf,
                            time_frame_tf,
                        )
                    elif eval_type == evaluators_enums.EvaluatorMatrixTypes.SOCIAL.value:
                        # Social evaluators - get those for the same cryptocurrency and symbol
                        evaluations = matrix.get_evaluations_by_evaluator(
                            matrix_id_tf, exchange_name_tf, eval_type, cryptocurrency, symbol_tf
                        )
                        # Also get social evaluators by cryptocurrency only
                        evaluations.update(
                            matrix.get_evaluations_by_evaluator(
                                matrix_id_tf, exchange_name_tf, eval_type, cryptocurrency
                            )
                        )
                    elif eval_type == evaluators_enums.EvaluatorMatrixTypes.REAL_TIME.value:
                        # Real-time evaluators need time_frame parameter
                        evaluations = matrix.get_evaluations_by_evaluator(
                            matrix_id_tf,
                            exchange_name_tf,
                            eval_type,
                            cryptocurrency,
                            symbol_tf,
                            time_frame_tf,
                        )
                    else:
                        # Fallback for any other evaluator types
                        evaluations = matrix.get_evaluations_by_evaluator(
                            matrix_id_tf,
                            exchange_name_tf,
                            eval_type,
                            cryptocurrency,
                            symbol_tf,
                            time_frame_tf,
                        )

                    all_evaluations.update(evaluations)

                valid_evaluations = [
                    {
                        "eval_note": ev.node_value,
                        "eval_note_description": ev.node_description or "",
                    }
                    for ev in all_evaluations.values()
                    if evaluators_util.check_valid_eval_note(ev.node_value)
                ]
                if valid_evaluations:
                    aggregated_data[eval_type] = valid_evaluations
                else:
                    missing_data_types.append(eval_type)
            else:
                missing_data_types.append(eval_type)

        if not aggregated_data:
            return

        ai_service = await self._get_ai_service()
        if not ai_service:
            self.eval_note = 0
            final_eval_note_description = "Error: AIService not available"
            self._completed_cryptocurrencies.add(cryptocurrency)
            await self.evaluation_completed(
                cryptocurrency=cryptocurrency,
                symbol=None,
                time_frame=None,
                eval_note=self.eval_note,
                eval_note_description=final_eval_note_description,
                eval_time=0,
                notify=True,
                origin_consumer=self.consumer_instance,
            )
            return

        self.eval_note, final_eval_note_description = await self._run_agents_analysis(
            aggregated_data, missing_data_types, ai_service
        )

        # Mark this cryptocurrency as completed
        self._completed_cryptocurrencies.add(cryptocurrency)

        # Publish evaluation on cryptocurrency level (no symbol, no timeframe)
        await self.evaluation_completed(
            cryptocurrency=cryptocurrency,
            symbol=None,
            time_frame=None,
            eval_note=self.eval_note,
            eval_note_description=final_eval_note_description,
            eval_time=0,
            notify=True,
            origin_consumer=self.consumer_instance,
        )

        # Clean up pending evaluations for this cryptocurrency
        if cryptocurrency in self._pending_evaluations:
            del self._pending_evaluations[cryptocurrency]
        if cryptocurrency in self._expected_symbols_timeframes:
            del self._expected_symbols_timeframes[cryptocurrency]


class GlobalLLMAIStrategyEvaluator(BaseLLMAIStrategyEvaluator):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_evaluating = False


    @classmethod
    def get_is_cryptocurrencies_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency dependant else False
        """
        return False

    async def matrix_callback(
        self,
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
        time_frame,
        **kwargs,
    ):
        if evaluator_type not in self.evaluator_types:
            return

        if cryptocurrency is None or (self.eval_note == common_constants.START_PENDING_EVAL_NOTE and not self._is_evaluating):
            self._is_evaluating = True
            # Only evaluate if it's a global evaluation or if we haven't evaluated yet
            await self._evaluate_global(
                matrix_id=matrix_id,
                exchange_name=exchange_name,
            )
            self._is_evaluating = False

    async def _evaluate_global(
        self,
        matrix_id: str,
        exchange_name: str,
    ):
        """
        Perform global market evaluation across all cryptocurrencies.
        """
        aggregated_data = {}
        missing_data_types = []

        for eval_type in self.evaluator_types:
            # Fetch global evaluators (no cryptocurrency, no symbol, no timeframe)
            evaluations = matrix.get_evaluations_by_evaluator(
                matrix_id, exchange_name, eval_type
            )

            valid_evaluations = [
                {
                    "eval_note": ev.node_value,
                    "eval_note_description": ev.node_description or "",
                }
                for ev in evaluations.values()
                if evaluators_util.check_valid_eval_note(ev.node_value)
            ]
            if valid_evaluations:
                aggregated_data[eval_type] = valid_evaluations
            else:
                missing_data_types.append(eval_type)

        if not aggregated_data:
            return

        ai_service = await self._get_ai_service()
        if not ai_service:
            self.eval_note = 0
            final_eval_note_description = "Error: LLMService not available"
            self._has_evaluated = True
            await self.evaluation_completed(
                cryptocurrency=None,
                symbol=None,
                time_frame=None,
                eval_note=self.eval_note,
                eval_note_description=final_eval_note_description,
                eval_time=0,
                notify=True,
                origin_consumer=self.consumer_instance,
            )
            return

        self.eval_note, final_eval_note_description = await self._run_agents_analysis(
            aggregated_data, missing_data_types, ai_service
        )

        # Publish evaluation at global level
        await self.evaluation_completed(
            cryptocurrency=None,
            symbol=None,
            time_frame=None,
            eval_note=self.eval_note,
            eval_note_description=final_eval_note_description,
            eval_time=0,
            notify=True,
            origin_consumer=self.consumer_instance,
        )
