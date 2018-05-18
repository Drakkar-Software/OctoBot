from config.cst import *
from evaluator.RealTime.realtime_evaluator import RealTimeTAEvaluator
from tools.time_frame_manager import TimeFrameManager


class InstantFluctuationsEvaluator(RealTimeTAEvaluator):
    def __init__(self, exchange, symbol):
        super().__init__(exchange, symbol)
        self.something_is_happening = False

        self.average_price = 0
        self.last_price = 0

        # Volume
        self.volume_updated = 0
        self.average_volume = 0
        self.last_volume = 0

        # Constants
        self.MIN_EVAL_NOTE = 0.5
        self.VOLUME_HAPPENING_THRESHOLD = 5
        self.PRICE_HAPPENING_THRESHOLD = 1.01

    def _refresh_data(self):
        self.update()

    def eval_impl(self):
        self.evaluate_volume_fluctuations()
        if self.something_is_happening:
            self.notify_evaluator_thread_managers(self.__class__.__name__)
            self.something_is_happening = False
        else:
            self.eval_note = START_PENDING_EVAL_NOTE

    def evaluate_volume_fluctuations(self):
        # check volume fluctuation
        if self.last_volume > self.VOLUME_HAPPENING_THRESHOLD * self.average_volume:
            # TEMP
            self.eval_note = self.MIN_EVAL_NOTE if self.last_price > self.average_price else -self.MIN_EVAL_NOTE
            self.something_is_happening = True

        # check price fluctuation
        if self.last_price > self.PRICE_HAPPENING_THRESHOLD * self.average_price:
            self.eval_note = self.MIN_EVAL_NOTE
            self.something_is_happening = True

        elif self.last_price < (1 - self.PRICE_HAPPENING_THRESHOLD) * self.average_price:
            self.eval_note = -self.MIN_EVAL_NOTE
            self.something_is_happening = True

    def update(self):
        self.volume_updated += 1

        if (self.refresh_time * self.volume_updated) > TimeFramesMinutes[self.specific_config[CONFIG_TIME_FRAME]]:
            volume_data = self.exchange.get_symbol_prices(self.symbol, self.specific_config[CONFIG_TIME_FRAME], 10)
            self.average_volume = volume_data[PriceStrings.STR_PRICE_VOL.value].mean()
            self.average_price = volume_data[PriceStrings.STR_PRICE_CLOSE.value].mean()
            self.volume_updated = 0

        else:
            volume_data = self.exchange.get_symbol_prices(self.symbol, self.specific_config[CONFIG_TIME_FRAME], 1)

        self.last_volume = volume_data[PriceStrings.STR_PRICE_VOL.value].tail(1).values[0]
        self.last_price = volume_data[PriceStrings.STR_PRICE_CLOSE.value].tail(1).values[0]

    def set_default_config(self):
        time_frames = self.exchange.get_exchange_manager().get_config_time_frame()
        min_time_frame = TimeFrameManager.find_config_min_time_frame(time_frames)

        self.specific_config = {
            CONFIG_TIME_FRAME: min_time_frame,
            CONFIG_REFRESH_RATE: TimeFramesMinutes[min_time_frame] / 6 * MINUTE_TO_SECONDS,
        }
