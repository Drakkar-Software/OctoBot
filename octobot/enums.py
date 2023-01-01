#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import enum


class CommunityFeedType(enum.Enum):
    WebsocketFeed = "WebsocketFeed"
    MQTTFeed = "MQTTFeed"


class CommunityEnvironments(enum.Enum):
    Staging = "Staging"
    Production = "Production"


class OptimizerModes(enum.Enum):
    NORMAL = "normal"
    GENETIC = "genetic"


class OptimizerConfig(enum.Enum):
    OPTIMIZER_ID = "optimizer_id"
    OPTIMIZER_IDS = "optimizer_ids"
    RANDOMLY_CHOSE_RUNS = "randomly_chose_runs"
    DATA_FILES = "data_files"
    OPTIMIZER_CONFIG = "optimizer_config"
    EXCHANGE_TYPE = "exchange_type"
    QUEUE_SIZE = "queue_size"
    EMPTY_THE_QUEUE = "empty_the_queue"
    START_TIMESTAMP = "start_timestamp"
    END_TIMESTAMP = "end_timestamp"
    IDLE_CORES = "idle_cores"
    NOTIFY_WHEN_COMPLETE = "notify_when_complete"
    DB_UPDATE_PERIOD = "db_update_period"
    MODE = "mode"
    MAX_OPTIMIZER_RUNS = "max_optimizer_runs"
    INITIAL_GENERATION_COUNT = "initial_generation_count"
    DEFAULT_GENERATIONS_COUNT = "default_generations_count"
    DEFAULT_RUN_PER_GENERATION = "default_run_per_generation"
    DEFAULT_SCORING_PARAMETERS = "default_scoring_parameters"
    DEFAULT_OPTIMIZER_FILTERS = "default_optimizer_filters"
    DEFAULT_OPTIMIZER_CONSTRAINTS = "default_optimizer_constraints"
    DEFAULT_MUTATION_PERCENT = "default_mutation_percent"
    MAX_MUTATION_PROBABILITY_PERCENT = "max_mutation_probability_percent"
    MIN_MUTATION_PROBABILITY_PERCENT = "min_mutation_probability_percent"
    DEFAULT_MAX_MUTATION_NUMBER_MULTIPLIER = "default_max_mutation_number_multiplier"
    DEFAULT_CROSSOVER_PERCENT = "default_crossover_percent"
    STAY_WITHIN_BOUNDARIES = "stay_within_boundaries"
    TARGET_FITNESS_SCORE = "target_fitness_score"
