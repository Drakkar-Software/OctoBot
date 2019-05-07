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

import time
from abc import abstractmethod

from config import MAX_TA_EVAL_TIME_SECONDS, CONFIG_EVALUATOR_TA
from evaluator.abstract_evaluator import AbstractEvaluator


class TAEvaluator(AbstractEvaluator):
    __metaclass__ = AbstractEvaluator

    def __init__(self):
        super().__init__()
        self.data = None
        self.short_term_averages = [7, 5, 4, 3, 2, 1]
        self.long_term_averages = [40, 30, 20, 15, 10]

    def set_data(self, data):
        self.data = data

    def get_is_evaluable(self):
        return self.data is not None

    @abstractmethod
    async def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")

    @classmethod
    def get_config_tentacle_type(cls) -> str:
        return CONFIG_EVALUATOR_TA

    async def eval(self) -> None:
        start_time = time.time()
        await super().eval()
        execution_time = time.time()-start_time
        if execution_time > MAX_TA_EVAL_TIME_SECONDS:
            self.logger.warning(f"for {self.symbol} took longer than expected: {execution_time} seconds.")

    # TA are not standalone tasks
    async def start_task(self):
        pass


class MomentumEvaluator(TAEvaluator):
    __metaclass__ = TAEvaluator

    @abstractmethod
    async def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")


class OrderBookEvaluator(TAEvaluator):
    __metaclass__ = TAEvaluator

    @abstractmethod
    async def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")


class VolatilityEvaluator(TAEvaluator):
    __metaclass__ = TAEvaluator

    @abstractmethod
    async def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")


class TrendEvaluator(TAEvaluator):
    __metaclass__ = TAEvaluator

    @abstractmethod
    async def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")
