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
import tulipy
import os

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.enums as enums
import octobot_commons.os_util as os_util
import octobot_commons.data_util as data_util
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.util as evaluators_util
import octobot_evaluators.errors as evaluators_errors
import octobot_trading.api as trading_api
import octobot_services.api as services_api
import octobot_services.errors as services_errors
import tentacles.Services.Services_bases


def _get_gpt_service():
    try:
        return tentacles.Services.Services_bases.GPTService
    except (AttributeError, ImportError):
        raise ImportError("the gpt_service tentacle is not installed")


class GPTEvaluator(evaluators.TAEvaluator):
    GLOBAL_VERSION = 1
    PREPROMPT = "Predict: {up or down} {confidence%} (no other information)"
    PASSED_DATA_LEN = 10
    MAX_CONFIDENCE_PERCENT = 100
    HIGH_CONFIDENCE_PERCENT = 80
    MEDIUM_CONFIDENCE_PERCENT = 50
    LOW_CONFIDENCE_PERCENT = 30
    INDICATORS = {
        "No indicator: raw candles price data": lambda data, period: data,
        "EMA: Exponential Moving Average": tulipy.ema,
        "SMA: Simple Moving Average": tulipy.sma,
        "Kaufman Adaptive Moving Average": tulipy.kama,
        "Hull Moving Average": tulipy.kama,
        "RSI: Relative Strength Index": tulipy.rsi,
        "Detrended Price Oscillator": tulipy.dpo,
    }
    SOURCES = ["Open", "High", "Low", "Close", "Volume", "Full candle (For no indicator only)"]
    ALLOW_GPT_REEVALUATION_ENV = "ALLOW_GPT_REEVALUATIONS"
    GPT_MODELS = []
    ALLOW_TOKEN_LIMIT_UPDATE = False

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.indicator = None
        self.source = None
        self.period = None
        self.min_confidence_threshold = 100
        self.gpt_model = _get_gpt_service().DEFAULT_MODEL
        self.is_backtesting = False
        self.min_allowed_timeframe = os.getenv("MIN_GPT_TIMEFRAME", None)
        self.enable_model_selector = os_util.parse_boolean_environment_var("ENABLE_GPT_MODELS_SELECTOR", "True")
        self._min_allowed_timeframe_minutes = 0
        try:
            if self.min_allowed_timeframe:
                self._min_allowed_timeframe_minutes = \
                    commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(self.min_allowed_timeframe)]
        except ValueError:
            self.logger.error(f"Invalid timeframe configuration: unknown timeframe: '{self.min_allowed_timeframe}'")
        self.allow_reevaluations = os_util.parse_boolean_environment_var(self.ALLOW_GPT_REEVALUATION_ENV, "True")
        self.gpt_tokens_limit = _get_gpt_service().NO_TOKEN_LIMIT_VALUE
        self.services_config = None

    def enable_reevaluation(self) -> bool:
        """
        Override when artificial re-evaluations from the evaluator channel can be disabled
        """
        return self.allow_reevaluations

    @classmethod
    def get_signals_history_type(cls):
        """
        Override when this evaluator uses a specific type of signal history
        """
        return commons_enums.SignalHistoryTypes.GPT

    async def load_and_save_user_inputs(self, bot_id: str) -> dict:
        """
        instance method API for user inputs
        Initialize and save the tentacle user inputs in run data
        :return: the filled user input configuration
        """
        self.is_backtesting = self._is_in_backtesting()
        if self.is_backtesting and not services_api.is_service_used_by_backtestable_feed(_get_gpt_service()):
            self.logger.error(f"{self.get_name()} is disabled in backtesting. It will only emit neutral evaluations")
        await self._init_GPT_models()
        return await super().load_and_save_user_inputs(bot_id)

    def init_user_inputs(self, inputs: dict) -> None:
        self.indicator = self.UI.user_input(
            "indicator", enums.UserInputTypes.OPTIONS, next(iter(self.INDICATORS)),
            inputs, options=list(self.INDICATORS),
            title="Indicator: the technical indicator to apply and give the result of to chat GPT."
        )
        self.source = self.UI.user_input(
            "source", enums.UserInputTypes.OPTIONS, self.SOURCES[3],
            inputs, options=self.SOURCES,
            title="Source: values of candles data to pass to the indicator."
        )
        self.period = self.UI.user_input(
            "period", enums.UserInputTypes.INT,
            self.period, inputs, min_val=1,
            title="Period: length of the indicator period or the number of candles to give to ChatGPT."
        )
        self.min_confidence_threshold = self.UI.user_input(
            "min_confidence_threshold", enums.UserInputTypes.INT,
            self.min_confidence_threshold, inputs, min_val=0, max_val=100,
            title="Minimum confidence threshold: % confidence value starting from which to return 1 or -1."
        )
        if self.enable_model_selector:
            current_value = self.specific_config.get("GPT_model")
            models = list(self.GPT_MODELS) or (
                [current_value] if current_value else [_get_gpt_service().DEFAULT_MODEL]
            )
            self.gpt_model = self.UI.user_input(
                "GPT model", enums.UserInputTypes.OPTIONS, _get_gpt_service().DEFAULT_MODEL,
                inputs, options=sorted(models),
                title="GPT Model: the GPT model to use. Enable the evaluator to load other models."
            )
        if os_util.parse_boolean_environment_var(self.ALLOW_GPT_REEVALUATION_ENV, "True"):
            self.allow_reevaluations = self.UI.user_input(
                "allow_reevaluation", enums.UserInputTypes.BOOLEAN, self.allow_reevaluations,
                inputs,
                title="Allow Reevaluation: send a ChatGPT request when realtime evaluators trigger a "
                      "global reevaluation Use latest available value otherwise. "
                      "Warning: enabling this can lead to a large amount of GPT requests and consumed tokens."
            )
        if self.ALLOW_TOKEN_LIMIT_UPDATE:
            self.gpt_tokens_limit = self.UI.user_input(
                "max_gpt_tokens", enums.UserInputTypes.INT,
                self.gpt_tokens_limit, inputs, min_val=_get_gpt_service().NO_TOKEN_LIMIT_VALUE,
                title=f"OpenAI token limit: maximum daily number of tokens to consume with a given OctoBot instance. "
                      f"Use {_get_gpt_service().NO_TOKEN_LIMIT_VALUE} to remove the limit."
            )

    async def _init_GPT_models(self):
        if not self.GPT_MODELS:
            self.GPT_MODELS = [_get_gpt_service().DEFAULT_MODEL]
            if self.enable_model_selector and not self.is_backtesting:
                try:
                    service = await services_api.get_service(
                        _get_gpt_service(), self.is_backtesting, self.services_config
                    )
                    self.GPT_MODELS = service.models
                    self.ALLOW_TOKEN_LIMIT_UPDATE = service.allow_token_limit_update()
                except Exception as err:
                    self.logger.exception(err, True, f"Impossible to fetch GPT models: {err}")

    async def _init_registered_topics(self, all_symbols_by_crypto_currencies, currencies, symbols, time_frames):
        await super()._init_registered_topics(all_symbols_by_crypto_currencies, currencies, symbols, time_frames)
        for time_frame in time_frames:
            if not self._check_timeframe(time_frame.value):
                self.logger.error(f"{time_frame.value} time frame will be ignored for {self.get_name()} "
                                  f"as {time_frame.value} is not allowed in this configuration. "
                                  f"The shortest allowed time frame is {self.min_allowed_timeframe}. {self.get_name()} "
                                  f"will emit neutral evaluations on this time frame.")

    async def ohlcv_callback(self, exchange: str, exchange_id: str,
                             cryptocurrency: str, symbol: str, time_frame, candle, inc_in_construction_data):
        candle_data = self.get_candles_data(exchange, exchange_id, symbol, time_frame, inc_in_construction_data)
        await self.evaluate(cryptocurrency, symbol, time_frame, candle_data, candle)

    async def evaluate(self, cryptocurrency, symbol, time_frame, candle_data, candle):
        async with self.async_evaluation():
            self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
            if self._check_timeframe(time_frame):
                try:
                    candle_time = candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]
                    computed_data = self.call_indicator(candle_data)
                    formatted_data = self.get_formatted_data(computed_data)
                    prediction = await self.ask_gpt(self.PREPROMPT, formatted_data, symbol, time_frame, candle_time) \
                        or ""
                    cleaned_prediction = prediction.strip().replace("\n", "").replace(".", "").lower()
                    prediction_side = self._parse_prediction_side(cleaned_prediction)
                    if prediction_side == 0 and not self.is_backtesting:
                        self.logger.warning(
                            f"Ignored ChatGPT answer for {symbol} {time_frame}, answer: '{cleaned_prediction}': "
                            f"missing prediction or % accuracy."
                        )
                        return
                    confidence = self._parse_confidence(cleaned_prediction) / 100
                    self.eval_note = prediction_side * confidence
                except services_errors.InvalidRequestError as e:
                    self.logger.error(f"Invalid GPT request: {e}")
                except services_errors.RateLimitError as e:
                    self.logger.error(f"Impossible to get ChatGPT evaluation for {symbol} on {time_frame}: "
                                      f"No remaining free tokens for today : {e}. To prevent this, you can reduce the "
                                      f"amount of traded pairs, use larger time frames or increase the maximum "
                                      f"allowed tokens.")
                except services_errors.UnavailableInBacktestingError:
                    # error already logged error for backtesting in use_backtesting_init_timeout
                    pass
                except evaluators_errors.UnavailableEvaluatorError as e:
                    self.logger.exception(e, True, f"Evaluation error: {e}")
                except tulipy.lib.InvalidOptionError as e:
                    self.logger.warning(
                        f"Error when computing {self.indicator} on {self.period} period with {len(candle_data)} "
                        f"candles: {e}"
                    )
                    self.logger.exception(e, False)
            else:
                self.logger.debug(f"Ignored {time_frame} time frame as the shorted allowed time frame is "
                                  f"{self.min_allowed_timeframe}")
            await self.evaluation_completed(cryptocurrency, symbol, time_frame,
                                            eval_time=evaluators_util.get_eval_time(full_candle=candle,
                                                                                    time_frame=time_frame))

    def get_formatted_data(self, computed_data) -> str:
        if self.source in self.get_unformated_sources():
            return str(computed_data)
        reduced_data = computed_data[-self.PASSED_DATA_LEN:]
        return ", ".join(str(datum).replace('[', '').replace(']', '') for datum in reduced_data)

    async def ask_gpt(self, preprompt, inputs, symbol, time_frame, candle_time) -> str:
        try:
            service = await services_api.get_service(
                _get_gpt_service(),
                self.is_backtesting,
                {} if self.is_backtesting else self.services_config
            )
            service.apply_daily_token_limit_if_possible(self.gpt_tokens_limit)
            model = self.gpt_model if self.enable_model_selector else None
            resp = await service.get_chat_completion(
                [
                    service.create_message("system", preprompt, model=model),
                    service.create_message("user", inputs, model=model),
                ],
                model=model,
                exchange=self.exchange_name,
                symbol=symbol,
                time_frame=time_frame,
                version=self.get_version(),
                candle_open_time=candle_time,
                use_stored_signals=self.is_backtesting
            )
            self.logger.info(
                f"GPT's answer is '{resp}' for {symbol} on {time_frame} with input: {inputs} "
                f"and candle_time: {candle_time}"
            )
            return resp
        except services_errors.CreationError as err:
            raise evaluators_errors.UnavailableEvaluatorError(f"Impossible to get ChatGPT prediction: {err}") from err

    def get_version(self):
        # later on, identify by its specs
        # return f"{self.gpt_model}-{self.source}-{self.indicator}-{self.period}-{self.GLOBAL_VERSION}"
        return "0.0.0"

    def call_indicator(self, candle_data):
        if self.source in self.get_unformated_sources():
            return candle_data
        return data_util.drop_nan(self.INDICATORS[self.indicator](candle_data, self.period))

    def get_candles_data(self, exchange, exchange_id, symbol, time_frame, inc_in_construction_data):
        if self.source in self.get_unformated_sources():
            limit = self.period if inc_in_construction_data else self.period + 1
            full_candles = trading_api.get_candles_as_list(
                trading_api.get_symbol_historical_candles(
                    self.get_exchange_symbol_data(exchange, exchange_id, symbol), time_frame, limit=limit
                )
            )
            # remove time value
            for candle in full_candles:
                candle.pop(commons_enums.PriceIndexes.IND_PRICE_TIME.value)
            if inc_in_construction_data:
                return full_candles
            return full_candles[:-1]
        return self.get_candles_data_api()(
            self.get_exchange_symbol_data(exchange, exchange_id, symbol), time_frame,
            include_in_construction=inc_in_construction_data
        )

    def get_unformated_sources(self):
        return (self.SOURCES[5], )

    def get_candles_data_api(self):
        return {
            self.SOURCES[0]: trading_api.get_symbol_open_candles,
            self.SOURCES[1]: trading_api.get_symbol_high_candles,
            self.SOURCES[2]: trading_api.get_symbol_low_candles,
            self.SOURCES[3]: trading_api.get_symbol_close_candles,
            self.SOURCES[4]: trading_api.get_symbol_volume_candles,
        }[self.source]

    def _check_timeframe(self, time_frame):
        return commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(time_frame)] >= \
            self._min_allowed_timeframe_minutes

    def _parse_prediction_side(self, cleaned_prediction):
        if "down " in cleaned_prediction:
            return 1
        elif "up " in cleaned_prediction:
            return -1
        return 0

    def _parse_confidence(self, cleaned_prediction):
        """
        possible formats:
        up 70%                   (most common case)
        up with 70% confidence
        up with high confidence
        """
        value = self.LOW_CONFIDENCE_PERCENT
        if "%" in cleaned_prediction:
            percent_index = cleaned_prediction.index("%")
            bracket_index = (cleaned_prediction[:percent_index].rindex("{") + 1) \
                if "{" in cleaned_prediction[:percent_index] else 0
            value = float(cleaned_prediction[bracket_index:percent_index].split(" ")[-1])
        elif "high" in cleaned_prediction:
            value = self.HIGH_CONFIDENCE_PERCENT
        elif "medium" in cleaned_prediction or "intermediate" in cleaned_prediction:
            value = self.MEDIUM_CONFIDENCE_PERCENT
        elif "low" in cleaned_prediction:
            value = self.LOW_CONFIDENCE_PERCENT
        elif not cleaned_prediction:
            value = 0
        else:
            self.logger.warning(f"Impossible to parse confidence in {cleaned_prediction}. Using low confidence")
        if value >= self.min_confidence_threshold:
            return self.MAX_CONFIDENCE_PERCENT
        return value
