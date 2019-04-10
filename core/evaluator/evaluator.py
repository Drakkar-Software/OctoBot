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
from core.consumer import Consumer


class TAEvaluatorConsumer(Consumer):
    def __init__(self, evaluator):
        super().__init__()
        self.ta_evaluator = evaluator

    async def consume(self):
        while not self.should_stop:
            await self.queue.get()
            await self.perform()

    async def perform(self, trigger_tag=None):
        await self.ta_evaluator.eval()

    @staticmethod
    def create_feed(**kwargs):
        pass


class RealTimeEvaluatorConsumer(Consumer):
    def __init__(self, evaluator):
        super().__init__()
        self.rt_evaluator = evaluator

    async def consume(self):
        while not self.should_stop:
            await self.queue.get()
            await self.perform()

    async def perform(self):
        await self.rt_evaluator.eval()

    @staticmethod
    def create_feed(**kwargs):
        pass
