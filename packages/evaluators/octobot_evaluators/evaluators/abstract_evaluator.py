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
import time
import asyncio
import contextlib
import typing

import octobot_tentacles_manager.api as api
import octobot_tentacles_manager.configuration as tm_configuration

import async_channel.constants as channel_constants
import async_channel.enums as channel_enums
import async_channel.channels as channels

import octobot_commons.constants as common_constants
import octobot_commons.errors as commons_errors
import octobot_commons.enums as commons_enums
import octobot_commons.logging as commons_logging
import octobot_commons.tentacles_management as tentacles_management

import octobot_evaluators.evaluators.channel as evaluator_channels
import octobot_evaluators.constants as constants
import octobot_evaluators.matrix as matrix
import octobot_evaluators.evaluators.evaluator_factory as evaluator_factory

import octobot_evaluators.util as util


class AbstractEvaluator(tentacles_management.AbstractTentacle):
    __metaclass__ = tentacles_management.AbstractTentacle
    HISTORIZE_USER_INPUT_CONFIG = True
    USER_INPUT_TENTACLE_TYPE = commons_enums.UserInputTentacleTypes.EVALUATOR

    def __init__(self, tentacles_setup_config: tm_configuration.TentaclesSetupConfiguration):
        super().__init__()
        self.logger = commons_logging.get_logger(self.get_name())

        # Evaluator matrix id
        self.matrix_id: typing.Optional[str] = None

        # OctoBot id this evaluator has been started with
        self.bot_id: typing.Optional[str] = None

        # Tentacle global setup configuration
        self.tentacles_setup_config: tm_configuration.TentaclesSetupConfiguration = tentacles_setup_config

        # Evaluator specific config (Is loaded from tentacle specific file)
        self.specific_config: dict = {}

        # Evaluator specific config snapshot before a config update
        self.previous_specific_config: dict = None

        # If this indicator is enabled
        self.enabled: bool = self.is_enabled(self.tentacles_setup_config, False)

        # Specified Cryptocurrency for this instance (Should be None if wildcard)
        self.cryptocurrency: typing.Optional[str] = None

        # Specified Cryptocurrency name for this instance (Should be None if wildcard)
        self.cryptocurrency_name: typing.Optional[str] = None

        # Symbol is the cryptocurrency pair (Should be None if wildcard)
        self.symbol: typing.Optional[str] = None

        # Evaluation related exchange name
        self.exchange_name: typing.Optional[str] = None

        # Time_frame is the chart time frame (Should be None if wildcard)
        self.time_frame = None

        # history time represents the period of time of the indicator
        self.history_time = None

        # Evaluator category
        self.evaluator_type = None

        # Eval note will be set by the eval_impl at each call
        self.eval_note = common_constants.START_PENDING_EVAL_NOTE

        # Pertinence of indicator will be used with the eval_note to provide a relevancy
        self.pertinence = constants.START_EVAL_PERTINENCE

        # Active tells if this evaluator is currently activated (an evaluator can be paused)
        self.is_active: bool = True

        self.eval_note_time_to_live = None
        self.eval_note_changed_time = None

        # Define evaluators default consumer priority level
        self.priority_level: int = channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value

        self.consumers: list = []

        # True when this evaluator is only triggered on closed candles
        self.is_triggered_after_candle_close: bool = False

        # Cleared when starting an async evaluation (using self.async_evaluation()) and set afterwards
        self._is_evaluation_completed: typing.Optional[asyncio.Event] = None

    def post_init(self, tentacles_setup_config):
        """
        Automatically called after __init__ when post_init is True (default) in evaluator_factory
        Override when necessary
        :param tentacles_setup_config: the tentacles_setup_config __init__ argument
        :return: None
        """
        pass

    @classmethod
    async def single_evaluation(
            cls,
            tentacles_setup_config: tm_configuration.TentaclesSetupConfiguration,
            specific_config: dict,
            ignore_cache=False,
            should_trigger_post_init=False,
            **kwargs):
        evaluator_instance = evaluator_factory.create_temporary_evaluator_with_local_config(
            cls, tentacles_setup_config, specific_config, should_trigger_post_init)
        evaluation, error = await evaluator_instance.evaluator_manual_callback(ignore_cache=ignore_cache, **kwargs)
        return evaluation, error, evaluator_instance

    async def evaluator_manual_callback(self, **kwargs):
        """
        Override this method to define the appropriate behavior when this evaluator is being
        called manually
        :param kwargs: keyword arguments to be used for evaluation
        :return: the evaluation value
        """
        raise NotImplementedError("evaluator_manual_callback is not implemented")

    @staticmethod
    def get_eval_type():
        """
        Override this method when self.eval_note is other than : START_PENDING_EVAL_NOTE or float[-1:1]
        :return: type
        """
        return constants.EVALUATOR_EVAL_DEFAULT_TYPE

    @classmethod
    def get_is_cryptocurrencies_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency dependant else False
        """
        return True

    @classmethod
    def get_is_cryptocurrency_name_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency name dependant else False
        """
        return True

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not symbol dependant else False
        """
        return True

    @classmethod
    def get_is_time_frame_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not time_frame dependant else False
        """
        return True

    def get_trigger_time_frames(self):
        return self.specific_config.get(common_constants.CONFIG_TRIGGER_TIMEFRAMES, common_constants.CONFIG_WILDCARD)

    @staticmethod
    def invalidate_cache_on_code_change():
        # False is not yet supported
        return True

    @staticmethod
    def invalidate_cache_on_config_change():
        # False is not yet supported
        return True

    @classmethod
    def use_cache(cls):
        return False

    @classmethod
    def get_signals_history_type(cls):
        """
        Override when this evaluator uses a specific type of signal history
        """
        return None

    def enable_reevaluation(self) -> bool:
        """
        Override when artificial re-evaluations from the evaluator channel can be disabled
        """
        return True

    def get_local_config(self):
        return self.specific_config

    def _get_tentacle_registration_topic(self, all_symbols_by_crypto_currencies, time_frames, real_time_time_frames):
        currencies = [self.cryptocurrency]
        symbols = [self.symbol]
        available_time_frames = [self.time_frame]
        if self.get_is_cryptocurrencies_wildcard():
            currencies = all_symbols_by_crypto_currencies.keys()
        if self.get_is_symbol_wildcard():
            symbols = [currency_symbol
                       for currency_symbols in all_symbols_by_crypto_currencies.values()
                       for currency_symbol in currency_symbols]
        if self.get_is_time_frame_wildcard():
            available_time_frames = time_frames
        trigger_timeframes = self.get_trigger_time_frames()
        if trigger_timeframes != common_constants.CONFIG_WILDCARD:
            available_time_frames = [tf
                                     for tf in available_time_frames
                                     if tf in trigger_timeframes]
        return currencies, symbols, available_time_frames

    def _is_in_backtesting(self):
        try:
            import octobot_trading.api as exchange_api
            return exchange_api.get_is_backtesting(
                exchange_api.get_exchange_manager_from_exchange_name_and_id(
                    self.exchange_name,
                    exchange_api.get_exchange_id_from_matrix_id(self.exchange_name, self.matrix_id)
                )
            )
        except ImportError as e:
            self.logger.error(f"Can't connect check if backtesting is enabled {e}")
        return False

    async def initialize(
        self, all_symbols_by_crypto_currencies, time_frames, real_time_time_frames, bot_id, specific_config=None
    ):
        await self.reload_config(bot_id, specific_config=specific_config)
        currencies, symbols, time_frames = self._get_tentacle_registration_topic(
            all_symbols_by_crypto_currencies, time_frames, real_time_time_frames
        )
        await self._init_registered_topics(all_symbols_by_crypto_currencies, currencies, symbols, time_frames)

    async def _init_registered_topics(self, all_symbols_by_crypto_currencies, currencies, symbols, time_frames):
        for currency in currencies:
            for symbol in symbols:
                if symbol is None or symbol in all_symbols_by_crypto_currencies[currency]:
                    for time_frame in time_frames:
                        matrix.set_tentacle_value(
                            matrix_id=self.matrix_id,
                            tentacle_type=self.get_eval_type(),
                            tentacle_value=None,
                            tentacle_path=matrix.get_matrix_default_value_path(
                                exchange_name=self.exchange_name,
                                tentacle_type=self.evaluator_type.value,
                                tentacle_name=self.get_name(),
                                cryptocurrency=currency,
                                symbol=symbol,
                                time_frame=time_frame.value if time_frame else None
                            )
                        )

    async def evaluation_completed(self,
                                   cryptocurrency: typing.Optional[str] = None,
                                   symbol: typing.Optional[str] = None,
                                   time_frame=None,
                                   eval_note=None,
                                   eval_time=0,
                                   eval_note_description=None,
                                   eval_note_metadata=None,
                                   notify=True,
                                   origin_consumer=None,
                                   cache_client=None,
                                   cache_if_available=True) -> None:
        """
        Main async method to notify matrix to update
        :param cryptocurrency: evaluated cryptocurrency
        :param symbol: evaluated symbol
        :param time_frame: evaluated time frame
        :param eval_note: if None = self.eval_note
        :param eval_time: the time of the evaluation if relevant, default is 0
        :param eval_note_description: the description of the evaluation if relevant
        :param eval_note_metadata: the metadata of the evaluation if relevant
        :param notify: if true, will trigger matrix consumers
        :param origin_consumer: the sender consumer if it doesn't want to be notified
        :param cache_client: an existing cache client to avoid creating a local one
        :param cache_if_available: when True, if the evaluator is using cache, its value will be cached
        :return: None
        """
        try:
            if eval_note is None:
                eval_note = self.eval_note if self.eval_note is not None else common_constants.START_PENDING_EVAL_NOTE

            if self.use_cache():
                cache_client = cache_client or util.local_cache_client(self, symbol, time_frame)
                if self.eval_note == common_constants.DO_NOT_OVERRIDE_CACHE:
                    self.eval_note, missing = await cache_client.get_cached_value(cache_key=eval_time)
                    cache_client.ensure_no_missing_cached_value(missing)
                    eval_note = self.eval_note
                elif cache_if_available and eval_note != common_constants.DO_NOT_CACHE:
                    await cache_client.set_cached_value(eval_note, cache_key=eval_time, flush_if_necessary=True)
            self.ensure_eval_note_is_not_expired()
            if notify:
                # skip warning when evaluation is not to be broadcasted (might be a simple reset)
                self._log_on_invalid_eval_not_time(self.exchange_name, self.matrix_id, symbol, eval_time, time_frame)
            await evaluator_channels.get_chan(constants.MATRIX_CHANNEL,
                                              self.matrix_id).get_internal_producer().send_eval_note(
                matrix_id=self.matrix_id,
                evaluator_name=self.get_name(),
                evaluator_type=self.evaluator_type.value,
                eval_note=eval_note,
                eval_note_type=self.get_eval_type(),
                eval_time=eval_time,
                eval_note_description=eval_note_description,
                eval_note_metadata=eval_note_metadata,
                exchange_name=self.exchange_name,
                cryptocurrency=cryptocurrency,
                symbol=symbol,
                time_frame=time_frame,
                notify=notify,
                origin_consumer=origin_consumer)
        except commons_errors.NoCacheValue:
            self.logger.warning(f"Evaluation as \"{common_constants.DO_NOT_OVERRIDE_CACHE}\" "
                                f"but the is no cache to publish an evaluation from")
        except Exception as e:
            # if ConfigManager.is_in_dev_mode(self.config): # TODO
            #     raise e
            # else:
            self.logger.exception(e, True, f"Exception in evaluation_completed(): {e}")
        finally:
            if self.eval_note == "nan":
                self.eval_note = common_constants.START_PENDING_EVAL_NOTE
                self.logger.warning(str(self.symbol) + " evaluator returned 'nan' as eval_note, ignoring this value.")

    async def start(self, bot_id: str) -> bool:
        """
        :return: success of the evaluator's start
        """
        self.bot_id = bot_id
        self.consumers.append(
            await evaluator_channels.get_chan(constants.EVALUATORS_CHANNEL, self.matrix_id).new_consumer(
                self.evaluators_callback,
                cryptocurrency=self.cryptocurrency if self.cryptocurrency else channel_constants.CHANNEL_WILDCARD,
                symbol=self.symbol if self.symbol else channel_constants.CHANNEL_WILDCARD,
                time_frame=self.time_frame if self.time_frame else channel_constants.CHANNEL_WILDCARD,
                priority_level=self.priority_level,
            )
        )

        try:
            import octobot_services.channel as services_channels
            self.consumers.append(
                await channels.get_chan(services_channels.UserCommandsChannel.get_name()).new_consumer(
                    self.user_commands_callback,
                    {"bot_id": bot_id, "subject": self.get_name()}
                )
            )
        except KeyError:
            # UserCommandsChannel might not be available
            pass
        except ImportError:
            self.logger.warning("Can't connect to services channels")

    async def user_commands_callback(self, bot_id, subject, action, data) -> None:
        self.logger.debug(f"Received {action} command")
        if action == commons_enums.UserCommands.RELOAD_CONFIG.value:
            await self.reload_config(bot_id)
            self.logger.debug("Reloaded configuration")

    async def stop(self) -> None:
        """
        implement if necessary
        :return: None
        """
        for consumer in self.consumers:
            await consumer.stop()

    async def prepare(self) -> None:
        """
        Called just before start(), implement if necessary
        :return: None
        """
        pass

    async def start_evaluator(self, bot_id: str) -> None:
        """
        Start a task as matrix producer
        :return: None
        """
        if await self.start(bot_id):
            self.logger.debug("Evaluator started")
        else:
            self.logger.debug("Evaluator not started")

    async def reload_config(self, bot_id: str, specific_config=None) -> None:
        self.set_default_config()
        specific_config = specific_config or api.get_tentacle_config(
            self.tentacles_setup_config, self.__class__
        )

        if not specific_config and self.ALLOW_SUPER_CLASS_CONFIG:
            # if nothing in config, try with any super-class' config file
            for super_class in self.get_parent_evaluator_classes(AbstractEvaluator):
                try:
                    if specific_config := api.get_tentacle_config(self.tentacles_setup_config, super_class):
                        break
                except KeyError:
                    pass  # super_class tentacle config not found
        self.specific_config.update(specific_config)
        await self.load_and_save_user_inputs(bot_id)
        self.logger.debug(f"Using config: {self.specific_config}")

    @classmethod
    def create_local_instance(cls, _, tentacles_setup_config, tentacle_config):
        return evaluator_factory.create_temporary_evaluator_with_local_config(
            cls, tentacles_setup_config, tentacle_config, False
        )

    def set_default_config(self):
        """
        To implement in subclasses if config necessary
        :return:
        """
        self.specific_config = {}

    @classmethod
    def get_evaluator_priority(cls, tentacles_setup_config) -> float:
        """
        Returns the priority of the evaluator (will later be compared to other evaluators).
        A higher priority evaluator will be called first when multiple evaluators are to
        be called at the same time.
        Default priority is DEFAULT_PRIORITY defined in OctoBot-Commons.
        Order is undefined between evaluators of the same priority.
        :return: the priority level
        """
        return api.get_tentacle_config(tentacles_setup_config, cls).get(common_constants.EVALUATOR_PRIORITY,
                                                                        common_constants.DEFAULT_EVALUATOR_PRIORITY)

    def reset(self) -> None:
        """
        Reset temporary parameters to enable fresh start
        :return: None
        """
        self.eval_note = common_constants.START_PENDING_EVAL_NOTE

    @classmethod
    def has_class_in_parents(cls, klass) -> bool:
        """
        Explore up to the 2nd degree parent
        :param klass: python Class to explore
        :return: Boolean
        """
        if klass in cls.__bases__:
            return True
        elif any(klass in base.__bases__ for base in cls.__bases__):
            return True
        else:
            for base in cls.__bases__:
                if any(klass in super_base.__bases__ for super_base in base.__bases__):
                    return True
        return False

    @classmethod
    def get_parent_evaluator_classes(cls, higher_parent_class_limit=None) -> list:
        """
        Return the evaluator parent classe(s)
        :param higher_parent_class_limit:
        :return: list of classes
        """
        return [
            class_type
            for class_type in cls.mro()
            if (higher_parent_class_limit if higher_parent_class_limit else AbstractEvaluator) in class_type.mro()
        ]

    def set_eval_note(self, new_eval_note) -> None:
        """
        Performs additionnal check to eval_note before changing it
        :param new_eval_note:
        :return: None
        """
        self.eval_note_changed()

        if self.eval_note == common_constants.START_PENDING_EVAL_NOTE:
            self.eval_note = common_constants.INIT_EVAL_NOTE

        if self.eval_note + new_eval_note > 1:
            self.eval_note = 1
        elif self.eval_note + new_eval_note < -1:
            self.eval_note = -1
        else:
            self.eval_note += new_eval_note

    @classmethod
    def is_enabled(cls, tentacles_setup_config, default) -> bool:
        """
        Check if the evaluator is enabled by configuration
        :param tentacles_setup_config: tentacles setup config
        :param default: default value if evaluator config is not found
        :return: evaluator config
        """
        try:
            return api.is_tentacle_activated_in_tentacles_setup_config(tentacles_setup_config,
                                                                       cls.get_name(),
                                                                       raise_errors=True)
        except KeyError:
            for parent in cls.mro():
                try:
                    return api.is_tentacle_activated_in_tentacles_setup_config(tentacles_setup_config,
                                                                               parent.__name__,
                                                                               raise_errors=True)
                except KeyError:
                    pass
        return default

    def save_evaluation_expiration_time(self, eval_note_time_to_live, eval_note_changed_time=None) -> None:
        """
        Use only if the current evaluation is to stay for a pre-defined amount of seconds
        :param eval_note_time_to_live:
        :param eval_note_changed_time:
        :return: None
        """
        self.eval_note_time_to_live = eval_note_time_to_live
        self.eval_note_changed_time = eval_note_changed_time if eval_note_changed_time else time.time()

    def eval_note_changed(self) -> None:
        """
        Eval note changed callback
        :return: None
        """
        if self.eval_note_time_to_live is not None and self.eval_note_changed_time is None:
            self.eval_note_changed_time = time.time()

    def ensure_eval_note_is_not_expired(self) -> None:
        """
        Eval note expiration check
        :return: None
        """
        if self.eval_note_time_to_live is not None:
            if self.eval_note_changed_time is None:
                self.eval_note_changed_time = time.time()

            if time.time() - self.eval_note_changed_time > self.eval_note_time_to_live:
                self.eval_note = common_constants.START_PENDING_EVAL_NOTE
                self.eval_note_time_to_live = None
                self.eval_note_changed_time = None

    def _log_on_invalid_eval_not_time(self, exchange_name, matrix_id, symbol, eval_time, time_frame) -> None:
        if not time_frame:
            return
        current_time = self._get_exchange_current_time(exchange_name, matrix_id)
        if not matrix.is_evaluation_valid_in_time(current_time, eval_time, commons_enums.TimeFrames(time_frame)):
            self.logger.warning(
                f"Performed {symbol} {time_frame} evaluation on outdated data: {eval_time=}, {current_time=}. "
                f"Up-to-date {symbol} price data on {time_frame} might not yet be available on {exchange_name}."
            )

    def _get_exchange_current_time(self, exchange_name, matrix_id):
        try:
            import octobot_trading.api as exchange_api
            exchange_manager = exchange_api.get_exchange_manager_from_exchange_name_and_id(
                exchange_name,
                exchange_api.get_exchange_id_from_matrix_id(exchange_name, matrix_id)
            )
            return exchange_api.get_exchange_current_time(exchange_manager)
        except ImportError:
            self.logger.error("Strategy requires OctoBot-Trading package installed")

    def get_exchange_symbol_data(self, exchange_name: str, exchange_id: str, symbol: str):
        try:
            import octobot_trading.api as exchange_api
            exchange_manager = exchange_api.get_exchange_manager_from_exchange_name_and_id(exchange_name, exchange_id)
            return exchange_api.get_symbol_data(exchange_manager, symbol)
        except (ImportError, KeyError):
            self.logger.error(f"Can't get {exchange_name} from exchanges instances")
        return

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
        pass

    @contextlib.asynccontextmanager
    async def async_evaluation(self):
        if self._is_evaluation_completed is None:
            self._is_evaluation_completed = asyncio.Event()
        try:
            self._is_evaluation_completed.clear()
            yield
        finally:
            self._is_evaluation_completed.set()

    async def wait_for_async_evaluation_completion(self, timeout):
        if self._is_evaluation_completed is None or self._is_evaluation_completed.is_set():
            return
        await asyncio.wait_for(self._is_evaluation_completed.wait(), timeout=timeout)

    def is_in_async_evaluation(self):
        if self._is_evaluation_completed is None:
            return False
        return not self._is_evaluation_completed.is_set()
