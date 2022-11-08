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
import decimal

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot.strategy_optimizer.fitness_parameter as fitness_parameter
import octobot.strategy_optimizer.optimizer_filter as optimizer_filter


class OptimizerSettings:
    def __init__(self, settings_dict=None):
        if settings_dict is None:
            settings_dict = {}
        # generic
        self.optimizer_config = settings_dict.get(commons_enums.OptimizerConfig.OPTIMIZER_CONFIG.value, None)
        self.randomly_chose_runs = settings_dict.get(commons_enums.OptimizerConfig.RANDOMLY_CHOSE_RUNS.value,
                                                     commons_constants.OPTIMIZER_DEFAULT_RANDOMLY_CHOSE_RUNS)
        self.data_files = settings_dict.get(commons_enums.OptimizerConfig.DATA_FILES.value)
        self.start_timestamp = settings_dict.get(commons_enums.OptimizerConfig.START_TIMESTAMP.value, None)
        self.end_timestamp = settings_dict.get(commons_enums.OptimizerConfig.END_TIMESTAMP.value, None)
        self.required_idle_cores = int(settings_dict.get(commons_enums.OptimizerConfig.IDLE_CORES.value,
                                                         commons_constants.OPTIMIZER_DEFAULT_REQUIRED_IDLE_CORES))
        self.notify_when_complete = settings_dict.get(commons_enums.OptimizerConfig.NOTIFY_WHEN_COMPLETE.value,
                                                      commons_constants.OPTIMIZER_DEFAULT_NOTIFY_WHEN_COMPLETE)
        self.optimizer_mode = settings_dict.get(commons_enums.OptimizerConfig.MODE.value,
                                                commons_enums.OptimizerModes.NORMAL.value)
        optimizer_id = settings_dict.get(commons_enums.OptimizerConfig.OPTIMIZER_ID.value, 1)
        self.optimizer_id = optimizer_id if optimizer_id is None else int(optimizer_id)
        self.optimizer_ids = settings_dict.get(commons_enums.OptimizerConfig.OPTIMIZER_IDS.value)
        self.optimizer_mode = settings_dict.get(commons_enums.OptimizerConfig.MODE.value,
                                                commons_enums.OptimizerModes.NORMAL.value)
        self.queue_size = int(settings_dict.get(commons_enums.OptimizerConfig.QUEUE_SIZE.value,
                                                commons_constants.OPTIMIZER_DEFAULT_QUEUE_SIZE))
        self.empty_the_queue = settings_dict.get(commons_enums.OptimizerConfig.EMPTY_THE_QUEUE.value, False)
        # update run database at the end of each period
        self.db_update_period = int(settings_dict.get(commons_enums.OptimizerConfig.DB_UPDATE_PERIOD.value,
                                                      commons_constants.OPTIMIZER_DEFAULT_DB_UPDATE_PERIOD))
        # AI / genetic
        self.max_optimizer_runs = settings_dict.get(commons_enums.OptimizerConfig.MAX_OPTIMIZER_RUNS.value,
                                                    commons_constants.OPTIMIZER_DEFAULT_MAX_OPTIMIZER_RUNS)
        self.generations_count = settings_dict.get(commons_enums.OptimizerConfig.DEFAULT_GENERATIONS_COUNT.value,
                                                   commons_constants.OPTIMIZER_DEFAULT_GENERATIONS_COUNT)
        self.initial_generation_count = settings_dict.get(commons_enums.OptimizerConfig.INITIAL_GENERATION_COUNT.value,
                                                          commons_constants.OPTIMIZER_DEFAULT_INITIAL_GENERATION_COUNT)
        self.run_per_generation = settings_dict.get(commons_enums.OptimizerConfig.DEFAULT_RUN_PER_GENERATION.value,
                                                    commons_constants.OPTIMIZER_DEFAULT_RUN_PER_GENERATION)
        self.fitness_parameters = self.parse_fitness_parameters(
            settings_dict.get(commons_enums.OptimizerConfig.DEFAULT_SCORING_PARAMETERS.value,
                              self.get_default_fitness_parameters())
        )
        self.exclude_filters = self.parse_optimizer_filter(
            settings_dict.get(commons_enums.OptimizerConfig.DEFAULT_OPTIMIZER_FILTERS.value,
                              self.get_default_optimizer_filters())
        )
        self.mutation_percent = float(settings_dict.get(
            commons_enums.OptimizerConfig.DEFAULT_MUTATION_PERCENT.value,
            commons_constants.OPTIMIZER_DEFAULT_MUTATION_PERCENT))
        self.max_mutation_probability_percent = decimal.Decimal(settings_dict.get(
            commons_enums.OptimizerConfig.MAX_MUTATION_PROBABILITY_PERCENT.value,
            commons_constants.OPTIMIZER_DEFAULT_MAX_MUTATION_PROBABILITY_PERCENT))
        self.min_mutation_probability_percent = decimal.Decimal(settings_dict.get(
            commons_enums.OptimizerConfig.MIN_MUTATION_PROBABILITY_PERCENT.value,
            commons_constants.OPTIMIZER_DEFAULT_MIN_MUTATION_PROBABILITY_PERCENT))
        self.max_mutation_number_multiplier = decimal.Decimal(settings_dict.get(
            commons_enums.OptimizerConfig.DEFAULT_MAX_MUTATION_NUMBER_MULTIPLIER.value,
            commons_constants.OPTIMIZER_DEFAULT_MAX_MUTATION_NUMBER_MULTIPLIER))
        self.crossover_percent = float(settings_dict.get(
            commons_enums.OptimizerConfig.DEFAULT_CROSSOVER_PERCENT.value,
            commons_constants.OPTIMIZER_DEFAULT_CROSSOVER_PERCENT))
        self.target_fitness_score = settings_dict.get(commons_enums.OptimizerConfig.TARGET_FITNESS_SCORE.value)
        self.stay_within_boundaries = settings_dict.get(commons_enums.OptimizerConfig.STAY_WITHIN_BOUNDARIES.value,
                                                        False)

    def parse_fitness_parameters(self, parameters):
        return [
            fitness_parameter.FitnessParameter.from_dict(param)
            for param in parameters
        ]

    def get_default_fitness_parameters(self):
        return [
            {
                fitness_parameter.FitnessParameter.NAME_KEY: commons_enums.BacktestingMetadata.PERCENT_GAINS.value,
                fitness_parameter.FitnessParameter.WEIGHT_KEY: 1,
                fitness_parameter.FitnessParameter.IS_RATIO_FROM_MAX_KEY: True,
            },
            {
                fitness_parameter.FitnessParameter.NAME_KEY:
                    commons_enums.BacktestingMetadata.COEFFICIENT_OF_DETERMINATION_MAX_BALANCE.value,
                fitness_parameter.FitnessParameter.WEIGHT_KEY: 1,
                fitness_parameter.FitnessParameter.IS_RATIO_FROM_MAX_KEY: False,
            },
        ]

    def parse_optimizer_filter(self, filters):
        return [
            optimizer_filter.OptimizerFilter.from_dict(element)
            for element in filters
        ]

    def get_default_optimizer_filters(self):
        return [
            {
                optimizer_filter.OptimizerFilter.LEFT_OPERAND_KEY_KEY: commons_enums.BacktestingMetadata.TRADES.value,
                optimizer_filter.OptimizerFilter.RIGHT_OPERAND_KEY_KEY: None,
                optimizer_filter.OptimizerFilter.LEFT_OPERAND_VALUE_KEY: None,
                optimizer_filter.OptimizerFilter.RIGHT_OPERAND_VALUE_KEY: 1,
                optimizer_filter.OptimizerFilter.OPERATOR_KEY: commons_enums.LogicalOperators.LOWER_THAN.value,
            },
            {
                optimizer_filter.OptimizerFilter.LEFT_OPERAND_KEY_KEY:
                    commons_enums.BacktestingMetadata.COEFFICIENT_OF_DETERMINATION_MAX_BALANCE.value,
                optimizer_filter.OptimizerFilter.RIGHT_OPERAND_KEY_KEY: None,
                optimizer_filter.OptimizerFilter.LEFT_OPERAND_VALUE_KEY: None,
                optimizer_filter.OptimizerFilter.RIGHT_OPERAND_VALUE_KEY: 0,
                optimizer_filter.OptimizerFilter.OPERATOR_KEY: commons_enums.LogicalOperators.LOWER_THAN.value,
            },
            {
                optimizer_filter.OptimizerFilter.LEFT_OPERAND_KEY_KEY:
                    commons_enums.BacktestingMetadata.PERCENT_GAINS.value,
                optimizer_filter.OptimizerFilter.RIGHT_OPERAND_KEY_KEY: None,
                optimizer_filter.OptimizerFilter.LEFT_OPERAND_VALUE_KEY: None,
                optimizer_filter.OptimizerFilter.RIGHT_OPERAND_VALUE_KEY: 0,
                optimizer_filter.OptimizerFilter.OPERATOR_KEY: commons_enums.LogicalOperators.LOWER_THAN.value,
            },
        ]
