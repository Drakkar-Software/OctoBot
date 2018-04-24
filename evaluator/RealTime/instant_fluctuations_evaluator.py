import time

from evaluator.RealTime.realtime_evaluator import RealTimeTAEvaluator

from config.cst import *


class InstantFluctuationsEvaluator(RealTimeTAEvaluator):
    def __init__(self, exchange, symbol):
        super().__init__(exchange, symbol)
        self.enabled = True
        self.something_is_happening = False
        self.refresh_time = 0

        self.average_price = 0
        self.last_price = 0

        # Volume
        self.volume_updated = 0
        self.average_volume = 0
        self.last_volume = 0

        self.VOLUME_HAPPENING_THRESHOLD = 5

    def refresh_data(self):
        self.update()

    def eval_impl(self):
        self.evaluate_volume_fluctuations()
        if self.something_is_happening:
            self.something_is_happening = False
            self.notify_evaluator_threads(self.__class__.__name__)

    def evaluate_volume_fluctuations(self):
        # TEMP
        if self.last_volume > self.VOLUME_HAPPENING_THRESHOLD * self.average_volume:
            self.eval_note = 0.5 if self.last_price > self.average_price else -0.5
            self.something_is_happening = True

    def update(self, force=False):
        self.volume_updated += 1

        if (self.refresh_time * self.volume_updated) > TimeFramesMinutes[self.specific_config[CONFIG_TIME_FRAME]] or force:
            volume_data = self.exchange.get_symbol_prices(self.symbol, self.specific_config[CONFIG_TIME_FRAME], 10)
            self.average_volume = volume_data[PriceStrings.STR_PRICE_VOL.value].mean()
            self.average_price = volume_data[PriceStrings.STR_PRICE_CLOSE.value].mean()
            self.volume_updated = 0

        else:
            volume_data = self.exchange.get_symbol_prices(self.symbol, self.specific_config[CONFIG_TIME_FRAME], 1)

        self.last_volume = volume_data[PriceStrings.STR_PRICE_VOL.value].tail(1).values[0]
        self.last_price = volume_data[PriceStrings.STR_PRICE_CLOSE.value].tail(1).values[0]

    def set_default_config(self):
        self.specific_config = {
            CONFIG_REFRESH_RATE: 10,
            CONFIG_TIME_FRAME: TimeFrames.ONE_MINUTE
        }

    def run(self):
        if self.specific_config[CONFIG_REFRESH_RATE] > self.exchange.get_rate_limit():
            self.refresh_time = self.specific_config[CONFIG_REFRESH_RATE]
        else:
            self.refresh_time = self.exchange.get_rate_limit()

        self.update(force=True)

        while self.keep_running:
            self.refresh_data()
            self.eval()
            time.sleep(self.refresh_time)
